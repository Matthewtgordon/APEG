"""Async Shopify Bulk Mutation Client with Staged Upload workflow."""
import json
import logging
import os
import tempfile
import uuid
from typing import Optional

import aiofiles
import aiofiles.os
import aiohttp
from redis.asyncio import Redis
from redis.asyncio.lock import Lock as AsyncRedisLock

from ..schemas.bulk_ops import (
    BulkOperation,
    ProductCurrentState,
    ProductUpdateInput,
    StagedTarget,
    StagedUploadParameter,
)
from .bulk_client import ShopifyBulkClient
from .exceptions import (
    ShopifyBulkApiError,
    ShopifyBulkGraphQLError,
    ShopifyBulkMutationLockedError,
    ShopifyStagedUploadError,
)


# GraphQL Operations (VERBATIM from spec)
MUTATION_STAGED_UPLOADS_CREATE = """
mutation {
  stagedUploadsCreate(input:[{
    resource: BULK_MUTATION_VARIABLES,
    filename: "bulk_op_vars",
    mimeType: "text/jsonl",
    httpMethod: POST
  }]){
    userErrors{ field, message },
    stagedTargets{
      url,
      resourceUrl,
      parameters { name, value }
    }
  }
}
"""

MUTATION_BULK_OPERATION_RUN_MUTATION = """
mutation bulkOperationRunMutation($mutation: String!, $stagedUploadPath: String!, $groupObjects: Boolean!, $clientIdentifier: String) {
  bulkOperationRunMutation(
    mutation: $mutation,
    stagedUploadPath: $stagedUploadPath,
    groupObjects: $groupObjects,
    clientIdentifier: $clientIdentifier
  ) {
    bulkOperation { id url status }
    userErrors { field message }
  }
}
"""

MUTATION_PRODUCT_UPDATE = """
mutation call($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product {
      id
      tags
      seo { title description }
    }
    userErrors { field message }
  }
}
"""

QUERY_PRODUCTS_CURRENT_STATE = """
{
  products {
    edges {
      node {
        id
        tags
        seo {
          title
          description
        }
      }
    }
  }
}
"""


class ShopifyBulkMutationClient:
    """Async client for Shopify bulk mutations with safe tag hydration.

    Implements the 4-step Staged Upload Dance:
    1. Reserve staged upload target (stagedUploadsCreate)
    2. Upload JSONL to staged URL (multipart/form-data)
    3. Trigger bulk mutation (bulkOperationRunMutation)
    4. Poll status via Phase 1 client
    """

    MUTATION_LOCK_TTL_SECONDS = 3600  # 1 hour for large mutations
    FILE_CHUNK_SIZE_BYTES = 64 * 1024

    def __init__(
        self,
        shop_domain: str,
        admin_access_token: str,
        api_version: str,
        session: aiohttp.ClientSession,
        redis: Redis,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize Bulk Mutation Client.

        Args:
            shop_domain: e.g., "mystore.myshopify.com"
            admin_access_token: Offline access token
            api_version: e.g., "2024-10"
            session: Injected aiohttp ClientSession
            redis: Injected redis.asyncio.Redis client
            logger: Optional logger instance
        """
        self.shop_domain = shop_domain
        self._access_token = admin_access_token
        self.api_version = api_version
        self.session = session
        self.redis = redis
        self.logger = logger or logging.getLogger(__name__)

        # Reuse Phase 1 client for polling
        self.bulk_client = ShopifyBulkClient(
            shop_domain=shop_domain,
            admin_access_token=admin_access_token,
            api_version=api_version,
            session=session,
            redis=redis,
            logger=logger,
        )

        self.graphql_endpoint = (
            f"https://{shop_domain}/admin/api/{api_version}/graphql.json"
        )
        self._mutation_lock_key = f"apeg:shopify:bulk_mutation_lock:{shop_domain}"
        self._current_lock: Optional[AsyncRedisLock] = None

    async def run_product_update_bulk(
        self,
        product_updates: list[ProductUpdateInput],
        client_identifier: str = "apeg-phase2-productUpdate",
    ) -> str:
        """Execute bulk product update with staged upload workflow.

        Args:
            product_updates: List of ProductUpdateInput with merged tags/seo
            client_identifier: Optional identifier for tracking

        Returns:
            Bulk operation ID (GID)

        Raises:
            ShopifyBulkMutationLockedError: If lock cannot be acquired
            ShopifyBulkGraphQLError: On GraphQL userErrors
            ShopifyStagedUploadError: On multipart upload failure
        """
        # Acquire mutation lock
        lock = AsyncRedisLock(
            self.redis,
            name=self._mutation_lock_key,
            timeout=self.MUTATION_LOCK_TTL_SECONDS,
            blocking=False,
        )

        acquired = await lock.acquire(blocking=False)
        if not acquired:
            raise ShopifyBulkMutationLockedError(self.shop_domain, self._mutation_lock_key)

        self._current_lock = lock
        self.logger.info(f"Acquired bulk mutation lock for shop={self.shop_domain}")

        jsonl_path = None
        try:
            # Generate JSONL file
            jsonl_path = await self._generate_product_update_jsonl(product_updates)

            # Step 1: Reserve staged upload target
            staged_target = await self._staged_uploads_create()

            # Step 2: Upload JSONL to staged target
            await self._upload_jsonl_to_staged_target(staged_target, jsonl_path)

            # Step 3: Trigger bulk mutation
            bulk_op = await self._bulk_operation_run_mutation(
                mutation=MUTATION_PRODUCT_UPDATE,
                staged_upload_path=staged_target.staged_upload_path,
                group_objects=False,
                client_identifier=client_identifier,
            )

            self.logger.info(
                f"Submitted bulk mutation: id={bulk_op.id}, "
                f"products_count={len(product_updates)}"
            )
            return bulk_op.id

        except Exception:
            await self._release_lock_best_effort()
            raise
        finally:
            if jsonl_path:
                await self._remove_file_best_effort(jsonl_path)

    async def poll_and_get_result(
        self,
        operation_id: str,
        poll_interval: float = 5.0,
        timeout: float = 7200,  # 2 hours
    ) -> BulkOperation:
        """Poll bulk mutation status until terminal state.

        Uses Phase 1 ShopifyBulkClient.poll_status() internally.
        Releases mutation lock when complete.

        Args:
            operation_id: Bulk operation GID
            poll_interval: Seconds between polls
            timeout: Maximum poll duration

        Returns:
            BulkOperation in terminal state
        """
        try:
            result = await self.bulk_client.poll_status(
                operation_id=operation_id,
                poll_interval=poll_interval,
                timeout=timeout,
            )
            return result
        finally:
            await self._release_lock_best_effort()

    async def fetch_current_product_state(
        self,
        product_ids: list[str],
    ) -> dict[str, ProductCurrentState]:
        """Fetch current tags and SEO for safe-write merge.

        Uses Phase 1 bulk query to fetch current product state.

        Args:
            product_ids: List of product GIDs

        Returns:
            Map of {product_id: ProductCurrentState}
        """
        if not product_ids:
            return {}

        target_ids = set(product_ids)

        # Submit bulk query for products
        bulk_query = QUERY_PRODUCTS_CURRENT_STATE
        operation = await self.bulk_client.submit_job(bulk_query)

        # Poll until complete
        result = await self.bulk_client.poll_status(operation.id)

        # Download and parse JSONL
        current_state_map: dict[str, ProductCurrentState] = {}
        async with self.session.get(result.url) as resp:
            resp.raise_for_status()

            async for raw_line in resp.content:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                node = json.loads(line)

                # Extract product data
                product_id = node.get("id")
                if not product_id or product_id not in target_ids:
                    continue

                seo = node.get("seo") or {}
                current_state_map[product_id] = ProductCurrentState(
                    id=product_id,
                    tags=node.get("tags", []),
                    seo_title=seo.get("title"),
                    seo_description=seo.get("description"),
                )

        return current_state_map

    def merge_product_updates(
        self,
        current_state_map: dict[str, ProductCurrentState],
        desired_updates: list[ProductUpdateInput],
    ) -> list[ProductUpdateInput]:
        """Merge current tags with desired updates (safe-write pattern).

        Args:
            current_state_map: Current product state from fetch_current_product_state
            desired_updates: Desired updates (may have partial tags or new SEO)

        Returns:
            Merged ProductUpdateInput list with complete tag sets
        """
        merged = []

        for update in desired_updates:
            current = current_state_map.get(update.id)
            if not current:
                self.logger.warning(
                    f"Product {update.id} not found in current state; using update as-is"
                )
                merged.append(update)
                continue

            # Merge tags: union of current + incoming
            current_tags = set(current.tags)
            incoming_tags = set(update.tags or [])
            merged_tags = sorted(current_tags | incoming_tags)

            # SEO: incoming wins if provided
            merged_seo = update.seo
            if not merged_seo and (current.seo_title or current.seo_description):
                from ..schemas.bulk_ops import ProductSEOInput

                merged_seo = ProductSEOInput(
                    title=current.seo_title,
                    description=current.seo_description,
                )

            merged.append(
                ProductUpdateInput(
                    id=update.id,
                    tags=merged_tags,
                    seo=merged_seo,
                )
            )

        return merged

    async def _staged_uploads_create(self) -> StagedTarget:
        """Step 1: Reserve staged upload target for bulk mutation variables."""
        payload = {"query": MUTATION_STAGED_UPLOADS_CREATE}

        resp_data = await self._post_graphql(payload)

        # Check userErrors
        mutation_result = resp_data["data"]["stagedUploadsCreate"]
        user_errors = mutation_result.get("userErrors", [])
        if user_errors:
            raise ShopifyBulkGraphQLError(user_errors)

        # Extract stagedTarget
        staged_targets = mutation_result.get("stagedTargets", [])
        if not staged_targets:
            raise ShopifyBulkApiError("No stagedTargets returned from stagedUploadsCreate")

        target_data = staged_targets[0]
        return StagedTarget(
            url=target_data["url"],
            resource_url=target_data.get("resourceUrl"),
            parameters=[
                StagedUploadParameter(name=p["name"], value=p["value"])
                for p in target_data.get("parameters", [])
            ],
        )

    async def _upload_jsonl_to_staged_target(
        self,
        staged_target: StagedTarget,
        jsonl_path: str,
    ) -> None:
        """Step 2: Upload JSONL to staged URL via multipart/form-data.

        CRITICAL: File field MUST be appended LAST in multipart form.
        """
        form = aiohttp.FormData()

        # Add Shopify-provided parameters first, in order received
        for param in staged_target.parameters:
            form.add_field(param.name, param.value)
            self.logger.debug(f"Added form field: {param.name}={param.value[:50]}...")

        file_iter = self._iter_file_chunks(jsonl_path)
        form.add_field(  # Add file field LAST (mandatory ordering)
            name="file",
            value=file_iter,
            filename=os.path.basename(jsonl_path),
            content_type="text/jsonl",
        )

        # Execute multipart POST
        async with self.session.post(staged_target.url, data=form) as resp:
            body = await resp.text()
            if resp.status not in (200, 201, 204):
                raise ShopifyStagedUploadError(status=resp.status, body=body)

            self.logger.info(
                f"Uploaded JSONL to staged target: status={resp.status}"
            )

    async def _bulk_operation_run_mutation(
        self,
        mutation: str,
        staged_upload_path: str,
        group_objects: bool,
        client_identifier: str,
    ) -> BulkOperation:
        """Step 3: Trigger bulk mutation run."""
        payload = {
            "query": MUTATION_BULK_OPERATION_RUN_MUTATION,
            "variables": {
                "mutation": mutation,
                "stagedUploadPath": staged_upload_path,
                "groupObjects": group_objects,
                "clientIdentifier": client_identifier,
            },
        }

        resp_data = await self._post_graphql(payload)

        # Check userErrors
        mutation_result = resp_data["data"]["bulkOperationRunMutation"]
        user_errors = mutation_result.get("userErrors", [])
        if user_errors:
            raise ShopifyBulkGraphQLError(user_errors)

        # Extract bulkOperation
        op_data = mutation_result["bulkOperation"]
        return BulkOperation(
            id=op_data["id"],
            status=op_data["status"],
            url=op_data.get("url"),
            object_count=None,
        )

    async def _post_graphql(self, payload: dict) -> dict:
        """Execute GraphQL POST (reuses Phase 1 retry logic)."""
        return await self.bulk_client._post_graphql(payload, retry=True)

    async def _generate_product_update_jsonl(
        self,
        product_updates: list[ProductUpdateInput],
    ) -> str:
        """Generate JSONL file for bulk mutation variables.

        Returns:
            Path to temporary JSONL file
        """
        temp_dir = tempfile.gettempdir()
        filename = f"apeg_bulk_mutation_{uuid.uuid4().hex}.jsonl"
        temp_path = os.path.join(temp_dir, filename)

        async with aiofiles.open(temp_path, mode="w", encoding="utf-8") as f:
            for update in product_updates:
                jsonl_line = json.dumps(update.to_jsonl_dict(), ensure_ascii=False)
                await f.write(jsonl_line + "\n")

        self.logger.debug(
            f"Generated JSONL: {temp_path}, lines={len(product_updates)}"
        )
        return temp_path

    async def _remove_file_best_effort(self, path: str) -> None:
        """Remove temporary JSONL file with error suppression."""
        try:
            await aiofiles.os.remove(path)
        except FileNotFoundError:
            return
        except Exception as exc:
            self.logger.error(f"Failed to remove temp JSONL file: {exc}")

    async def _release_lock_best_effort(self) -> None:
        """Release mutation lock with error suppression."""
        if self._current_lock:
            try:
                await self._current_lock.release()
                self.logger.info(
                    f"Released bulk mutation lock for shop={self.shop_domain}"
                )
            except Exception as e:
                self.logger.error(f"Failed to release mutation lock: {e}")
            finally:
                self._current_lock = None

    async def _iter_file_chunks(self, path: str):
        """Yield file chunks asynchronously for multipart upload."""
        async with aiofiles.open(path, mode="rb") as f:
            while True:
                chunk = await f.read(self.FILE_CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                yield chunk
