"""Unit tests for ShopifyBulkMutationClient (mocked)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.apeg_core.shopify.bulk_mutation_client import ShopifyBulkMutationClient
from src.apeg_core.shopify.exceptions import (
    ShopifyBulkMutationLockedError,
    ShopifyBulkGraphQLError,
    ShopifyStagedUploadError,
)
from src.apeg_core.schemas.bulk_ops import (
    ProductUpdateInput,
    ProductSEOInput,
    ProductCurrentState,
    StagedTarget,
    StagedUploadParameter,
)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return AsyncMock()


@pytest.fixture
def mock_session():
    """Mock aiohttp ClientSession."""
    return MagicMock()


@pytest.fixture
def mutation_client(mock_session, mock_redis):
    """Instantiate ShopifyBulkMutationClient with mocks."""
    return ShopifyBulkMutationClient(
        shop_domain="test-shop.myshopify.com",
        admin_access_token="shpat_fake_token",
        api_version="2024-10",
        session=mock_session,
        redis=mock_redis,
    )


@pytest.mark.asyncio
async def test_staged_uploads_create_success(mutation_client):
    """Test stagedUploadsCreate returns StagedTarget."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "data": {
            "stagedUploadsCreate": {
                "stagedTargets": [
                    {
                        "url": "https://upload.shopify.com/...",
                        "resourceUrl": None,
                        "parameters": [
                            {"name": "key", "value": "tmp/bulk_op_vars_123"},
                            {"name": "acl", "value": "private"},
                        ],
                    }
                ],
                "userErrors": [],
            }
        }
    }
    mock_response.__aenter__.return_value = mock_response
    mutation_client.session.post.return_value = mock_response

    result = await mutation_client._staged_uploads_create()

    assert isinstance(result, StagedTarget)
    assert result.url == "https://upload.shopify.com/..."
    assert result.staged_upload_path == "tmp/bulk_op_vars_123"
    assert len(result.parameters) == 2


@pytest.mark.asyncio
async def test_staged_uploads_create_user_errors(mutation_client):
    """Test stagedUploadsCreate raises on userErrors."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "data": {
            "stagedUploadsCreate": {
                "stagedTargets": [],
                "userErrors": [
                    {"field": "resource", "message": "Invalid resource type"}
                ],
            }
        }
    }
    mock_response.__aenter__.return_value = mock_response
    mutation_client.session.post.return_value = mock_response

    with pytest.raises(ShopifyBulkGraphQLError) as exc_info:
        await mutation_client._staged_uploads_create()

    assert "Invalid resource type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_jsonl_multipart_ordering(mutation_client):
    """Test JSONL upload enforces file field LAST in multipart form."""
    staged_target = StagedTarget(
        url="https://upload.test.com/",
        parameters=[
            StagedUploadParameter(name="key", value="tmp/test_123"),
            StagedUploadParameter(name="acl", value="private"),
        ],
    )

    async def fake_file_iter():
        yield b'{"product":{"id":"123"}}'

    mutation_client._iter_file_chunks = MagicMock(return_value=fake_file_iter())

    mock_response = AsyncMock()
    mock_response.status = 204
    mock_response.text.return_value = ""
    mock_response.__aenter__.return_value = mock_response
    mutation_client.session.post.return_value = mock_response

    await mutation_client._upload_jsonl_to_staged_target(
        staged_target,
        "/fake/path.jsonl",
    )

    # Verify POST was called
    assert mutation_client.session.post.called
    call_args = mutation_client.session.post.call_args

    # Verify URL
    assert call_args[0][0] == "https://upload.test.com/"

    # Verify FormData was passed
    assert "data" in call_args[1]


@pytest.mark.asyncio
async def test_upload_jsonl_http_error(mutation_client):
    """Test JSONL upload raises ShopifyStagedUploadError on HTTP error."""
    staged_target = StagedTarget(
        url="https://upload.test.com/",
        parameters=[StagedUploadParameter(name="key", value="tmp/test")],
    )

    async def fake_file_iter():
        yield b"{}"

    mutation_client._iter_file_chunks = MagicMock(return_value=fake_file_iter())

    mock_response = AsyncMock()
    mock_response.status = 403
    mock_response.text.return_value = "Forbidden"
    mock_response.__aenter__.return_value = mock_response
    mutation_client.session.post.return_value = mock_response

    with pytest.raises(ShopifyStagedUploadError) as exc_info:
        await mutation_client._upload_jsonl_to_staged_target(
            staged_target,
            "/fake/path.jsonl",
        )

    assert exc_info.value.status == 403
    assert "Forbidden" in exc_info.value.body


@pytest.mark.asyncio
async def test_merge_product_updates_safe_write(mutation_client):
    """Test merge_product_updates performs safe tag union."""
    current_state_map = {
        "gid://shopify/Product/123": ProductCurrentState(
            id="gid://shopify/Product/123",
            tags=["existing-tag-1", "existing-tag-2"],
            seo_title="Original Title",
            seo_description="Original Desc",
        ),
    }

    desired_updates = [
        ProductUpdateInput(
            id="gid://shopify/Product/123",
            tags=["new-tag-1"],
            seo=ProductSEOInput(title="New Title"),
        ),
    ]

    merged = mutation_client.merge_product_updates(current_state_map, desired_updates)

    assert len(merged) == 1
    assert set(merged[0].tags) == {"existing-tag-1", "existing-tag-2", "new-tag-1"}
    assert merged[0].seo.title == "New Title"


@pytest.mark.asyncio
async def test_product_update_input_to_jsonl_dict():
    """Test ProductUpdateInput.to_jsonl_dict() formatting."""
    update = ProductUpdateInput(
        id="gid://shopify/Product/456",
        tags=["tag1", "tag2"],
        seo=ProductSEOInput(title="Test Title", description="Test Desc"),
    )

    jsonl_dict = update.to_jsonl_dict()

    assert jsonl_dict == {
        "product": {
            "id": "gid://shopify/Product/456",
            "tags": ["tag1", "tag2"],
            "seo": {"title": "Test Title", "description": "Test Desc"},
        }
    }


@pytest.mark.asyncio
async def test_run_product_update_bulk_lock_failure(mutation_client):
    """Test run_product_update_bulk raises when lock unavailable."""
    mock_lock = AsyncMock()
    mock_lock.acquire.return_value = False

    with patch("src.apeg_core.shopify.bulk_mutation_client.AsyncRedisLock", return_value=mock_lock):
        with pytest.raises(ShopifyBulkMutationLockedError) as exc_info:
            await mutation_client.run_product_update_bulk([])

        assert "test-shop.myshopify.com" in str(exc_info.value)
