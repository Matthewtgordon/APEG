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


class StagedUploadParameter(BaseModel):
    """Shopify staged upload form parameter."""

    name: str
    value: str


class StagedTarget(BaseModel):
    """Shopify staged upload target response."""

    url: str = Field(..., description="Multipart upload URL")
    resource_url: Optional[str] = Field(None, description="Resource URL after upload")
    parameters: list[StagedUploadParameter] = Field(default_factory=list)

    def get_parameter_value(self, name: str) -> Optional[str]:
        """Extract parameter value by name."""
        for param in self.parameters:
            if param.name == name:
                return param.value
        return None

    @property
    def staged_upload_path(self) -> str:
        """Extract the 'key' parameter for stagedUploadPath."""
        key = self.get_parameter_value("key")
        if not key:
            raise ValueError("Missing 'key' parameter in stagedTarget")
        return key


class ProductSEOInput(BaseModel):
    """SEO fields for product update."""

    title: Optional[str] = None
    description: Optional[str] = None


class ProductUpdateInput(BaseModel):
    """Product update payload for bulk mutation JSONL."""

    id: str = Field(..., description="Product GID (e.g., gid://shopify/Product/123)")
    tags: Optional[list[str]] = Field(None, description="Complete merged tag list")
    seo: Optional[ProductSEOInput] = Field(None, description="SEO title/description")

    def to_jsonl_dict(self) -> dict:
        """Convert to JSONL line dict with 'product' key."""
        payload = {"id": self.id}
        if self.tags is not None:
            payload["tags"] = self.tags
        if self.seo is not None:
            payload["seo"] = self.seo.model_dump(exclude_none=True)
        return {"product": payload}


class ProductCurrentState(BaseModel):
    """Current product state for safe-write merge."""

    id: str
    tags: list[str] = Field(default_factory=list)
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
