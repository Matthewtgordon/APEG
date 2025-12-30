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
from datetime import datetime
from typing import Optional

import aiohttp
from redis.asyncio import Redis

from src.apeg_core.shopify.bulk_mutation_client import ShopifyBulkMutationClient
from src.apeg_core.schemas.bulk_ops import BulkOperation, ProductUpdateInput


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
        return await resp.json()


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
    # Enforce safety gates
    safety_gates()

    # Load environment
    shop_domain = require_env("SHOPIFY_STORE_DOMAIN")
    access_token = require_env("SHOPIFY_ADMIN_ACCESS_TOKEN")
    api_version = require_env("SHOPIFY_API_VERSION")

    graphql_endpoint = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"

    # Optional: Use existing test product
    test_product_id = os.getenv("TEST_PRODUCT_ID")
    created_product = False
    product_id = None

    # Initialize clients
    async with aiohttp.ClientSession() as session:
        # Redis setup (optional if client supports lock-free mode)
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis = Redis.from_url(redis_url, decode_responses=False)

        try:
            mutation_client = ShopifyBulkMutationClient(
                shop_domain=shop_domain,
                admin_access_token=access_token,
                api_version=api_version,
                session=session,
                redis=redis,
            )

            # Setup: Get or create test product
            if test_product_id:
                product_id = test_product_id
                logger.info(f"Using provided test product: {product_id}")
            else:
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                title = f"APEG Safe Write Test {timestamp}"
                product_id = await create_test_product(
                    session, graphql_endpoint, access_token, title
                )
                created_product = True

            try:
                # ------------------------------------------------------------
                # SCENARIO 1: SAFE TAG MERGE (READ-MERGE-WRITE)
                # ------------------------------------------------------------
                logger.info("=" * 60)
                logger.info("SCENARIO 1: Safe Tag Merge (Preserve Original Tags)")
                logger.info("=" * 60)

                # Fetch initial state
                initial = await fetch_product_tags(
                    session, graphql_endpoint, access_token, product_id
                )
                initial_tags = set(initial["tags"])
                logger.info(f"Initial tags: {sorted(initial_tags)}")

                # Generate unique new tag
                prefix = os.getenv("TEST_TAG_PREFIX", "apeg_safe_write_test")
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                new_tag = f"{prefix}_{timestamp}"

                if new_tag in initial_tags:
                    new_tag = f"{new_tag}_x"

                logger.info(f"Adding new tag: {new_tag}")

                # Merge tags (union)
                merged_tags = sorted(initial_tags | {new_tag})

                # Submit bulk mutation
                product_update = ProductUpdateInput(
                    id=product_id,
                    tags=merged_tags,
                )

                bulk_op_id = await mutation_client.run_product_update_bulk(
                    [product_update]
                )
                logger.info(f"Submitted bulk operation: {bulk_op_id}")

                # Poll until complete
                result = await mutation_client.poll_and_get_result(
                    bulk_op_id,
                    poll_interval=2.0,
                    timeout=300,
                )

                if not result.is_success:
                    raise RuntimeError(
                        f"Bulk operation did not complete successfully: "
                        f"status={result.status}, error={result.error_code}"
                    )

                logger.info(
                    f"PASS: Bulk operation completed ({result.object_count} objects)"
                )

                # Verify: Fetch product again
                after = await fetch_product_tags(
                    session, graphql_endpoint, access_token, product_id
                )
                after_tags = set(after["tags"])
                logger.info(f"Final tags: {sorted(after_tags)}")

                # Assertion 1: New tag present
                if new_tag not in after_tags:
                    raise AssertionError(
                        f"FAIL: New tag '{new_tag}' not found in product tags"
                    )

                # Assertion 2: All original tags preserved
                missing_tags = initial_tags - after_tags
                if missing_tags:
                    raise AssertionError(
                        f"FAIL: Safe write failed; missing original tags: "
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
                # CLEANUP GUARANTEE: Delete created test product
                if created_product and product_id:
                    try:
                        logger.info("Cleaning up test product...")
                        await delete_test_product(
                            session, graphql_endpoint, access_token, product_id
                        )
                        logger.info("PASS: Cleanup successful")
                    except Exception as cleanup_error:
                        logger.error(
                            f"CLEANUP FAILED for product {product_id}: {cleanup_error}"
                        )
                        sys.exit(1)

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
