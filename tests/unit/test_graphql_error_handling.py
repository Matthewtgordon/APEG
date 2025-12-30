"""Unit tests for GraphQL root-level error handling (critical bug fix)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.apeg_core.shopify.bulk_client import ShopifyBulkClient
from src.apeg_core.shopify.exceptions import ShopifyBulkGraphQLError


@pytest.mark.asyncio
async def test_root_level_errors_trigger_exception():
    """Test that root ["errors"] raises ShopifyBulkGraphQLError before data access."""
    mock_session = MagicMock()
    mock_redis = AsyncMock()

    client = ShopifyBulkClient(
        shop_domain="test.myshopify.com",
        admin_access_token="test-token",
        api_version="2024-10",
        session=mock_session,
        redis=mock_redis,
    )

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "errors": [
            {"message": "Access denied to resource"},
            {"message": "Insufficient permissions"},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_response.__aenter__.return_value = mock_response

    mock_session.post.return_value = mock_response

    with pytest.raises(ShopifyBulkGraphQLError) as exc_info:
        await client._post_graphql({"query": "test"})

    assert "Access denied" in str(exc_info.value)
    assert "Insufficient permissions" in str(exc_info.value)
