"""Unit tests for API routes."""

import pytest
from fastapi.testclient import TestClient

from src.apeg_core.main import create_app


@pytest.fixture
def client(monkeypatch):
    """Create test client with mocked environment."""
    monkeypatch.setenv("APEG_API_KEY", "test-api-key")
    monkeypatch.setenv("SHOPIFY_STORE_DOMAIN", "test-shop.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_test")
    monkeypatch.setenv("SHOPIFY_API_VERSION", "2024-10")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_seo_update_job_missing_api_key(client):
    """Test endpoint rejects request without API key (401)."""
    response = client.post(
        "/api/v1/jobs/seo-update",
        json={
            "run_id": "test-run-1",
            "shop_domain": "test-shop.myshopify.com",
            "products": [
                {
                    "product_id": "gid://shopify/Product/123",
                    "tags_add": ["test-tag"],
                    "tags_remove": [],
                }
            ],
        },
    )

    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_seo_update_job_invalid_api_key(client):
    """Test endpoint rejects request with invalid API key."""
    response = client.post(
        "/api/v1/jobs/seo-update",
        json={
            "run_id": "test-run-1",
            "shop_domain": "test-shop.myshopify.com",
            "products": [
                {
                    "product_id": "gid://shopify/Product/123",
                    "tags_add": ["test-tag"],
                    "tags_remove": [],
                }
            ],
        },
        headers={"X-APEG-API-KEY": "wrong-key"},
    )

    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_seo_update_job_shop_domain_mismatch(client):
    """Test endpoint rejects mismatched shop_domain."""
    response = client.post(
        "/api/v1/jobs/seo-update",
        json={
            "run_id": "test-run-1",
            "shop_domain": "wrong-shop.myshopify.com",
            "products": [
                {
                    "product_id": "gid://shopify/Product/123",
                    "tags_add": ["test-tag"],
                    "tags_remove": [],
                }
            ],
        },
        headers={"X-APEG-API-KEY": "test-api-key"},
    )

    assert response.status_code == 400
    assert "shop_domain mismatch" in response.json()["detail"]


def test_seo_update_job_empty_products(client):
    """Test endpoint rejects empty products list."""
    response = client.post(
        "/api/v1/jobs/seo-update",
        json={
            "run_id": "test-run-1",
            "shop_domain": "test-shop.myshopify.com",
            "products": [],
        },
        headers={"X-APEG-API-KEY": "test-api-key"},
    )

    assert response.status_code == 400
    assert "products must be non-empty" in response.json()["detail"]


def test_seo_update_job_success_queued(client):
    """Test endpoint returns 202 with job_id for valid request."""
    response = client.post(
        "/api/v1/jobs/seo-update",
        json={
            "run_id": "test-run-success",
            "shop_domain": "test-shop.myshopify.com",
            "products": [
                {
                    "product_id": "gid://shopify/Product/123",
                    "tags_add": ["apeg-test"],
                    "tags_remove": [],
                    "seo": {"title": "Test Title", "description": "Test Desc"},
                }
            ],
            "dry_run": True,
        },
        headers={"X-APEG-API-KEY": "test-api-key"},
    )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["run_id"] == "test-run-success"
    assert data["received_count"] == 1


def test_seo_update_job_dry_run(client):
    """Test endpoint accepts dry_run flag."""
    response = client.post(
        "/api/v1/jobs/seo-update",
        json={
            "run_id": "test-run-dry",
            "shop_domain": "test-shop.myshopify.com",
            "products": [
                {
                    "product_id": "gid://shopify/Product/123",
                    "tags_add": ["dry-run-tag"],
                    "tags_remove": [],
                }
            ],
            "dry_run": True,
        },
        headers={"X-APEG-API-KEY": "test-api-key"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
