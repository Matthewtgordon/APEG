"""FastAPI routes for APEG job submission API."""
import logging
import os
import uuid
from typing import Optional

import aiohttp
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from ..schemas.bulk_ops import ProductSEO, ProductUpdateSpec
from ..shopify.bulk_mutation_client import ShopifyBulkMutationClient
from .auth import require_api_key


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["jobs"])


class SEOFields(BaseModel):
    """SEO title and description fields."""

    title: Optional[str] = Field(None, description="SEO title")
    description: Optional[str] = Field(None, description="SEO meta description")


class SEOUpdateProduct(BaseModel):
    """Product SEO and tag update specification."""

    product_id: str = Field(
        ..., description="Product GID (e.g., gid://shopify/Product/1234567890)"
    )
    tags_add: list[str] = Field(
        default_factory=list, description="Tags to add (merged with existing tags)"
    )
    tags_remove: list[str] = Field(
        default_factory=list, description="Tags to remove from existing tags"
    )
    seo: Optional[SEOFields] = Field(
        None, description="SEO fields to update (title/description)"
    )


class SEOUpdateJobRequest(BaseModel):
    """Request payload for SEO update job submission."""

    run_id: str = Field(
        ..., description="Client-provided run identifier for idempotency tracking"
    )
    shop_domain: str = Field(
        ..., description="Target Shopify store domain (must match configured store)"
    )
    products: list[SEOUpdateProduct] = Field(
        ..., description="Products to update (must be non-empty)"
    )
    dry_run: bool = Field(
        False, description="If true, validate and log actions without executing writes"
    )


class SEOUpdateJobResponse(BaseModel):
    """Immediate response for queued job."""

    job_id: str = Field(..., description="Server-generated job ID")
    status: str = Field(..., description="Job status (always 'queued' on acceptance)")
    run_id: str = Field(..., description="Echo of client-provided run_id")
    received_count: int = Field(..., description="Number of products received")


async def _run_seo_update_job(job_id: str, payload: SEOUpdateJobRequest) -> None:
    """Background task: Execute SEO update job with safe-write pipeline.

    This function MUST be exception-safe; all errors are caught and logged.
    """
    try:
        logger.info(
            "Starting SEO update job: job_id=%s, run_id=%s, products=%s, dry_run=%s",
            job_id,
            payload.run_id,
            len(payload.products),
            payload.dry_run,
        )

        if payload.dry_run:
            logger.info("DRY RUN MODE: Would update %s products", len(payload.products))
            for product in payload.products:
                logger.info(
                    "  Product %s: tags_add=%s, tags_remove=%s, seo=%s",
                    product.product_id,
                    product.tags_add,
                    product.tags_remove,
                    product.seo,
                )
            logger.info("Job %s completed (dry run)", job_id)
            return

        shop_domain = os.getenv("SHOPIFY_STORE_DOMAIN")
        access_token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
        api_version = os.getenv("SHOPIFY_API_VERSION", "2024-10")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        if not shop_domain or not access_token:
            raise RuntimeError(
                "SHOPIFY_STORE_DOMAIN and SHOPIFY_ADMIN_ACCESS_TOKEN must be set"
            )

        timeout = aiohttp.ClientTimeout(total=300, connect=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            redis = Redis.from_url(redis_url, decode_responses=False)
            try:
                mutation_client = ShopifyBulkMutationClient(
                    shop_domain=shop_domain,
                    access_token=access_token,
                    api_version=api_version,
                    session=session,
                    redis=redis,
                )

                update_specs: list[ProductUpdateSpec] = []
                for product in payload.products:
                    seo_input = None
                    if product.seo:
                        seo_input = ProductSEO(
                            title=product.seo.title,
                            description=product.seo.description,
                        )

                    update_specs.append(
                        ProductUpdateSpec(
                            product_id=product.product_id,
                            tags_add=product.tags_add,
                            tags_remove=product.tags_remove,
                            seo=seo_input,
                        )
                    )

                logger.info("Submitting bulk mutation for %s products", len(update_specs))

                bulk_ref = await mutation_client.run_product_update_bulk(
                    run_id=payload.run_id,
                    updates=update_specs,
                    dry_run=payload.dry_run,
                )

                logger.info("Bulk operation submitted: %s", bulk_ref.bulk_op_id)

                result = await mutation_client.poll_to_terminal(
                    bulk_ref.bulk_op_id,
                    timeout_s=3600,
                )

                if result.is_success:
                    logger.info(
                        "Job %s completed successfully: bulk_op=%s, objects=%s",
                        job_id,
                        bulk_ref.bulk_op_id,
                        result.object_count,
                    )
                else:
                    logger.error(
                        "Job %s failed: status=%s, error=%s",
                        job_id,
                        result.status,
                        result.error_code,
                    )

            finally:
                await redis.aclose()

    except Exception as exc:
        logger.error(
            "Job %s (run_id=%s) failed with exception: %s",
            job_id,
            payload.run_id,
            exc,
            exc_info=True,
        )


@router.post(
    "/jobs/seo-update",
    response_model=SEOUpdateJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_api_key)],
    summary="Submit SEO/tag update job",
    description=(
        "Enqueue a bulk product SEO and tag update job. "
        "Returns immediately (202 Accepted) with job_id. "
        "Job executes in background using safe-write tag merge."
    ),
)
async def create_seo_update_job(
    payload: SEOUpdateJobRequest,
    background_tasks: BackgroundTasks,
) -> SEOUpdateJobResponse:
    """Submit SEO update job for background processing.

    Validates:
    - API key (X-APEG-API-KEY header) - returns 401 if missing/invalid
    - shop_domain matches configured SHOPIFY_STORE_DOMAIN
    - products list is non-empty

    Returns immediately with job_id; actual work happens in background.
    """
    configured_store = os.getenv("SHOPIFY_STORE_DOMAIN")
    if not configured_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SHOPIFY_STORE_DOMAIN is not configured",
        )

    if payload.shop_domain != configured_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"shop_domain mismatch: expected '{configured_store}', "
                f"got '{payload.shop_domain}'"
            ),
        )

    if not payload.products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="products must be non-empty",
        )

    job_id = str(uuid.uuid4())

    background_tasks.add_task(_run_seo_update_job, job_id, payload)

    logger.info(
        "Queued SEO update job: job_id=%s, run_id=%s, products_count=%s",
        job_id,
        payload.run_id,
        len(payload.products),
    )

    return SEOUpdateJobResponse(
        job_id=job_id,
        status="queued",
        run_id=payload.run_id,
        received_count=len(payload.products),
    )
