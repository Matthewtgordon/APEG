"""Phase 2 Integration Tests: Safe Tag Writes & Staged Upload.

SAFETY GATES (ALL REQUIRED):
- APEG_ENV=DEMO
- SHOPIFY_STORE_DOMAIN in DEMO_STORE_DOMAIN_ALLOWLIST
- APEG_ALLOW_WRITES=YES

Exit codes:
- 0: All tests passed
- 2: Safety gate failure (env misconfiguration)
- 1: Test assertion failure
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import aiohttp
from redis.asyncio import Redis

from src.apeg_core.shopify.bulk_mutation_client import ShopifyBulkMutationClient
from src.apeg_core.schemas.bulk_ops import ProductUpdateSpec


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# GraphQL Queries (Script-Local)
QUERY_GET_PRODUCT_TAGS = """
query GetProductTags($id: ID!) {
  product(id: $id) {
    id
    tags
    seo { title description }
  }
}
"""

MUTATION_CREATE_TEST_PRODUCT = """
mutation CreateTestProduct($input: ProductInput!) {
  productCreate(input: $input) {
    product { id title tags }
    userErrors { field message }
  }
}
"""

MUTATION_DELETE_PRODUCT = """
mutation DeleteProduct($input: ProductDeleteInput!) {
  productDelete(input: $input) {
    deletedProductId
    userErrors { field message }
  }
}
"""


def require_env(name: str) -> str:
    """Get required environment variable or exit."""
    value = os.getenv(name)
    if not value:
        logger.error(f"Missing required environment variable: {name}")
        raise SystemExit(2)
    return value


def safety_gates() -> None:
    """Enforce DEMO-only safety gates."""
    # GATE 1: APEG_ENV must be DEMO
    if os.getenv("APEG_ENV") != "DEMO":
        logger.error("REFUSING TO RUN: APEG_ENV must be 'DEMO'")
        sys.exit(2)

    # GATE 2: Store domain must be in allowlist
    store = require_env("SHOPIFY_STORE_DOMAIN").strip()
    allowlist_raw = require_env("DEMO_STORE_DOMAIN_ALLOWLIST")
    allowlist = {s.strip() for s in allowlist_raw.split(",") if s.strip()}

    if store not in allowlist:
        logger.error(
            f"REFUSING TO RUN: Store '{store}' not in allowlist: {allowlist}"
        )
        sys.exit(2)

    # GATE 3: Explicit write confirmation required
    if os.getenv("APEG_ALLOW_WRITES") != "YES":
        logger.error('REFUSING TO RUN: Set APEG_ALLOW_WRITES="YES" to proceed')
        sys.exit(2)

    logger.info("PASS: Safety gates passed (DEMO-only mode confirmed)")


async def post_graphql(
    session: aiohttp.ClientSession,
    endpoint: str,
    access_token: str,
    query: str,
    variables: Optional[dict] = None,
) -> dict:
    """Execute GraphQL query/mutation."""
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token,
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    async with session.post(endpoint, json=payload, headers=headers) as resp:
        resp.raise_for_status()
        json_data = await resp.json()

        if "errors" in json_data and json_data["errors"]:
            messages = [
                error.get("message", str(error)) for error in json_data["errors"]
            ]
            raise RuntimeError(f"GraphQL root errors: {'; '.join(messages)}")

        return json_data


async def fetch_product_tags(
    session: aiohttp.ClientSession,
    endpoint: str,
    access_token: str,
    product_id: str,
) -> dict:
    """Fetch current product tags and SEO."""
    result = await post_graphql(
        session,
        endpoint,
        access_token,
        QUERY_GET_PRODUCT_TAGS,
        {"id": product_id},
    )

    product = result["data"]["product"]
    if not product:
        raise ValueError(f"Product not found: {product_id}")

    return {
        "id": product["id"],
        "tags": product.get("tags", []),
        "seo": product.get("seo") or {},
    }


async def create_test_product(
    session: aiohttp.ClientSession,
    endpoint: str,
    access_token: str,
    title: str,
) -> str:
    """Create a test product and return its GID."""
    result = await post_graphql(
        session,
        endpoint,
        access_token,
        MUTATION_CREATE_TEST_PRODUCT,
        {
            "input": {
                "title": title,
                "tags": ["apeg-integration-test"],
            }
        },
    )

    mutation_result = result["data"]["productCreate"]
    user_errors = mutation_result.get("userErrors", [])
    if user_errors:
        raise RuntimeError(f"Failed to create product: {user_errors}")

    product_id = mutation_result["product"]["id"]
    logger.info(f"Created test product: {product_id}")
    return product_id


async def delete_test_product(
    session: aiohttp.ClientSession,
    endpoint: str,
    access_token: str,
    product_id: str,
) -> None:
    """Delete a test product."""
    result = await post_graphql(
        session,
        endpoint,
        access_token,
        MUTATION_DELETE_PRODUCT,
        {"input": {"id": product_id}},
    )

    mutation_result = result["data"]["productDelete"]
    user_errors = mutation_result.get("userErrors", [])
    if user_errors:
        logger.error(f"Failed to delete product {product_id}: {user_errors}")
        raise RuntimeError(f"Cleanup failed: {user_errors}")

    logger.info(f"Deleted test product: {product_id}")


async def main() -> None:
    """Execute Phase 2 integration tests."""
    safety_gates()

    shop_domain = require_env("SHOPIFY_STORE_DOMAIN")
    access_token = require_env("SHOPIFY_ADMIN_ACCESS_TOKEN")
    api_version = require_env("SHOPIFY_API_VERSION")

    graphql_endpoint = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"

    test_product_id = os.getenv("TEST_PRODUCT_ID")
    created_product = False
    product_id: Optional[str] = None

    async with aiohttp.ClientSession() as session:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis = Redis.from_url(redis_url, decode_responses=False)

        try:
            mutation_client = ShopifyBulkMutationClient(
                shop_domain=shop_domain,
                access_token=access_token,
                api_version=api_version,
                session=session,
                redis=redis,
            )

            try:
                if test_product_id:
                    product_id = test_product_id
                    logger.info(f"Using provided test product: {product_id}")
                else:
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                    title = f"APEG Safe Write Test {timestamp}"
                    product_id = await create_test_product(
                        session, graphql_endpoint, access_token, title
                    )
                    created_product = True

                # ------------------------------------------------------------
                # SCENARIO 1: SAFE TAG MERGE (READ-MERGE-WRITE)
                # ------------------------------------------------------------
                logger.info("=" * 60)
                logger.info("SCENARIO 1: Safe Tag Merge (Preserve Original Tags)")
                logger.info("=" * 60)

                initial = await fetch_product_tags(
                    session, graphql_endpoint, access_token, product_id
                )
                initial_tags = set(initial["tags"])
                logger.info(f"Initial tags: {sorted(initial_tags)}")

                prefix = os.getenv("TEST_TAG_PREFIX", "apeg_safe_write_test")
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                new_tag = f"{prefix}_{timestamp}"

                if new_tag in initial_tags:
                    new_tag = f"{new_tag}_x"

                logger.info(f"Adding new tag: {new_tag}")

                update_spec = ProductUpdateSpec(
                    product_id=product_id,
                    tags_add=[new_tag],
                    tags_remove=[],
                )

                run_id = f"phase2-safe-write-{timestamp}"
                bulk_ref = await mutation_client.run_product_update_bulk(
                    run_id=run_id,
                    updates=[update_spec],
                )
                logger.info(f"Submitted bulk operation: {bulk_ref.bulk_op_id}")

                result = await mutation_client.poll_to_terminal(
                    bulk_ref.bulk_op_id,
                    timeout_s=300,
                )

                if not result.is_success:
                    raise RuntimeError(
                        "Bulk operation did not complete successfully: "
                        f"status={result.status}, error={result.error_code}"
                    )

                logger.info(
                    "PASS: Bulk operation completed (%s objects)",
                    result.object_count,
                )

                after = await fetch_product_tags(
                    session, graphql_endpoint, access_token, product_id
                )
                after_tags = set(after["tags"])
                logger.info(f"Final tags: {sorted(after_tags)}")

                if new_tag not in after_tags:
                    raise AssertionError(
                        f"FAIL: New tag '{new_tag}' not found in product tags"
                    )

                missing_tags = initial_tags - after_tags
                if missing_tags:
                    raise AssertionError(
                        "FAIL: Safe write failed; missing original tags: "
                        f"{sorted(missing_tags)}"
                    )

                logger.info("PASS: Safe write preserved all original tags")
                logger.info(f"PASS: New tag '{new_tag}' successfully added")

                # ------------------------------------------------------------
                # SCENARIO 2: STAGED UPLOAD DANCE (IMPLICIT)
                # ------------------------------------------------------------
                logger.info("=" * 60)
                logger.info("SCENARIO 2: Staged Upload Dance")
                logger.info("=" * 60)
                logger.info("PASS: Staged upload dance completed (no 403/400 errors)")
                logger.info(
                    "  (Implicitly validated by Scenario 1 completing successfully)"
                )

                # ------------------------------------------------------------
                # ALL TESTS PASSED
                # ------------------------------------------------------------
                logger.info("=" * 60)
                logger.info("PASS: ALL INTEGRATION TESTS PASSED")
                logger.info("=" * 60)

            finally:
                if created_product and product_id:
                    try:
                        logger.info("Cleaning up test product...")
                        await delete_test_product(
                            session, graphql_endpoint, access_token, product_id
                        )
                        logger.info("PASS: Cleanup successful")
                    except Exception as cleanup_error:
                        logger.error(
                            "CLEANUP FAILED; orphaned product_id=%s; error=%s",
                            product_id,
                            cleanup_error,
                        )
                        raise SystemExit(1)

        finally:
            await redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
        sys.exit(0)
    except AssertionError as e:
        logger.error(f"Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Integration test failed: {e}", exc_info=True)
        sys.exit(1)
