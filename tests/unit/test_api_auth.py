"""Unit tests for API authentication."""
import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.apeg_core.api.auth import require_api_key


@pytest.mark.asyncio
async def test_require_api_key_success():
    """Test API key validation succeeds with correct key."""
    with patch.dict(os.environ, {"APEG_API_KEY": "test-secret-key"}):
        result = await require_api_key("test-secret-key")
        assert result == "test-secret-key"


@pytest.mark.asyncio
async def test_require_api_key_invalid():
    """Test API key validation fails with incorrect key (401)."""
    with patch.dict(os.environ, {"APEG_API_KEY": "correct-key"}):
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key("wrong-key")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "API-Key"}


@pytest.mark.asyncio
async def test_require_api_key_missing():
    """Test API key validation fails when header is missing (401)."""
    with patch.dict(os.environ, {"APEG_API_KEY": "test-key"}):
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(None)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_api_key_not_configured():
    """Test API key validation fails when APEG_API_KEY not set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError) as exc_info:
            await require_api_key("any-key")

        assert "APEG_API_KEY environment variable not configured" in str(
            exc_info.value
        )
