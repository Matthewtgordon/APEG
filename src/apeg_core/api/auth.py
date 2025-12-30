"""FastAPI authentication dependencies for APEG API."""
import os
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader


# Define API key header security scheme
api_key_header = APIKeyHeader(name="X-APEG-API-KEY", auto_error=False)


async def require_api_key(
    api_key: Annotated[str | None, Security(api_key_header)] = None
) -> str:
    """Validate API key from request header.

    Args:
        api_key: API key from X-APEG-API-KEY header (optional)

    Returns:
        Validated API key

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    expected_key = os.getenv("APEG_API_KEY")

    if not expected_key:
        raise RuntimeError("APEG_API_KEY environment variable not configured")

    # Return 401 for both missing AND invalid keys
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "API-Key"},
        )

    return api_key
