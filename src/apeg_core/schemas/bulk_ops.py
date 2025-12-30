"""Pydantic models for Shopify Bulk Operations API responses."""
from typing import Optional

from pydantic import BaseModel, Field


class BulkOperation(BaseModel):
    """Shopify BulkOperation response model."""

    id: str = Field(
        ..., description="GID of bulk operation (e.g., gid://shopify/BulkOperation/123)"
    )
    status: str = Field(
        ...,
        description="CREATED|RUNNING|COMPLETED|FAILED|CANCELING|CANCELED|EXPIRED",
    )
    url: Optional[str] = Field(
        None, description="JSONL download URL (present when COMPLETED)"
    )
    object_count: Optional[int] = Field(None, description="Number of objects processed")
    error_code: Optional[str] = Field(None, description="Error code if FAILED")
    partial_data_url: Optional[str] = Field(
        None, description="Partial JSONL URL if job failed mid-run"
    )

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

    @property
    def staged_upload_path(self) -> str:
        """Extract the 'key' parameter for stagedUploadPath."""
        for param in self.parameters:
            if param.name == "key":
                return param.value
        raise ValueError("Missing 'key' parameter in stagedTarget")


class ProductSEO(BaseModel):
    """SEO fields for product update."""

    title: Optional[str] = None
    description: Optional[str] = None


class ProductUpdateSpec(BaseModel):
    """Product update specification (input to safe-write merger)."""

    product_id: str = Field(..., description="Product GID")
    tags_add: list[str] = Field(default_factory=list, description="Tags to add")
    tags_remove: list[str] = Field(default_factory=list, description="Tags to remove")
    tags_full: Optional[list[str]] = Field(None, description="Override mode (discouraged)")
    seo: Optional[ProductSEO] = Field(None, description="SEO fields")


class ProductUpdateInput(BaseModel):
    """Product update payload for bulk mutation JSONL."""

    id: str = Field(..., description="Product GID")
    tags: Optional[list[str]] = Field(None, description="Complete merged tag list")
    seo: Optional[ProductSEO] = Field(None, description="SEO title/description")

    def to_jsonl_dict(self) -> dict:
        """Convert to JSONL line dict with 'product' key."""
        payload = {"id": self.id}
        if self.tags is not None:
            payload["tags"] = self.tags
        if self.seo is not None:
            payload["seo"] = self.seo.model_dump(exclude_none=True)
        return {"product": payload}


class BulkOperationRef(BaseModel):
    """Reference to submitted bulk operation."""

    bulk_op_id: str
    run_id: str
    shop_domain: str
