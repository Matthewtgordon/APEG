# n8n Workflow Configuration Guide - APEG Integration

## Overview

This guide configures an n8n HTTP Request workflow to submit SEO/tag update jobs to the APEG FastAPI endpoint (`POST /api/v1/jobs/seo-update`).

Key Behavior:
- APEG returns 202 Accepted immediately (does not wait for Shopify completion)
- n8n treats 202 as "job queued successfully"
- No completion callback in Phase 3 (future enhancement)

---

## 1. HTTP REQUEST NODE CONFIGURATION

### Node Settings

Method: `POST`

URL:
```
{{ $env.APEG_API_BASE_URL }}/api/v1/jobs/seo-update
```
- Set `APEG_API_BASE_URL` environment variable:
  - Development: `http://localhost:8000`
  - Production: `https://apeg.yourdomain.com`

Send Body: `ON`

Body Content Type: `JSON`

Response Format: `JSON`

Options:
- [X] Include Response Headers and Status

Timeout: `10000` (10 seconds - API responds immediately with 202)

---

### Headers

Manual Header Configuration:
- Name: `Content-Type`
- Value: `application/json`

Authentication: Use n8n Credential (see Section 2)

---

### JSON Body

Required Fields:
```json
{
  "run_id": "n8n-{{ $now.setZone('UTC').toISO() }}",
  "shop_domain": "{{ $env.SHOPIFY_STORE_DOMAIN }}",
  "dry_run": false,
  "products": [
    {
      "product_id": "gid://shopify/Product/1234567890",
      "tags_add": ["apeg_seo", "birthstone_march"],
      "tags_remove": ["old_tag"],
      "seo": {
        "title": "Beautiful Handcrafted March Birthstone Ring",
        "description": "Aquamarine gemstone ring with artisan metalwork"
      }
    }
  ]
}
```

Field Definitions:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Unique identifier for idempotency tracking. Use n8n execution ID pattern. |
| `shop_domain` | string | Must match APEG's `SHOPIFY_STORE_DOMAIN`. Use env var. |
| `dry_run` | boolean | `true` = validate only, no Shopify writes. `false` = execute. |
| `products` | array | Non-empty list of products to update. |
| `products[].product_id` | string | Shopify GID (e.g., `gid://shopify/Product/123`) |
| `products[].tags_add` | array | Tags to add (merged with existing). Optional. |
| `products[].tags_remove` | array | Tags to remove from existing. Optional. |
| `products[].seo` | object | SEO updates (title/description). Optional. |

---

## 2. CREDENTIAL MANAGEMENT

### Create n8n Credential (Header Auth)

DO NOT hardcode API keys in workflow JSON.

Steps:
1. Navigate to: Credentials -> New Credential
2. Select: HTTP Request -> Header Auth
3. Configure:
   - Name: `APEG API Key (DEMO)` or `APEG API Key (LIVE)`
   - Header Name: `X-APEG-API-KEY`
   - Header Value: [paste APEG_API_KEY value]
4. Save credential

In HTTP Request Node:
- Authentication: Select the credential created above

Security (Self-Hosted n8n):
- Set `N8N_ENCRYPTION_KEY` environment variable to encrypt stored credentials
- See: https://docs.n8n.io/hosting/configuration/environment-variables/security/

---

## 3. RECOMMENDED WORKFLOW LAYOUT

Minimum Working Workflow:
```
[Manual Trigger]
    ->
[Set Node: Build Payload]
    - Set run_id: n8n-{{ $now.setZone('UTC').toISO() }}
    - Set shop_domain: {{ $env.SHOPIFY_STORE_DOMAIN }}
    - Set dry_run: false
    - Set products: [...]
    ->
[HTTP Request: POST to APEG]
    - URL: {{ $env.APEG_API_BASE_URL }}/api/v1/jobs/seo-update
    - Auth: Header Auth credential
    - Body: {{ $json }}
    ->
[IF Node: Assert 202]
    - Condition: {{ $json.statusCode }} == 202
    ->
[Set Node: Extract Job Info]
    - job_id: {{ $json.body.job_id }}
    - run_id: {{ $json.body.run_id }}
    - received_count: {{ $json.body.received_count }}
    ->
[Optional: Log to Sheet/Database]
```

---

## 4. ENVIRONMENT VARIABLES (n8n)

Required:
```bash
APEG_API_BASE_URL=http://localhost:8000
SHOPIFY_STORE_DOMAIN=your-demo-store.myshopify.com
```

Optional (for credential via env - NOT RECOMMENDED):
```bash
# Prefer credential store over env vars for API keys
# APEG_API_KEY=your-secret-key
```

Set in n8n:
- Docker: Add to docker-compose.yml environment section
- Self-hosted: Add to .env file or systemd service
- Cloud: Use n8n cloud environment variable settings

---

## 5. END-TO-END VERIFICATION TESTS

### TEST 0: Network + Auth Reachability (Negative Test)

Purpose: Prove n8n can reach APEG and auth enforcement works

Steps:
1. Configure HTTP Request node with correct URL
2. Use invalid credential (wrong API key)
3. Set minimal valid body: dry_run: true, 1 product
4. Execute workflow

Expected Result:
- Workflow FAILS
- HTTP status: 401 Unauthorized
- Error message: "Invalid API key"

Evidence: Screenshot of n8n execution error showing 401

---

### TEST 1: Dry Run Happy Path (202 Without Shopify Writes)

Purpose: Prove 202 response and dry run execution

Steps:
1. Configure HTTP Request node with valid credential
2. Set body:
```json
{
  "run_id": "n8n-test-dry-run",
  "shop_domain": "{{ $env.SHOPIFY_STORE_DOMAIN }}",
  "dry_run": true,
  "products": [{
    "product_id": "gid://shopify/Product/1234567890",
    "tags_add": ["test-tag"]
  }]
}
```
3. Execute workflow

Expected Result:
- Workflow SUCCESS
- HTTP status: 202 Accepted
- Response body contains:
  - job_id (UUID format)
  - status: "queued"
  - run_id: "n8n-test-dry-run"
  - received_count: 1

APEG Server Logs:
- "Starting SEO update job: ... dry_run=True"
- "DRY RUN MODE: Would update 1 products"
- "Job [job_id] completed (dry run)"

Evidence:
- n8n execution success screenshot
- APEG server log excerpt

---

### TEST 2: Live Single Item (Prove Background Dispatch)

Purpose: Prove background execution and Shopify write

Steps:
1. Set body:
```json
{
  "run_id": "n8n-test-live-single",
  "shop_domain": "{{ $env.SHOPIFY_STORE_DOMAIN }}",
  "dry_run": false,
  "products": [{
    "product_id": "gid://shopify/Product/[KNOWN_PRODUCT_ID]",
    "tags_add": ["apeg_phase3_test_{{ $now.toMillis() }}"]
  }]
}
```
2. Execute workflow

Expected Result:
- Workflow returns 202 within 10 seconds (no timeout)
- Response body matches TEST 1 structure

APEG Server Logs:
- "Fetching current state for 1 products"
- "Submitting bulk mutation for 1 products"
- "Bulk operation submitted: [bulk_op_id]"
- "Job [job_id] completed successfully"

Shopify Admin Verification:
- Open product in Shopify admin
- Confirm test tag is present

Evidence:
- n8n execution time < 10s
- APEG logs showing bulk operation lifecycle
- Shopify admin screenshot with tag

---

### TEST 3: Live Small Batch (Prove Batch Acceptance)

Purpose: Prove multi-product batch handling

Steps:
1. Set body with 5 products
2. Execute workflow

Expected Result:
- Workflow returns 202
- received_count: 5
- APEG logs show batch processing

Evidence:
- n8n execution showing received_count=5
- APEG logs confirming 5 products processed

---

## 6. TROUBLESHOOTING

### Error: "Invalid API key" (401)

Cause: Credential mismatch between n8n and APEG server

Fix:
1. Verify `APEG_API_KEY` on APEG server: `echo $APEG_API_KEY`
2. Verify n8n credential value matches exactly
3. Check for whitespace/newlines in credential value

---

### Error: "shop_domain mismatch" (400)

Cause: `shop_domain` in request does not match APEG's `SHOPIFY_STORE_DOMAIN`

Fix:
1. Verify APEG server: `echo $SHOPIFY_STORE_DOMAIN`
2. Update n8n env var or body to match

---

### Error: Request timeout

Cause: APEG server unreachable or timeout too short

Fix:
1. Verify APEG server is running: `curl http://localhost:8000/docs`
2. Check network connectivity (firewall, DNS)
3. Increase timeout if needed (should not be necessary for 202 response)

---

### Success but no Shopify changes

Cause: `dry_run: true` OR background job failed

Fix:
1. Check body: ensure `dry_run: false`
2. Check APEG server logs for job execution errors
3. Verify `APEG_ALLOW_WRITES=YES` on APEG server

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
- Future enhancement: GET /api/v1/jobs/{job_id} endpoint
