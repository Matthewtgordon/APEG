# n8n Workflow Configuration Guide - APEG Integration

> **📍 Quick Links:** [Main README](../README.md) | [API Usage](API_USAGE.md) | [Environment Setup](ENVIRONMENT.md) | [Docs Index](README.md)

**Purpose:** Configure n8n to trigger APEG SEO update jobs  
**Last Updated:** 2025-12-30

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#1-prerequisite-n8n-environment-variables)
- [Create n8n Credential](#2-create-n8n-credential-header-auth)
- [HTTP Request Node Configuration](#3-http-request-node-configuration-apeg-api-call)
- [Array Typing Issue (Critical)](#4-array-typing-issue-critical)
- [Testing](#5-testing-workflow-execution)
- [Troubleshooting](#6-troubleshooting)

---

## Overview

This guide configures an n8n HTTP Request workflow to submit SEO/tag update jobs to the APEG FastAPI endpoint (`POST /api/v1/jobs/seo-update`).

Key Behavior:
- APEG returns 202 Accepted immediately (does not wait for Shopify completion)
- n8n treats 202 as "job queued successfully"
- No completion callback in Phase 3 (future enhancement)

---

## 1. PREREQUISITE: n8n Environment Variables

Set these in your n8n deployment environment (not APEG's .env):
```bash
# Required
APEG_API_BASE_URL=http://192.168.1.50:8000  # Use LAN IP or Tailscale IP (NOT localhost if in Docker)
SHOPIFY_STORE_DOMAIN=your-demo-store.myshopify.com

# Optional (credential encryption - HIGHLY RECOMMENDED for self-hosted)
N8N_ENCRYPTION_KEY=your-random-32-char-encryption-key
```

Docker Network Configuration:

If n8n runs in Docker, DO NOT use `localhost` to reach APEG on the host machine.

Choose one:
- LAN IP (recommended): `http://192.168.1.50:8000` (replace with your host's actual LAN IP)
- Tailscale/VPN IP: `http://100.x.x.x:8000` (if using Tailscale)
- host.docker.internal: May require `--add-host=host.docker.internal:host-gateway` (Linux only, not recommended)

APEG server must listen on `0.0.0.0` (not `127.0.0.1`) for external connections:
```bash
PYTHONPATH=. uvicorn src.apeg_core.main:app --host 0.0.0.0 --port 8000
```

---

## 2. CREATE N8N CREDENTIAL (Header Auth)

DO NOT hardcode API keys in workflow JSON.

Steps:
1. Navigate to: Credentials -> + New Credential
2. In the search box, type "HTTP Request" and select it
3. Inside the credential configuration modal:
   - Credential Name: `APEG API Key (DEMO)` or `APEG API Key (LIVE)`
   - Authentication: Select `Header Auth` from dropdown
   - Header Name: `X-APEG-API-KEY`
   - Header Value: Paste your APEG_API_KEY value
     - Best practice: Use n8n expression if available: `{{ $env.APEG_API_KEY }}`
     - Otherwise, paste the actual key securely
4. Click Save

Important: Header Auth is NOT a standalone credential type. It's a configuration option within the generic HTTP Request credential.

---

## 3. HTTP REQUEST NODE CONFIGURATION

### Basic Settings

Method: `POST`

URL:
```
{{ $env.APEG_API_BASE_URL }}/api/v1/jobs/seo-update
```

Authentication: Select the credential you created in Step 2

Send Body: `ON`

Body Content Type: `JSON`

Response Format: `JSON`

Options:
- Include Response Headers and Status (required to capture statusCode)

Timeout: `10000` (10 seconds - API responds immediately with 202)

---

### JSON Body Configuration

CRITICAL: Array Typing Rule

The API expects `products` as a JSON Array (not a string). If your upstream node outputs products as a JSON string, you must parse it.

Safe Expression Pattern:
```javascript
{{ typeof $json.products === 'string' ? JSON.parse($json.products) : $json.products }}
```

Complete Body Structure:
```json
{
  "run_id": "{{ 'n8n-' + $now.setZone('UTC').toISO() }}",
  "shop_domain": "{{ $env.SHOPIFY_STORE_DOMAIN }}",
  "dry_run": false,
  "products": "{{ typeof $json.products === 'string' ? JSON.parse($json.products) : $json.products }}"
}
```

Field Mapping (Expression Mode):

To map fields reliably in n8n:
1. Click the (fx) Expression button in the Value field
2. Clear the expression editor completely
3. Click the desired variable in the left panel to insert it
4. Save

Do NOT drag-and-drop; this can produce malformed expressions depending on n8n version.

---

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `run_id` | string | Yes | Unique identifier for idempotency tracking. Use n8n execution ID pattern. |
| `shop_domain` | string | Yes | Must match APEG's `SHOPIFY_STORE_DOMAIN`. Use env var. |
| `dry_run` | boolean | Yes | `true` = validate only, no Shopify writes. `false` = execute. |
| `products` | array | Yes | Non-empty list of products to update. MUST BE ARRAY, NOT STRING. |
| `products[].product_id` | string | Yes | Shopify GID (e.g., `gid://shopify/Product/123`) |
| `products[].tags_add` | array | No | Tags to add (merged with existing). Default: `[]` |
| `products[].tags_remove` | array | No | Tags to remove from existing. Default: `[]` |
| `products[].seo` | object | No | SEO updates (title/description). |
| `products[].seo.title` | string | No | SEO title |
| `products[].seo.description` | string | No | SEO meta description |

---

## 4. RECOMMENDED WORKFLOW LAYOUT

Minimum Working Workflow:
```
[Manual Trigger]
    ->
[Set Node: Build Payload]
    - run_id: {{ 'n8n-' + $now.setZone('UTC').toISO() }}
    - shop_domain: {{ $env.SHOPIFY_STORE_DOMAIN }}
    - dry_run: false
    - products: [{ product_id: "gid://shopify/Product/123", tags_add: ["test"] }]
    ->
[HTTP Request: POST to APEG]
    - URL: {{ $env.APEG_API_BASE_URL }}/api/v1/jobs/seo-update
    - Auth: HTTP Request credential (Header Auth)
    - Body: JSON (see Section 3)
    ->
[IF Node: Assert 202]
    - Condition: {{ $json.statusCode }} == 202
    ->
[Set Node: Extract Job Info]
    - job_id: {{ $json.body.job_id }}
    - run_id: {{ $json.body.run_id }}
    - status: {{ $json.body.status }}
    - received_count: {{ $json.body.received_count }}
    ->
[Optional: Log to Sheet/Database]
```

---

## 5. END-TO-END VERIFICATION TEST (Dry Run)

Preconditions:
- APEG API running and accessible from n8n
- n8n environment contains `APEG_API_BASE_URL` and `SHOPIFY_STORE_DOMAIN`
- n8n credential configured with valid `APEG_API_KEY`

Workflow Configuration:

1. Manual Trigger outputs:
```json
{
  "run_id": "n8n-e2e-dryrun-001",
  "shop_domain": "your-demo-store.myshopify.com",
  "dry_run": true,
  "products": "[{\"product_id\":\"gid://shopify/Product/1\",\"tags_add\":[\"test-tag\"],\"tags_remove\":[],\"seo\":{\"title\":\"Test Title\",\"description\":\"Test Desc\"}}]"
}
```

2. HTTP Request Node:
   - Method: POST
   - URL: `{{ $env.APEG_API_BASE_URL }}/api/v1/jobs/seo-update`
   - Auth: HTTP Request credential (Header Auth)
   - Body Content Type: JSON
   - Body:
```json
{
  "run_id": "{{ $json.run_id }}",
  "shop_domain": "{{ $json.shop_domain }}",
  "dry_run": "{{ $json.dry_run }}",
  "products": "{{ typeof $json.products === 'string' ? JSON.parse($json.products) : $json.products }}"
}
```

PASS CRITERIA:
- HTTP node returns statusCode = 202
- Response body contains:
  - job_id (UUID format)
  - status: "queued"
  - run_id: "n8n-e2e-dryrun-001"
  - received_count: 1
- Workflow completes immediately (no waiting for Shopify)
- APEG server logs show:
  - "Starting SEO update job: ... dry_run=True"
  - "DRY RUN MODE: Would update 1 products"
  - "Job [job_id] completed (dry run)"

Evidence Required:
- n8n execution success screenshot showing 202 response
- APEG server log excerpt

---

## 6. TROUBLESHOOTING

### Error: "Cannot connect" / ECONNREFUSED

Cause: n8n cannot reach APEG server (network issue)

Fix:
1. If n8n is in Docker and APEG is on host:
   - DO NOT use `localhost` or `127.0.0.1`
   - Use host's LAN IP: `http://192.168.1.50:8000`
   - Or Tailscale IP: `http://100.x.x.x:8000`
2. Verify APEG server is listening on 0.0.0.0:
```bash
   # Check server bind address
   ps aux | rg uvicorn
   # Should show --host 0.0.0.0
```
3. Test connectivity from inside n8n container:
```bash
   docker exec -it n8n curl http://192.168.1.50:8000/docs
   # Should return HTML (or 401 if auth enforced)
```

---

### Error: "Invalid API key" (401)

Cause: Credential mismatch between n8n and APEG server

Fix:
1. Verify APEG server key:
```bash
   echo $APEG_API_KEY
```
2. Verify n8n credential value matches exactly
3. Check for whitespace/newlines in credential value
4. Test with curl:
```bash
   curl -X POST http://192.168.1.50:8000/api/v1/jobs/seo-update \
     -H "X-APEG-API-KEY: ${APEG_API_KEY}" \
     -H "Content-Type: application/json" \
     -d '{"run_id":"test","shop_domain":"demo.myshopify.com","dry_run":true,"products":[]}'
   # Should return 400 (empty products) NOT 401
```

---

### Error: "shop_domain mismatch" (400)

Cause: `shop_domain` in request does not match APEG's `SHOPIFY_STORE_DOMAIN`

Fix:
1. Verify APEG server domain:
```bash
   echo $SHOPIFY_STORE_DOMAIN
```
2. Update n8n env var `SHOPIFY_STORE_DOMAIN` to match
3. Ensure workflow uses: `{{ $env.SHOPIFY_STORE_DOMAIN }}`

---

### Error: 422 Unprocessable Entity (products field)

Cause: `products` sent as a string instead of array

Example of WRONG:
```json
{
  "products": "[{\"product_id\":\"...\"}]"  // STRING - WRONG
}
```

Example of CORRECT:
```json
{
  "products": [{"product_id":"..."}]  // ARRAY - CORRECT
}
```

Fix:
Use the safe expression pattern:
```javascript
{{ typeof $json.products === 'string' ? JSON.parse($json.products) : $json.products }}
```

---

### Success but no Shopify changes

Cause: `dry_run: true` OR background job failed OR writes disabled

Fix:
1. Check body: ensure `dry_run: false`
2. Check APEG server logs for job execution errors
3. Verify APEG server has: `APEG_ALLOW_WRITES=YES`
4. Verify APEG has valid Shopify credentials

---

## 7. PHASE 3 LIMITATIONS

No Status Callback:
- n8n receives 202 immediately
- Job executes in background
- No automatic notification of completion/failure
- Future enhancement: webhook callback endpoint

No Retry on Failure:
- Failed jobs are logged server-side
- No automatic retry mechanism
- Manual resubmission required

No Job Status Query:
- Cannot query job status by job_id
- Future enhancement: `GET /api/v1/jobs/{job_id}` endpoint

In-Process Background Tasks:
- Jobs are not persisted
- Server restart interrupts running jobs
- Future enhancement: persistent queue (Celery, RQ)
