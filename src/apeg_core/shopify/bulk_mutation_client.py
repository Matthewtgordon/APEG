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
    BulkOperationRef,
    ProductSEO,
    ProductUpdateInput,
    ProductUpdateSpec,
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
from .graphql_strings import (
    MUTATION_BULK_OPERATION_RUN_MUTATION,
    MUTATION_PRODUCT_UPDATE,
    MUTATION_STAGED_UPLOADS_CREATE,
    QUERY_PRODUCTS_CURRENT_STATE,
)


logger = logging.getLogger(__name__)


class ShopifyBulkMutationClient:
    """Async client for Shopify bulk mutations with safe tag hydration."""

    MUTATION_LOCK_TTL_SECONDS = 1800  # 30 minutes
    FILE_CHUNK_SIZE_BYTES = 64 * 1024

    def __init__(
        self,
        shop_domain: str,
        access_token: str,
        api_version: str,
        session: aiohttp.ClientSession,
        redis: Redis,
        bulk_client: Optional[ShopifyBulkClient] = None,
        lock_ttl_seconds: int = MUTATION_LOCK_TTL_SECONDS,
        logger_instance: Optional[logging.Logger] = None,
    ):
        """Initialize Bulk Mutation Client.

        Args:
            shop_domain: e.g., "mystore.myshopify.com"
            access_token: Offline access token
            api_version: e.g., "2024-10"
            session: Injected aiohttp ClientSession
            redis: Injected redis.asyncio.Redis client
            bulk_client: Optional Phase 1 client (created if None)
            lock_ttl_seconds: Redis lock TTL
            logger_instance: Optional logger
        """
        self.shop_domain = shop_domain
        self._access_token = access_token
        self.api_version = api_version
        self.session = session
        self.redis = redis
        self.lock_ttl_seconds = lock_ttl_seconds
        self.logger = logger_instance or logger

        # Reuse or create Phase 1 client
        self.bulk_client = bulk_client or ShopifyBulkClient(
            shop_domain=shop_domain,
            admin_access_token=access_token,
            api_version=api_version,
            session=session,
            redis=redis,
            logger=self.logger,
        )

        self._mutation_lock_key = f"apeg:shopify:bulk_lock:{shop_domain}"
        self._current_lock: Optional[AsyncRedisLock] = None

    async def run_product_update_bulk(
        self,
        run_id: str,
        updates: list[ProductUpdateSpec],
        dry_run: bool = False,
    ) -> BulkOperationRef:
        """Execute bulk product update with safe-write pipeline.

        Pipeline:
        1. Acquire Redis lock
        2. Fetch current product state
        3. Merge tags (safe-write)
        4. Generate JSONL
        5. Staged upload dance
        6. Trigger bulk mutation

        Args:
            run_id: Client identifier for idempotency
            updates: Product update specifications
            dry_run: If true, log actions without executing

        Returns:
            BulkOperationRef with bulk_op_id

        Raises:
            ShopifyBulkMutationLockedError: If lock unavailable
            ShopifyBulkGraphQLError: On GraphQL errors
            ShopifyStagedUploadError: On upload failure
        """
        if dry_run:
            self.logger.info(f"DRY RUN: Would update {len(updates)} products")
            return BulkOperationRef(
                bulk_op_id="dry-run-no-op",
                run_id=run_id,
                shop_domain=self.shop_domain,
            )

        lock = AsyncRedisLock(
            self.redis,
            name=self._mutation_lock_key,
            timeout=self.lock_ttl_seconds,
            blocking=False,
        )

        acquired = await lock.acquire(blocking=False)
        if not acquired:
            raise ShopifyBulkMutationLockedError(
                self.shop_domain, self._mutation_lock_key
            )

        self._current_lock = lock
        self.logger.info(f"Acquired mutation lock: run_id={run_id}")

        jsonl_path: Optional[str] = None
        try:
            product_ids = [spec.product_id for spec in updates]
            current_tags_map = await self.fetch_current_tags(product_ids)

            merged_updates = self._merge_product_updates(updates, current_tags_map)
            jsonl_path = await self._generate_mutation_jsonl(merged_updates)

            try:
                staged_target = await self._staged_uploads_create()
                await self._upload_jsonl_to_staged_target(staged_target, jsonl_path)

                bulk_op = await self._bulk_operation_run_mutation(
                    mutation=MUTATION_PRODUCT_UPDATE,
                    staged_upload_path=staged_target.staged_upload_path,
                    group_objects=False,
                    client_identifier=f"apeg-phase2:{run_id}",
                )

                self.logger.info(
                    "Submitted bulk mutation: op_id=%s, run_id=%s, updates=%s",
                    bulk_op.id,
                    run_id,
                    len(merged_updates),
                )

                return BulkOperationRef(
                    bulk_op_id=bulk_op.id,
                    run_id=run_id,
                    shop_domain=self.shop_domain,
                )
            finally:
                if jsonl_path:
                    await self._remove_file_best_effort(jsonl_path)

        except Exception:
            await self._release_lock_best_effort()
            raise

    async def poll_to_terminal(
        self,
        bulk_op_id: str,
        timeout_s: int = 3600,
    ) -> BulkOperation:
        """Poll bulk operation until terminal state.

        Uses Phase 1 client for polling. Releases lock when complete.
        """
        try:
            return await self.bulk_client.poll_status(
                operation_id=bulk_op_id,
                poll_interval=5.0,
                timeout=timeout_s,
            )
        finally:
            await self._release_lock_best_effort()

    async def fetch_current_tags(
        self,
        product_ids: list[str],
    ) -> dict[str, list[str]]:
        """Fetch current tags for safe-write merge (Phase 1 bulk query)."""
        if not product_ids:
            return {}

        target_ids = set(product_ids)

        operation = await self.bulk_client.submit_job(QUERY_PRODUCTS_CURRENT_STATE)
        result = await self.bulk_client.poll_status(operation.id)

        tags_map: dict[str, list[str]] = {}
        async with self.session.get(result.url) as resp:
            resp.raise_for_status()
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue

                node = json.loads(line)
                product_id = node.get("id")
                if product_id and product_id in target_ids:
                    tags_map[product_id] = node.get("tags", [])

        return tags_map

    def _merge_product_updates(
        self,
        updates: list[ProductUpdateSpec],
        current_tags_map: dict[str, list[str]],
    ) -> list[ProductUpdateInput]:
        """Merge current tags with desired updates (safe-write pattern)."""
        merged: list[ProductUpdateInput] = []

        for spec in updates:
            current_tags = set(current_tags_map.get(spec.product_id, []))

            if spec.tags_full is not None:
                final_tags = sorted(set(spec.tags_full))
            else:
                add_tags = set(spec.tags_add)
                remove_tags = set(spec.tags_remove)
                final_tags = sorted((current_tags | add_tags) - remove_tags)

            merged.append(
                ProductUpdateInput(
                    id=spec.product_id,
                    tags=final_tags,
                    seo=spec.seo,
                )
            )

        return merged

    async def _generate_mutation_jsonl(
        self,
        updates: list[ProductUpdateInput],
    ) -> str:
        """Generate JSONL file for bulk mutation variables."""
        temp_dir = tempfile.gettempdir()
        filename = f"apeg_bulk_mutation_{uuid.uuid4().hex}.jsonl"
        temp_path = os.path.join(temp_dir, filename)

        async with aiofiles.open(temp_path, mode="w", encoding="utf-8") as f:
            for update in updates:
                jsonl_line = json.dumps(update.to_jsonl_dict(), ensure_ascii=False)
                await f.write(jsonl_line + "\n")

        self.logger.debug(
            "Generated JSONL: %s, lines=%s",
            temp_path,
            len(updates),
        )
        return temp_path

    async def _staged_uploads_create(self) -> StagedTarget:
        """Step A: Reserve staged upload target."""
        variables = {
            "input": [
                {
                    "resource": "BULK_MUTATION_VARIABLES",
                    "filename": "bulk_op_vars",
                    "mimeType": "text/jsonl",
                    "httpMethod": "POST",
                }
            ]
        }

        resp_data = await self.bulk_client._post_graphql(
            {"query": MUTATION_STAGED_UPLOADS_CREATE, "variables": variables}
        )

        mutation_result = resp_data["data"]["stagedUploadsCreate"]
        user_errors = mutation_result.get("userErrors", [])
        if user_errors:
            raise ShopifyBulkGraphQLError(
                f"stagedUploadsCreate userErrors: {user_errors}"
            )

        staged_targets = mutation_result.get("stagedTargets", [])
        if not staged_targets:
            raise ShopifyBulkApiError("No stagedTargets returned")

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
        """Step B: Upload JSONL via multipart (CRITICAL: file field LAST)."""
        form = aiohttp.FormData()

        for param in staged_target.parameters:
            form.add_field(param.name, param.value)

        file_iter = self._iter_file_chunks(jsonl_path)
        form.add_field(  # Add file field LAST (mandatory ordering)
            name="file",
            value=file_iter,
            filename="bulk_op_vars.jsonl",
            content_type="text/jsonl",
        )

        async with self.session.post(staged_target.url, data=form) as resp:
            body = await resp.text()
            if resp.status not in (200, 201, 204):
                raise ShopifyStagedUploadError(status=resp.status, body=body)

            self.logger.info("Uploaded JSONL: status=%s", resp.status)

    async def _bulk_operation_run_mutation(
        self,
        mutation: str,
        staged_upload_path: str,
        group_objects: bool,
        client_identifier: str,
    ) -> BulkOperation:
        """Step C: Trigger bulk mutation run."""
        variables = {
            "mutation": mutation,
            "stagedUploadPath": staged_upload_path,
            "groupObjects": group_objects,
            "clientIdentifier": client_identifier,
        }

        resp_data = await self.bulk_client._post_graphql(
            {"query": MUTATION_BULK_OPERATION_RUN_MUTATION, "variables": variables}
        )

        mutation_result = resp_data["data"]["bulkOperationRunMutation"]
        user_errors = mutation_result.get("userErrors", [])
        if user_errors:
            raise ShopifyBulkGraphQLError(
                f"bulkOperationRunMutation userErrors: {user_errors}"
            )

        op_data = mutation_result["bulkOperation"]
        return BulkOperation(
            id=op_data["id"],
            status=op_data["status"],
            url=op_data.get("url"),
            object_count=None,
        )

    async def _release_lock_best_effort(self) -> None:
        """Release mutation lock with error suppression."""
        if self._current_lock:
            try:
                await self._current_lock.release()
                self.logger.info("Released mutation lock")
            except Exception as e:
                self.logger.error(f"Failed to release lock: {e}")
            finally:
                self._current_lock = None

    async def _remove_file_best_effort(self, path: str) -> None:
        """Remove temporary JSONL file with error suppression."""
        try:
            await aiofiles.os.remove(path)
        except FileNotFoundError:
            return
        except Exception as exc:
            self.logger.error(f"Failed to remove temp JSONL file: {exc}")

    async def _iter_file_chunks(self, path: str):
        """Yield file chunks asynchronously for multipart upload."""
        async with aiofiles.open(path, mode="rb") as f:
            while True:
                chunk = await f.read(self.FILE_CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                yield chunk
