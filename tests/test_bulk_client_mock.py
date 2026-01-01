"""Unit tests for ShopifyBulkClient (mocked, no real API calls)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.apeg_core.schemas.bulk_ops import BulkOperation
from src.apeg_core.shopify.bulk_client import ShopifyBulkClient
from src.apeg_core.shopify.exceptions import (
    ShopifyBulkApiError,
    ShopifyBulkGraphQLError,
    ShopifyBulkJobLockedError,
)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    return redis


@pytest.fixture
def mock_session():
    """Mock aiohttp ClientSession."""
    session = MagicMock()
    return session


@pytest.fixture
def bulk_client(mock_session, mock_redis):
    """Instantiate ShopifyBulkClient with mocks."""
    return ShopifyBulkClient(
        shop_domain="test-shop.myshopify.com",
        admin_access_token="shpat_fake_token",
        api_version="2024-10",
        session=mock_session,
        redis=mock_redis,
    )


@pytest.mark.asyncio
async def test_submit_job_success(bulk_client, mock_redis):
    """Test successful bulk job submission."""
    # Mock lock acquisition
    mock_lock = AsyncMock()
    mock_lock.acquire.return_value = True

    with patch("src.apeg_core.shopify.bulk_client.AsyncRedisLock", return_value=mock_lock):
        # Mock GraphQL response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()  # Sync method in aiohttp
        mock_response.json.return_value = {
            "data": {
                "bulkOperationRunQuery": {
                    "bulkOperation": {
                        "id": "gid://shopify/BulkOperation/123",
                        "status": "CREATED",
                    },
                    "userErrors": [],
                }
            }
        }
        mock_response.__aenter__.return_value = mock_response
        bulk_client.session.post.return_value = mock_response

        # Execute
        result = await bulk_client.submit_job("{ products { edges { node { id } } } }")

        # Verify
        assert result.id == "gid://shopify/BulkOperation/123"
        assert result.status == "CREATED"
        assert mock_lock.acquire.called


@pytest.mark.asyncio
async def test_submit_job_lock_failure(bulk_client):
    """Test submit_job raises ShopifyBulkJobLockedError when lock unavailable."""
    mock_lock = AsyncMock()
    mock_lock.acquire.return_value = False

    with patch("src.apeg_core.shopify.bulk_client.AsyncRedisLock", return_value=mock_lock):
        with pytest.raises(ShopifyBulkJobLockedError) as exc_info:
            await bulk_client.submit_job("{ products { edges { node { id } } } }")

        assert "test-shop.myshopify.com" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_job_graphql_user_errors(bulk_client):
    """Test submit_job raises ShopifyBulkGraphQLError on userErrors."""
    mock_lock = AsyncMock()
    mock_lock.acquire.return_value = True

    with patch("src.apeg_core.shopify.bulk_client.AsyncRedisLock", return_value=mock_lock):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()  # Sync method in aiohttp
        mock_response.json.return_value = {
            "data": {
                "bulkOperationRunQuery": {
                    "bulkOperation": None,
                    "userErrors": [{"field": "query", "message": "Invalid query syntax"}],
                }
            }
        }
        mock_response.__aenter__.return_value = mock_response
        bulk_client.session.post.return_value = mock_response

        with pytest.raises(ShopifyBulkGraphQLError) as exc_info:
            await bulk_client.submit_job("invalid query")

        assert "Invalid query syntax" in str(exc_info.value)
        # Verify lock was released
        assert mock_lock.release.called


@pytest.mark.asyncio
async def test_poll_status_completed(bulk_client):
    """Test poll_status returns BulkOperation when status=COMPLETED."""
    # Capture mock lock reference BEFORE poll_status clears it
    mock_lock = AsyncMock()
    bulk_client._current_lock = mock_lock

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()  # Sync method in aiohttp
    mock_response.json.return_value = {
        "data": {
            "node": {
                "id": "gid://shopify/BulkOperation/123",
                "status": "COMPLETED",
                "url": "https://storage.shopifycloud.com/result.jsonl",
                "objectCount": "500",
                "errorCode": None,
                "partialDataUrl": None,
            }
        }
    }
    mock_response.__aenter__.return_value = mock_response
    bulk_client.session.post.return_value = mock_response

    result = await bulk_client.poll_status(
        "gid://shopify/BulkOperation/123",
        poll_interval=0.01,
        timeout=5,
    )

    assert result.status == "COMPLETED"
    assert result.url == "https://storage.shopifycloud.com/result.jsonl"
    assert result.object_count == 500
    # Assert on captured reference (bulk_client._current_lock is now None after release)
    assert mock_lock.release.called
    assert bulk_client._current_lock is None  # Verify lock was properly cleared


@pytest.mark.asyncio
async def test_poll_status_completed_missing_url(bulk_client):
    """Test poll_status raises error when COMPLETED but url is missing."""
    bulk_client._current_lock = AsyncMock()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()  # Sync method in aiohttp
    mock_response.json.return_value = {
        "data": {
            "node": {
                "id": "gid://shopify/BulkOperation/123",
                "status": "COMPLETED",
                "url": None,
                "objectCount": "500",
                "errorCode": None,
                "partialDataUrl": None,
            }
        }
    }
    mock_response.__aenter__.return_value = mock_response
    bulk_client.session.post.return_value = mock_response

    with pytest.raises(ShopifyBulkApiError) as exc_info:
        await bulk_client.poll_status(
            "gid://shopify/BulkOperation/123",
            poll_interval=0.01,
            timeout=5,
        )

    assert "url missing" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_poll_status_failed_with_partial_data(bulk_client):
    """Test poll_status raises error with partial_data_url on FAILED status."""
    bulk_client._current_lock = AsyncMock()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()  # Sync method in aiohttp
    mock_response.json.return_value = {
        "data": {
            "node": {
                "id": "gid://shopify/BulkOperation/123",
                "status": "FAILED",
                "url": None,
                "objectCount": "250",
                "errorCode": "TIMEOUT",
                "partialDataUrl": "https://storage.shopifycloud.com/partial.jsonl",
            }
        }
    }
    mock_response.__aenter__.return_value = mock_response
    bulk_client.session.post.return_value = mock_response

    with pytest.raises(ShopifyBulkApiError) as exc_info:
        await bulk_client.poll_status(
            "gid://shopify/BulkOperation/123",
            poll_interval=0.01,
            timeout=5,
        )

    error_message = str(exc_info.value)
    assert "FAILED" in error_message
    assert "TIMEOUT" in error_message
    assert "partial.jsonl" in error_message


@pytest.mark.asyncio
async def test_http_429_with_retry_after(bulk_client):
    """Test _post_graphql respects Retry-After header on 429."""
    # First call: 429 with Retry-After
    mock_resp_429 = AsyncMock()
    mock_resp_429.status = 429
    mock_resp_429.headers = {"Retry-After": "0.1"}
    mock_resp_429.text.return_value = "Rate limited"
    mock_resp_429.__aenter__.return_value = mock_resp_429

    # Second call: 200 success
    mock_resp_200 = AsyncMock()
    mock_resp_200.status = 200
    mock_resp_200.json.return_value = {"data": {"test": "success"}}
    mock_resp_200.raise_for_status = MagicMock()
    mock_resp_200.__aenter__.return_value = mock_resp_200

    bulk_client.session.post.side_effect = [mock_resp_429, mock_resp_200]

    result = await bulk_client._post_graphql({"query": "test"}, retry=True)

    assert result == {"data": {"test": "success"}}
    assert bulk_client.session.post.call_count == 2


@pytest.mark.asyncio
async def test_http_4xx_non_retryable(bulk_client):
    """Test _post_graphql raises immediately on 4xx (except 429)."""
    mock_response = AsyncMock()
    mock_response.status = 403
    mock_response.text.return_value = "Forbidden"
    mock_response.__aenter__.return_value = mock_response

    bulk_client.session.post.return_value = mock_response

    with pytest.raises(ShopifyBulkApiError) as exc_info:
        await bulk_client._post_graphql({"query": "test"}, retry=True)

    assert "403" in str(exc_info.value)
    assert "non-retryable" in str(exc_info.value)
    assert bulk_client.session.post.call_count == 1  # No retry
