"""Async Shopify GraphQL Bulk Operations Client with Redis concurrency control."""
import asyncio
import logging
import random
from time import monotonic
from typing import Optional

import aiohttp
from redis.asyncio import Redis
from redis.asyncio.lock import Lock as AsyncRedisLock

from ..schemas.bulk_ops import BulkOperation
from .exceptions import (
    ShopifyBulkApiError,
    ShopifyBulkGraphQLError,
    ShopifyBulkJobLockedError,
)


# GraphQL Operations (VERBATIM from spec)
MUTATION_BULK_RUN_QUERY = """
mutation BulkRunQuery($query: String!) {
  bulkOperationRunQuery(query: $query) {
    bulkOperation {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

QUERY_BULK_OP_BY_ID = """
query BulkOpById($id: ID!) {
  node(id: $id) {
    ... on BulkOperation {
      id
      status
      errorCode
      objectCount
      url
      partialDataUrl
    }
  }
}
"""

MUTATION_BULK_CANCEL = """
mutation BulkCancel($id: ID!) {
  bulkOperationCancel(id: $id) {
    bulkOperation {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""


class ShopifyBulkClient:
    """Async client for Shopify GraphQL Admin Bulk Operations API.

    Enforces 1 concurrent job per shop via Redis locks.
    Implements defensive retry logic for 429/5xx/network errors.
    """

    LOCK_TTL_SECONDS = 1800  # 30 minutes
    LOCK_REFRESH_INTERVAL = 300  # 5 minutes
    DEFAULT_POLL_INTERVAL = 2.0  # seconds
    DEFAULT_POLL_TIMEOUT = 3600  # 1 hour

    MAX_RETRY_ATTEMPTS = 6
    RETRY_BASE_DELAY = 0.5  # seconds
    RETRY_MULTIPLIER = 2.0
    RETRY_MAX_DELAY = 30.0  # seconds
    RETRY_JITTER_MS = 250  # milliseconds

    def __init__(
        self,
        shop_domain: str,
        admin_access_token: str,
        api_version: str,
        session: aiohttp.ClientSession,
        redis: Redis,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize Shopify Bulk Client.

        Args:
            shop_domain: e.g., "mystore.myshopify.com"
            admin_access_token: Offline access token (never logged)
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

        self.graphql_endpoint = (
            f"https://{shop_domain}/admin/api/{api_version}/graphql.json"
        )
        self._lock_key = f"apeg:shopify:bulk_lock:{shop_domain}"
        self._current_lock: Optional[AsyncRedisLock] = None

    async def submit_job(self, bulk_query: str) -> BulkOperation:
        """Submit a bulk operation query job to Shopify.

        Args:
            bulk_query: GraphQL query string for bulk operation

        Returns:
            BulkOperation with id and initial status

        Raises:
            ShopifyBulkJobLockedError: If lock cannot be acquired
            ShopifyBulkGraphQLError: If GraphQL returns userErrors
            ShopifyBulkApiError: For other API errors
        """
        # Acquire Redis lock (fail fast)
        lock = AsyncRedisLock(
            self.redis,
            name=self._lock_key,
            timeout=self.LOCK_TTL_SECONDS,
            blocking=False,
        )

        acquired = await lock.acquire(blocking=False)
        if not acquired:
            raise ShopifyBulkJobLockedError(self.shop_domain, self._lock_key)

        self._current_lock = lock
        self.logger.info(f"Acquired bulk lock for shop={self.shop_domain}")

        try:
            payload = {
                "query": MUTATION_BULK_RUN_QUERY,
                "variables": {"query": bulk_query},
            }

            resp_data = await self._post_graphql(payload, retry=True)

            # Check for GraphQL userErrors
            mutation_result = resp_data["data"]["bulkOperationRunQuery"]
            user_errors = mutation_result.get("userErrors", [])
            if user_errors:
                raise ShopifyBulkGraphQLError(user_errors)

            # Extract bulkOperation
            op_data = mutation_result["bulkOperation"]
            operation = BulkOperation(
                id=op_data["id"],
                status=op_data["status"],
                url=None,
                object_count=None,
            )

            self.logger.info(
                f"Submitted bulk job: id={operation.id}, status={operation.status}"
            )
            return operation

        except Exception:
            # Release lock on any failure during submit
            await self._release_lock_best_effort()
            raise

    async def poll_status(
        self,
        operation_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_POLL_TIMEOUT,
    ) -> BulkOperation:
        """Poll bulk operation status until terminal state.

        Args:
            operation_id: GID of bulk operation (from submit_job)
            poll_interval: Seconds between poll requests
            timeout: Maximum seconds to poll before raising timeout error

        Returns:
            BulkOperation in terminal state (COMPLETED/FAILED/CANCELED/EXPIRED)

        Raises:
            ShopifyBulkApiError: On timeout, missing data, or terminal failure
        """
        start_time = monotonic()
        last_lock_refresh = monotonic()

        while True:
            # Check timeout
            elapsed = monotonic() - start_time
            if elapsed > timeout:
                await self._release_lock_best_effort()
                raise ShopifyBulkApiError(
                    f"Bulk poll timeout after {elapsed:.1f}s for op={operation_id}"
                )

            # Refresh lock TTL every LOCK_REFRESH_INTERVAL
            if monotonic() - last_lock_refresh > self.LOCK_REFRESH_INTERVAL:
                await self._refresh_lock_ttl()
                last_lock_refresh = monotonic()

            # Poll via node(id) query
            payload = {
                "query": QUERY_BULK_OP_BY_ID,
                "variables": {"id": operation_id},
            }

            resp_data = await self._post_graphql(payload, retry=True)
            node = resp_data["data"].get("node")

            if node is None:
                await self._release_lock_best_effort()
                raise ShopifyBulkApiError(
                    f"Bulk operation not found: id={operation_id}"
                )

            # Parse BulkOperation
            operation = BulkOperation(
                id=node["id"],
                status=node["status"],
                url=node.get("url"),
                object_count=self._safe_int(node.get("objectCount")),
                error_code=node.get("errorCode"),
                partial_data_url=node.get("partialDataUrl"),
            )

            self.logger.debug(
                f"Poll: status={operation.status}, elapsed={elapsed:.1f}s"
            )

            # Check terminal states
            if operation.status == "COMPLETED":
                await self._release_lock_best_effort()
                if not operation.url:
                    raise ShopifyBulkApiError(
                        f"Bulk operation COMPLETED but url missing: {operation.id}"
                    )
                self.logger.info(f"Bulk operation completed: {operation.id}")
                return operation

            if operation.status in {"FAILED", "CANCELED", "EXPIRED"}:
                await self._release_lock_best_effort()
                raise ShopifyBulkApiError(
                    f"Bulk operation terminal failure: status={operation.status}, "
                    f"error_code={operation.error_code}, "
                    f"partial_data_url={operation.partial_data_url}"
                )

            # Still in progress: CREATED, RUNNING, CANCELING
            await asyncio.sleep(poll_interval)

    async def _post_graphql(self, payload: dict, retry: bool = True) -> dict:
        """Execute GraphQL POST with retry logic.

        Args:
            payload: GraphQL query/mutation payload
            retry: Whether to retry on transient errors

        Returns:
            Parsed JSON response data

        Raises:
            ShopifyBulkApiError: On non-retryable errors or max retries exceeded
        """
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self._access_token,
        }

        attempt = 0
        while True:
            attempt += 1

            try:
                timeout = aiohttp.ClientTimeout(total=60, connect=10)
                async with self.session.post(
                    self.graphql_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                ) as resp:
                    response_text = await resp.text()

                    # Handle 429 (Rate Limit)
                    if resp.status == 429:
                        if not retry or attempt > self.MAX_RETRY_ATTEMPTS:
                            raise ShopifyBulkApiError(
                                f"HTTP 429 after {attempt} attempts: {response_text[:200]}"
                            )

                        retry_after = resp.headers.get("Retry-After")
                        if retry_after:
                            delay = float(retry_after)
                            self.logger.warning(
                                f"HTTP 429, Retry-After={delay}s, attempt={attempt}"
                            )
                        else:
                            delay = self._calculate_backoff(attempt)
                            self.logger.warning(
                                f"HTTP 429, backoff={delay:.2f}s, attempt={attempt}"
                            )

                        await asyncio.sleep(delay)
                        continue

                    # Handle 5xx (Server Errors)
                    if 500 <= resp.status < 600:
                        if not retry or attempt > self.MAX_RETRY_ATTEMPTS:
                            raise ShopifyBulkApiError(
                                f"HTTP {resp.status} after {attempt} attempts: {response_text[:200]}"
                            )

                        delay = self._calculate_backoff(attempt)
                        self.logger.warning(
                            f"HTTP {resp.status}, backoff={delay:.2f}s, attempt={attempt}"
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Handle other 4xx (Client Errors - no retry)
                    if 400 <= resp.status < 500:
                        raise ShopifyBulkApiError(
                            f"HTTP {resp.status} (non-retryable): {response_text[:500]}"
                        )

                    # Success: parse JSON
                    resp.raise_for_status()
                    json_data = await resp.json()

                    # CRITICAL BUG FIX: Check root-level errors BEFORE accessing data
                    if "errors" in json_data and json_data["errors"]:
                        error_messages = [
                            e.get("message", str(e)) for e in json_data["errors"]
                        ]
                        raise ShopifyBulkGraphQLError(
                            f"GraphQL root errors: {'; '.join(error_messages)}"
                        )

                    return json_data

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if not retry or attempt > self.MAX_RETRY_ATTEMPTS:
                    raise ShopifyBulkApiError(
                        f"Network error after {attempt} attempts: {e}"
                    )

                delay = self._calculate_backoff(attempt)
                self.logger.warning(
                    f"Network error: {e}, backoff={delay:.2f}s, attempt={attempt}"
                )
                await asyncio.sleep(delay)
                continue

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter.

        Args:
            attempt: Current retry attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        delay = min(
            self.RETRY_BASE_DELAY * (self.RETRY_MULTIPLIER ** (attempt - 1)),
            self.RETRY_MAX_DELAY,
        )
        jitter = random.uniform(0, self.RETRY_JITTER_MS / 1000.0)
        return delay + jitter

    async def _refresh_lock_ttl(self) -> None:
        """Extend Redis lock TTL to prevent expiry during long-running polls."""
        if self._current_lock:
            try:
                await self._current_lock.reacquire()
                self.logger.debug(
                    f"Refreshed bulk lock TTL for shop={self.shop_domain}"
                )
            except Exception as e:
                self.logger.error(f"Failed to refresh lock TTL: {e}")

    async def _release_lock_best_effort(self) -> None:
        """Release Redis lock with error suppression."""
        if self._current_lock:
            try:
                await self._current_lock.release()
                self.logger.info(f"Released bulk lock for shop={self.shop_domain}")
            except Exception as e:
                self.logger.error(f"Failed to release lock: {e}")
            finally:
                self._current_lock = None

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        """Safely convert value to int or None."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
