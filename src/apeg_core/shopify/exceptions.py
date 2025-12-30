"""Custom exceptions for Shopify Bulk Client."""


class ShopifyBulkClientError(Exception):
    """Base exception for all Shopify Bulk Client errors."""


class ShopifyBulkJobLockedError(ShopifyBulkClientError):
    """Raised when Redis lock cannot be acquired (another job in progress)."""

    def __init__(self, shop_domain: str, lock_key: str):
        self.shop_domain = shop_domain
        self.lock_key = lock_key
        super().__init__(
            f"Bulk operation lock already held for shop={shop_domain}, key={lock_key}"
        )


class ShopifyBulkApiError(ShopifyBulkClientError):
    """Raised for Shopify API errors (HTTP 4xx/5xx, missing data)."""


class ShopifyBulkGraphQLError(ShopifyBulkClientError):
    """Raised when GraphQL returns userErrors."""

    def __init__(self, user_errors: list):
        self.user_errors = user_errors
        super().__init__(f"GraphQL userErrors: {user_errors}")


class ShopifyBulkMutationLockedError(ShopifyBulkClientError):
    """Raised when bulk mutation lock cannot be acquired."""

    def __init__(self, shop_domain: str, lock_key: str):
        self.shop_domain = shop_domain
        self.lock_key = lock_key
        super().__init__(
            f"Bulk mutation lock already held for shop={shop_domain}, key={lock_key}"
        )


class ShopifyStagedUploadError(ShopifyBulkClientError):
    """Raised for staged upload failures (multipart POST errors)."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"Staged upload failed: HTTP {status}, body={body[:200]}")
