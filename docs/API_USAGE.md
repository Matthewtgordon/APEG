# APEG API Usage Guide

## Overview
The APEG API provides HTTP endpoints for n8n to enqueue long-running Shopify bulk operations without blocking.

IMPORTANT LIMITATION: Background tasks run in-process and are not persisted. Server restarts will interrupt running jobs. This is acceptable for Phase 3 development; consider upgrading to a persistent queue (Celery, RQ) for production.

## Base URL
```
http://localhost:8000  # Development
https://apeg.yourdomain.com  # Production
```

## Authentication

All endpoints require API key authentication via header:
```
X-APEG-API-KEY: your-secret-api-key
```

**What is APEG_API_KEY?**

`APEG_API_KEY` is a **user-defined secret string** configured on the APEG server (environment variable `APEG_API_KEY`). **Treat it like a password.**

- **Format:** 32+ character random string (recommended: hex-encoded)
- **Generation:** `openssl rand -hex 32`
- **Example formats (non-functional):**
  - `apeg_sk_live_3f6b9c2a8d1e4c7f9a0b1c2d3e4f5a6b`
  - `apeg_key_demo_abc123def456ghi789jkl012mno345pq`
- **Security:** Do NOT reuse Shopify access tokens. Do NOT commit to repo.

The APEG FastAPI server validates incoming requests by comparing the `X-APEG-API-KEY` header value against the `APEG_API_KEY` environment variable.

**Missing or invalid API keys return 401 Unauthorized** with `WWW-Authenticate: API-Key` header.

## Endpoints

### POST /api/v1/jobs/seo-update
Submit SEO and tag update job for background processing.

Request:
```json
{
  "run_id": "n8n-2025-12-30T120000Z",
  "shop_domain": "your-store.myshopify.com",
  "dry_run": false,
  "products": [
    {
      "product_id": "gid://shopify/Product/1234567890",
      "tags_add": ["apeg_seo", "holiday_2024"],
      "tags_remove": ["old_tag"],
      "seo": {
        "title": "New SEO Title",
        "description": "New SEO Description"
      }
    }
  ]
}
```

Response: 202 Accepted
```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "queued",
  "run_id": "n8n-2025-12-30T120000Z",
  "received_count": 1
}
```

Validation Rules:
- shop_domain must match configured SHOPIFY_STORE_DOMAIN
- products must be non-empty array
- product_id must be valid Shopify GID format
- tags_add and tags_remove are merged with current tags (safe-write)

Error Responses:
- 401 Unauthorized: Missing or invalid API key
- 400 Bad Request: Validation failure (shop_domain mismatch, empty products)
- 422 Unprocessable Entity: Invalid request schema

## Safe Write Behavior

### Tag Merging
Tags are merged using set operations:
```python
final_tags = (current_tags | tags_add) - tags_remove
```

Example:
- Current tags: ["tag1", "tag2", "tag3"]
- Request: tags_add=["tag4"], tags_remove=["tag2"]
- Result: ["tag1", "tag3", "tag4"]

### SEO Updates
- If seo is provided, it replaces current SEO fields
- If seo is omitted, current SEO is preserved

## Dry Run Mode
Set "dry_run": true to validate request without executing Shopify writes:
- Validates payload schema
- Logs intended actions
- Returns 202 immediately
- No Shopify API calls made

## Background Execution
Jobs execute asynchronously after 202 response:
1. Fetch current product state (tags + SEO)
2. Merge tags using safe-write algorithm
3. Submit Shopify bulk mutation (staged upload)
4. Poll until completion
5. Log outcome (success/failure)

Job failures are logged server-side; no status callback currently implemented.

RELIABILITY NOTE: Background tasks are in-process. Long-running jobs may be interrupted by server restarts. Jobs are not persisted or retried automatically.

## Example: n8n HTTP Request Node

See complete n8n workflow configuration: [docs/N8N_WORKFLOW_CONFIG.md](./N8N_WORKFLOW_CONFIG.md)

Quick Reference - Critical Typing Issue:

When mapping `products` field in n8n, ensure it sends as a JSON Array (not a string):
```javascript
{{ typeof $json.products === 'string' ? JSON.parse($json.products) : $json.products }}
```

This prevents 422 errors from incorrect type serialization.

## Example: curl
```bash
curl -sS -X POST "http://localhost:8000/api/v1/jobs/seo-update" \
  -H "Content-Type: application/json" \
  -H "X-APEG-API-KEY: ${APEG_API_KEY}" \
  -d '{
    "run_id": "manual-test-2025-12-30",
    "shop_domain": "your-demo-store.myshopify.com",
    "dry_run": false,
    "products": [
      {
        "product_id": "gid://shopify/Product/1234567890",
        "tags_add": ["apeg_seo"],
        "tags_remove": [],
        "seo": {
          "title": "Beautiful Handcrafted Jewelry",
          "description": "Discover unique artisan jewelry pieces."
        }
      }
    ]
  }'
```

## Running the Server

### Development
CRITICAL: Use PYTHONPATH=. to avoid import errors:
```bash
# Load environment
set -a; source .env; set +a

# Run with auto-reload (PYTHONPATH required for src.* imports)
PYTHONPATH=. uvicorn src.apeg_core.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
# Run with multiple workers
PYTHONPATH=. uvicorn src.apeg_core.main:app --workers 4 --host 0.0.0.0 --port 8000
```

## Health Check
FastAPI provides automatic documentation:
- Interactive docs: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json
