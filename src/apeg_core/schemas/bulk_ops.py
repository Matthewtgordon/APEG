"""Pydantic models for Shopify Bulk Operations API responses."""
from typing import Optional

from pydantic import BaseModel, Field


class BulkOperation(BaseModel):
    """Shopify BulkOperation response model."""

    id: str = Field(..., description="GID of bulk operation (e.g., gid://shopify/BulkOperation/123)")
    status: str = Field(
        ...,
        description="CREATED|RUNNING|COMPLETED|FAILED|CANCELING|CANCELED|EXPIRED",
    )
    url: Optional[str] = Field(
        None, description="JSONL download URL (present when COMPLETED)"
    )
    object_count: Optional[int] = Field(None, description="Number of objects processed")
    error_code: Optional[str] = Field(None, description="Error code if FAILED")
    partial_data_url: Optional[str] = Field(None, description="Partial JSONL URL if job failed mid-run")

    @property
    def is_terminal(self) -> bool:
        """Check if operation has reached terminal state."""
        return self.status in {"COMPLETED", "FAILED", "CANCELED", "EXPIRED"}

    @property
    def is_success(self) -> bool:
        """Check if operation completed successfully."""
        return self.status == "COMPLETED"
