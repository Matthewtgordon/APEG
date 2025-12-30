"""APEG FastAPI application entry point."""
import logging

from fastapi import FastAPI

from .api.routes import router as api_router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="APEG API",
        version="0.1.0",
        description="Async Product Enhancement Gateway for Shopify bulk operations",
    )

    app.include_router(api_router)

    return app


app = create_app()
