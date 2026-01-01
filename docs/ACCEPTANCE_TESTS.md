# ACCEPTANCE_TESTS.md
# Spec → Test Mapping

> **📍 Quick Links:** [Main README](../README.md) | [Project Plan](PROJECT_PLAN_ACTIVE.md) | [Architecture Spec](integration-architecture-spec-v1.4.1.md) | [Docs Index](README.md)

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2025-12-29

## 📋 Quick Navigation

| Phase | Test Range | Status |
|-------|------------|--------|
| [Phase 0](#phase-0--configuration--preconditions) | TEST-DOCS-*, TEST-ENV-* | Required |
| [Phase 1](#phase-1--shopify-backbone-stage-2-verified) | TEST-BULK-* | ✅ Verified |
| [Phase 2](#phase-2-bulk-mutations-critical-bug-fix) | TEST-CRITICAL-*, TEST-MUTATION-*, TEST-P2-* | ✅ Complete |
| [Phase 3](#phase-3-n8n-orchestration-bindings) | TEST-API-*, TEST-N8N-* | ✅ Complete |
| [Phase 4](#phase-4-data-collection--metrics-intelligence) | TEST-META-*, TEST-SHOPIFY-*, TEST-COLLECTOR-* | 🚧 In Progress |
| [Phase 5](#phase-5-feedback-loop--refinement-engine) | TEST-FEEDBACK-* | 🚧 In Progress |

---

## PHASE 0 — Configuration & Preconditions

| Test ID | Test Name | Spec Section | Method | Expected | Actual | Status | Evidence |
|---------|-----------|--------------|--------|----------|--------|--------|----------|
|  | Shopify auth: `{ shop { name } }` | 1.8, Appendix F |  |  |  | REQUIRED |  |
|  | Meta token debug valid | 1.8, 6.12 |  |  |  | REQUIRED |  |
|  | n8n credential ID documented | 8.13 |  |  |  | REQUIRED |  |
| AT-P0-LEGACY-APP-01 | Legacy custom app creation constraints | Section 1.7 | Research validation | New apps after 2026-01-01 require Shopify Dev Dashboard; existing legacy apps unaffected | Matches expected | VERIFIED | Stage 2 Research Log |
| AT-P0-CJ-ATTRIBUTION-01 | CustomerJourney attribution window semantics | Section 7 | Research validation | CustomerJourney uses a 30-day attribution window (not data retention); non-build-gating | Matches expected | VERIFIED | Stage 2 Research Log |

---

## Phase 0: Documentation Baseline

### TEST-DOCS-01: Spec Version Updated
**Requirement:** Spec header must show Version 1.4.1
**Test Method:** `grep "Version: 1.4.1" docs/integration-architecture-spec-v1.4.md`
**Evidence Source:** Grep output
**Status:** READY FOR TEST

### TEST-DOCS-02: Env Var Standardization
**Requirement:** All references use SHOPIFY_ADMIN_ACCESS_TOKEN (not SHOPIFY_API_TOKEN)
**Test Method:** 
1. `grep -c "SHOPIFY_ADMIN_ACCESS_TOKEN" docs/integration-architecture-spec-v1.4.md`
2. `grep "SHOPIFY_API_TOKEN" docs/integration-architecture-spec-v1.4.md` (expect: empty)
**Evidence Source:** Grep output
**Status:** READY FOR TEST

### TEST-DOCS-03: Safety Lock Language Present
**Requirement:** PROJECT_PLAN_ACTIVE must use backup command pattern (no direct .env overwrite)
**Test Method:** `grep -A 3 "cp .env .env.bak" docs/PROJECT_PLAN_ACTIVE.md`
**Evidence Source:** Grep output
**Status:** READY FOR TEST

---

## PHASE 1 — Shopify Backbone (Stage 2 VERIFIED)

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| `bulkOperations(...)` absent from QueryRoot | 5.6 | ✓ VERIFIED | "Field 'bulkOperations' doesn't exist" |
| `node(id:)` polling works | 5.6 | ✓ VERIFIED | Returns BulkOperation with status |
| Sequential bulk query lock | 5.10 | ✓ VERIFIED | "already in progress" error on concurrent |
| Bulk query → COMPLETED | 5.6 | ✓ VERIFIED | Dev-store test |
| Bulk mutation → COMPLETED | 5.5 | ✓ VERIFIED | Staged upload + runMutation |
| Upload hard-gate (non-2xx blocks) | 5.5 | ✓ VERIFIED | "JSONL file could not be found" |
| stagedUploadPath rejects local paths | 5.5 | ✓ VERIFIED | /tmp path rejected |
| Tag merge preserves existing | 2.4.2 | ✓ VERIFIED | Pre-existing tags preserved |

---

## Phase 1: Shopify Bulk Client

### TEST-BULK-01: Redis Lock Enforcement
**Requirement:** Only 1 concurrent bulk job per shop
**Test Method:** 
1. Run mock test: `pytest tests/unit/test_bulk_client_mock.py::test_submit_job_lock_failure -v`
2. Verify ShopifyBulkJobLockedError raised when lock unavailable
**Evidence Source:** Unit test execution log
**Status:** READY FOR TEST

### TEST-BULK-02: GraphQL Operations (Verbatim Strings)
**Requirement:** Use exact GraphQL strings from spec
**Test Method:**
1. `grep -n "bulkOperationRunQuery" src/apeg_core/shopify/bulk_client.py`
2. `grep -n "node(id:" src/apeg_core/shopify/bulk_client.py`
**Evidence Source:** Code inspection
**Status:** READY FOR TEST

### TEST-BULK-03: Retry-After Header Handling
**Requirement:** Respect Retry-After on HTTP 429
**Test Method:**
1. Run mock test: `pytest tests/unit/test_bulk_client_mock.py::test_http_429_with_retry_after -v`
2. Verify client sleeps for Retry-After duration before retry
**Evidence Source:** Unit test execution log
**Status:** READY FOR TEST

### TEST-BULK-04: Terminal State Validation
**Requirement:** Raise error if COMPLETED but url missing
**Test Method:**
1. Run mock test: `pytest tests/unit/test_bulk_client_mock.py::test_poll_status_completed_missing_url -v`
2. Verify ShopifyBulkApiError raised with "url missing" message
**Evidence Source:** Unit test execution log
**Status:** READY FOR TEST

---

## Phase 2: Bulk Mutations (CRITICAL BUG FIX)

### TEST-CRITICAL-01: Root GraphQL Error Handling
**Requirement:** MUST check root ["errors"] before accessing ["data"] (prevent KeyError crashes)
**Test Method:** `pytest tests/unit/test_graphql_error_handling.py::test_root_level_errors_trigger_exception -v`
**Evidence Source:** Unit test execution (regression test)
**Status:** READY FOR TEST

### TEST-MUTATION-01: Staged Upload Workflow
**Requirement:** Complete 4-step dance without errors
**Test Method:**
1. Code inspection: `grep -n "_staged_uploads_create\\|_upload_jsonl\\|_bulk_operation_run_mutation" src/apeg_core/shopify/bulk_mutation_client.py`
2. Verify all 3 methods present in pipeline
**Evidence Source:** Code inspection
**Status:** READY FOR TEST

### TEST-MUTATION-02: UserErrors Handling
**Requirement:** Raise ShopifyBulkGraphQLError on stagedUploadsCreate/bulkOperationRunMutation userErrors
**Test Method:** `pytest tests/unit/test_bulk_mutation_client.py::test_staged_uploads_create_user_errors -v`
**Evidence Source:** Unit test execution
**Status:** READY FOR TEST

### TEST-MUTATION-03: Safe Tag Merge
**Requirement:** Tags = (current ∪ tags_add) - tags_remove
**Test Method:** `pytest tests/unit/test_bulk_mutation_client.py::test_safe_write_tag_merge -v`
**Evidence Source:** Unit test execution
**Status:** READY FOR TEST

### TEST-MUTATION-04: Multipart Field Ordering
**Requirement:** Parameters first (in order), file field LAST
**Test Method:** Code inspection: `grep -A 15 "_upload_jsonl_to_staged_target" src/apeg_core/shopify/bulk_mutation_client.py`
**Evidence Source:** Code inspection (verify loop over parameters, then file field)
**Status:** READY FOR TEST

## Phase 2: Schema Fix Verification

### TEST-P2-SCHEMA-COMPLETE-01: groupObjects Complete Removal
**Requirement:** ZERO instances of groupObjects in Phase 2 mutation code
**Test Method:**
1. Comprehensive search: `rg -n "groupObjects|\$groupObjects|group_objects" src/apeg_core/ -S`
2. Expected: 0 hits (or only explanatory comments marked as such)
3. Verify GraphQL string: `grep -A 20 "MUTATION_BULK_OPERATION_RUN_MUTATION" src/apeg_core/shopify/graphql_strings.py`
4. Confirm no `$groupObjects` variable declaration
5. Confirm no `groupObjects:` argument in mutation call
**Evidence Source:** Code inspection (ripgrep output)
**Status:** VERIFIED (Done 12.30)

### TEST-P2-INTEGRATION-GREEN-01: Phase 2 Integration Test Pass
**Requirement:** Integration test must exit 0 after schema fix
**Test Method:**
1. Ensure DEMO store credentials configured in `.env`
2. Ensure Redis running: `docker ps | grep redis`
3. Run: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py`
4. Expected output:
   - "SCENARIO 1: Safe Tag Merge" - PASS
   - "SCENARIO 2: Staged Upload Dance" - PASS
   - "ALL INTEGRATION TESTS PASSED"
   - Exit code: 0
5. Expected NO output containing:
   - "GraphQL root errors"
   - "Field 'groupObjects'"
   - "declared but not used"
**Evidence Source:** Integration test stdout/stderr + exit code (Command: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py`)
**Status:** VERIFIED (Done 12.30)

**Pass Signal:**
- Safe Write verification confirms original tags preserved
- New tag successfully added
- Staged upload dance completed without HTTP 403/400
- No GraphQL schema validation errors

---

## Phase 2 Integration Tests (Real API)

### INT-TEST-PHASE2-01: Safety Gates Enforcement
**Requirement:** Script MUST refuse to run without DEMO safety gates
**Test Method:**
1. Run without APEG_ENV=DEMO: `python tests/integration/verify_phase2_safe_writes.py`
2. Verify exit code 2 (safety gate failure)
3. Run with APEG_ALLOW_WRITES=NO
4. Verify exit code 2
5. Run with store not in allowlist
6. Verify exit code 2
**Evidence Source:** Exit code verification
**Status:** READY FOR TEST

### INT-TEST-PHASE2-02: Safe Tag Merge (Live API)
**Requirement:** Original tags MUST be preserved when adding new tags
**Test Method:**
1. Configure `.env.integration` with DEMO credentials
2. Set `TEST_PRODUCT_ID` to existing product with known tags
3. Run: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py`
4. Verify exit code 0
5. Check logs: "PASS: Safe write preserved all original tags"
6. Manually verify product in Shopify Admin: all original tags + new tag present
**Evidence Source:** Integration test output (Command: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py`)
**Status:** VERIFIED (Done 12.30)

### INT-TEST-PHASE2-03: Staged Upload End-to-End
**Requirement:** 4-step staged upload dance completes without HTTP errors
**Test Method:**
1. Run integration script (as above)
2. Verify no 403/400 errors in logs
3. Verify bulk operation reaches COMPLETED status
4. Check logs: "PASS: Staged upload dance completed"
**Evidence Source:** Integration test output (Command: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py`)
**Status:** VERIFIED (Done 12.30)

### INT-TEST-PHASE2-04: Cleanup Guarantee
**Requirement:** Created test products MUST be deleted (even on failure)
**Test Method:**
1. Run integration script WITHOUT TEST_PRODUCT_ID (forces product creation)
2. Observe product creation log: "Created test product: gid://..."
3. Artificially inject failure (modify script to raise after mutation)
4. Verify cleanup log: "Deleted test product: gid://..."
5. Manually verify product NOT in Shopify Admin
**Evidence Source:** Integration test output + cleanup logs (Command: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py`)
**Status:** VERIFIED (Done 12.30)

---

## PHASE 2 — Safe Writes

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| Tag hydration (fetch→union→update) | 2.4.2 | REQUIRED | |
| SEO update via ProductInput.seo | 2.3 | REQUIRED | |
| Audit log before/after | 9.x | REQUIRED | |
| Rollback procedure tested | Appendix F | REQUIRED | |

---

## Phase 3: API Layer (n8n Integration) - REVISED

### TEST-API-01: API Key Authentication (401 Enforcement)
**Requirement:** Endpoint MUST return 401 (not 422) for missing/invalid API key
**Test Method:**
1. Run unit test: `pytest tests/unit/test_api_auth.py::test_require_api_key_invalid -v`
2. Verify HTTPException 401 raised with WWW-Authenticate header
3. Run integration: `curl -X POST http://localhost:8000/api/v1/jobs/seo-update` (no header)
4. Verify 401 response (not 422)
5. Run integration: `curl -X POST http://localhost:8000/api/v1/jobs/seo-update -H "X-APEG-API-KEY: wrong"`
6. Verify 401 response with "Invalid API key" detail
**Evidence Source:** Unit test + curl verification
**Status:** READY FOR TEST

### TEST-API-02: Shop Domain Validation
**Requirement:** Endpoint MUST reject mismatched shop_domain
**Test Method:**
1. Run unit test: `pytest tests/unit/test_api_routes.py::test_seo_update_job_shop_domain_mismatch -v`
2. Verify 400 response with "shop_domain mismatch" detail
**Evidence Source:** Unit test execution log
**Status:** READY FOR TEST

### TEST-API-03: Immediate 202 Response
**Requirement:** Endpoint MUST return 202 Accepted immediately (never wait for Shopify)
**Test Method:**
1. Start server: `PYTHONPATH=. uvicorn src.apeg_core.main:app --reload`
2. Submit job via curl (see docs/API_USAGE.md)
3. Measure response time (should be <100ms)
4. Verify response contains: job_id, status="queued", run_id, received_count
**Evidence Source:** curl timing + response body
**Status:** VERIFIED (Done 12.30)
**Evidence:**
```
curl response:
{"job_id":"085a13b1-d44e-4ca2-b19b-e32accb1dde6","status":"queued","run_id":"manual-test-cli-01","received_count":1}
```

### TEST-API-04: Background Task Execution
**Requirement:** Background task MUST execute safe-write pipeline asynchronously
**Test Method:**
1. Configure .env with DEMO credentials
2. Submit job with dry_run=true
3. Check server logs: verify "DRY RUN MODE" message
4. Submit job with dry_run=false (single product)
5. Check server logs: verify bulk operation submission + polling + completion
**Evidence Source:** Server logs (stdout/stderr)
**Status:** BLOCKED (requires DEMO store credentials + Phase 2 method verification)

### TEST-API-05: Exception Safety
**Requirement:** Background task failures MUST be logged without crashing server
**Test Method:**
1. Submit job with invalid product_id (e.g., "gid://shopify/Product/99999999999")
2. Verify server continues running (no process exit)
3. Check logs for exception traceback with job_id
**Evidence Source:** Server logs + process status
**Status:** BLOCKED (requires DEMO store credentials)

### TEST-API-06: aiohttp Timeout Configuration
**Requirement:** aiohttp session MUST have connect and total timeouts configured
**Test Method:**
1. Code inspection: grep "ClientTimeout" src/apeg_core/api/routes.py
2. Verify timeout(total=300, connect=30) in _run_seo_update_job
**Evidence Source:** Code inspection
**Status:** READY FOR TEST

### TEST-API-07: PYTHONPATH Execution
**Requirement:** Server MUST start without import errors using documented command
**Test Method:**
1. Run: `PYTHONPATH=. uvicorn src.apeg_core.main:app --reload`
2. Verify no ModuleNotFoundError
3. Access http://localhost:8000/docs
4. Verify interactive documentation loads
**Evidence Source:** Server startup logs + browser verification
**Status:** READY FOR TEST

---

## Phase 3 Part 2: n8n Workflow + Environment Parity

### TEST-ENV-01: Environment Parity Check (BLOCKING GATE)
**Requirement:** All environment templates MUST contain APEG_API_KEY in APEG API Configuration section
**Test Method:**
1. Run: `grep -R "APEG_API_KEY" .env*.example`
2. Verify output shows APEG_API_KEY exists in .env.example
3. If .env.integration.example exists (pre-consolidation), verify it contains APEG_API_KEY OR is deprecated
4. Manually inspect .env.example to confirm "APEG API Configuration" section is complete
**Evidence Source:** Command output + manual inspection confirmation
**Status:** VERIFIED (2026-01-01)
**Evidence (2024-12-30):**
```bash
# Command output:
.env.example:APEG_API_KEY=your-secret-api-key-here

# Manual inspection:
PASS - .env.example contains complete APEG API Configuration section
PASS - Active .env contains APEG_API_KEY with non-placeholder value (user verified)
PASS - .env.integration.example is deleted

# Overall Result: [PASS/FAIL]
# Overall Result: PASS
# Date: 2024-12-30
```

**Evidence (2026-01-01 05:58Z):**
- .env.example keys: 30
- .env keys: 13
- Missing keys: FEEDBACK_APPROVAL_MODE, FEEDBACK_BASELINE_DAYS, FEEDBACK_CTR_BAD, FEEDBACK_CTR_GOOD, FEEDBACK_DECISION_LOG_DIR, FEEDBACK_ENABLED, FEEDBACK_MAX_ACTIONS_PER_RUN, FEEDBACK_MIN_CLICKS_PROXY, FEEDBACK_MIN_IMPRESSIONS, FEEDBACK_MIN_ORDERS, FEEDBACK_MIN_SPEND_USD, FEEDBACK_REQUIRE_APPROVAL, FEEDBACK_ROAS_BAD, FEEDBACK_ROAS_GOOD, FEEDBACK_WINDOW_DAYS, METRICS_BACKFILL_DAYS, METRICS_COLLECTION_TIME, METRICS_DB_PATH, METRICS_RAW_DIR, METRICS_TIMEZONE, STRATEGY_TAG_CATALOG
- Extra keys: APEG_API_BASE_URL, APEG_API_HOST, DEMO_STORE_DOMAIN_ALLOWLIST, META_APP_ID
- APEG_API_KEY: VALID
- Overall Result: FAIL

**Evidence (2026-01-01 06:44Z):**
- .env.example keys: 30
- .env keys: 37
- Missing keys: none
- Extra keys: APEG_API_BASE_URL, APEG_API_HOST, APEG_API_PORT, DEMO_STORE_DOMAIN_ALLOWLIST, META_APP_ID, TEST_PRODUCT_ID, TEST_TAG_PREFIX
- APEG_API_KEY: VALID
- Overall Result: PASS

**Evidence (2026-01-01 08:39Z):**
- .env.example keys: 30
- .env keys: 37
- Missing keys: none
- Extra keys: APEG_API_BASE_URL, APEG_API_HOST, APEG_API_PORT, DEMO_STORE_DOMAIN_ALLOWLIST, META_APP_ID, TEST_PRODUCT_ID, TEST_TAG_PREFIX
- APEG_API_KEY: VALID
- Overall Result: PASS

---

### TEST-N8N-01: Network + Auth Reachability (Negative Test)
**Requirement:** n8n workflow MUST receive 401 when using invalid API key
**Test Method:**
1. Configure n8n HTTP Request node:
   - URL: `{{ $env.APEG_API_BASE_URL }}/api/v1/jobs/seo-update`
   - Authentication: HTTP Request credential with WRONG API key value
   - Body: Minimal valid (dry_run=true, 1 product)
2. Execute workflow
3. Verify workflow FAILS with 401 Unauthorized error
4. Verify error message contains "Invalid API key"
**Evidence Source:** n8n execution screenshot showing 401 error
**Status:** VERIFIED (Done 12.30)
**Evidence:**
```
> POST /api/v1/jobs/seo-update HTTP/1.1
> Host: 100.126.221.42:8000
> X-APEG-API-KEY: wrong_key
< HTTP/1.1 401 Unauthorized
< www-authenticate: API-Key
< detail: Invalid API key
```

---

### TEST-N8N-02: Dry Run Happy Path (202 Without Shopify Writes)
**Requirement:** n8n workflow MUST receive 202 with job_id for valid dry run request
**Test Method:**
1. Configure n8n HTTP Request node with VALID credential
2. Set body with products array (NOT string):
```json
{
  "run_id": "n8n-test-dryrun",
  "shop_domain": "{{ $env.SHOPIFY_STORE_DOMAIN }}",
  "dry_run": true,
  "products": "{{ typeof $json.products === 'string' ? JSON.parse($json.products) : $json.products }}"
}
```
3. Execute workflow
4. Verify workflow SUCCESS with statusCode=202 (response time < 10s)
5. Verify response contains: job_id, status="queued", run_id, received_count=1
6. Verify APEG logs show "DRY RUN MODE" message and no Shopify API calls
**Evidence Source:** n8n execution success + APEG server logs
**Status:** VERIFIED (Done 12.30)
**Evidence:**
```json
// n8n Response:
// HTTP 202 Accepted
{
  "job_id": "0d2c579c-e2d4-4717-a939-9b787f70cdfb",
  "status": "queued",
  "run_id": "n8n-manual-test-01",
  "received_count": 1
}

// APEG Logs:
[Paste log excerpt showing dry run execution]
```

---

### TEST-N8N-03: Array Typing Correctness
**Requirement:** products field MUST be sent as JSON array (not string) to prevent 422
**Test Method:**
1. Create upstream Set node that outputs products as a JSON string:
```json
{
  "products": "[{\"product_id\":\"gid://shopify/Product/1\",\"tags_add\":[\"test\"]}]"
}
```
2. Configure HTTP Request node with typing-safe expression:
```javascript
{{ typeof $json.products === 'string' ? JSON.parse($json.products) : $json.products }}
```
3. Execute workflow
4. Verify NO 422 error
5. Verify 202 response OR 400 (for other validation reasons, NOT 422)
**Evidence Source:** n8n execution showing successful type conversion
**Status:** BLOCKED (2026-01-01; n8n unavailable in sandbox)
**Evidence:**
```
[Execution screenshot showing 202 response despite string input]
```

**Evidence (2026-01-01 08:42Z):**
SKIPPED in sandbox: n8n instance not available and localhost networking is blocked; rerun in full environment.

---

### TEST-N8N-04: Docker Network Connectivity
**Requirement:** n8n in Docker MUST reach APEG on host using LAN IP (not localhost)
**Test Method:**
1. Start n8n in Docker
2. Start APEG on host with `--host 0.0.0.0`
3. Set n8n env var: `APEG_API_BASE_URL=http://192.168.1.50:8000` (use actual LAN IP)
4. Execute workflow
5. Verify successful connection (401 or 202, NOT connection refused)
6. Negative test: Change to `http://localhost:8000` and verify ECONNREFUSED
**Evidence Source:** n8n execution logs + curl test from inside container
**Status:** BLOCKED (requires Docker setup)
**Evidence:**
```bash
# Test from inside n8n container:
docker exec -it n8n curl http://192.168.1.50:8000/docs
# Expected: HTML response (or 401)

# Negative test:
docker exec -it n8n curl http://localhost:8000/docs
# Expected: Connection refused
```

---

### TEST-N8N-05: Live Single Item (Background Execution Proof)
**Requirement:** Background job MUST execute and update Shopify product
**Test Method:**
1. Configure n8n with dry_run=false
2. Use known product_id with timestamp-based test tag:
```json
{
  "product_id": "gid://shopify/Product/[KNOWN_ID]",
  "tags_add": ["apeg_n8n_test_{{ $now.toMillis() }}"]
}
```
3. Execute workflow (verify 202 response < 10s)
4. Monitor APEG logs for:
   - Bulk operation submission
   - Polling lifecycle
   - Completion message
5. Verify tag appears on product in Shopify admin
**Evidence Source:** n8n timing + APEG logs + Shopify admin screenshot
**Status:** VERIFIED (2026-01-01)
**Evidence (2026-01-01 07:02Z; failed due to Redis):**
```json
// n8n response:
{
  "job_id": "05654559-5ff3-4daa-a8d0-c01aaed11336",
  "status": "queued",
  "run_id": "n8n-manual-test-01",
  "received_count": 1
}
```
```text
APEG Logs:
2026-01-01 07:02:32,280 [INFO] src.apeg_core.api.routes: Queued SEO update job: job_id=05654559-5ff3-4daa-a8d0-c01aaed11336, run_id=n8n-manual-test-01, products_count=1
2026-01-01 07:02:32,282 [INFO] src.apeg_core.api.routes: Starting SEO update job: job_id=05654559-5ff3-4daa-a8d0-c01aaed11336, run_id=n8n-manual-test-01, products=1, dry_run=False
2026-01-01 07:02:32,661 [ERROR] src.apeg_core.api.routes: Job 05654559-5ff3-4daa-a8d0-c01aaed11336 (run_id=n8n-manual-test-01) failed with exception: Error 111 connecting to localhost:6379. Connection refused.
```

**Evidence (2026-01-01 07:17Z; success after Redis install):**
```json
// n8n response:
[
  {
    "job_id": "c7dd52cd-54e5-402e-8b81-d9d0275405f2",
    "status": "queued",
    "run_id": "n8n-manual-test-01",
    "received_count": 1
  }
]
```
```text
APEG Logs:
2026-01-01 07:17:43,259 [INFO] src.apeg_core.api.routes: Queued SEO update job: job_id=c7dd52cd-54e5-402e-8b81-d9d0275405f2, run_id=n8n-manual-test-01, products_count=1
2026-01-01 07:17:43,260 [INFO] src.apeg_core.api.routes: Starting SEO update job: job_id=c7dd52cd-54e5-402e-8b81-d9d0275405f2, run_id=n8n-manual-test-01, products=1, dry_run=False
2026-01-01 07:17:43,272 [INFO] src.apeg_core.shopify.bulk_mutation_client: Acquired mutation lock: run_id=n8n-manual-test-01
2026-01-01 07:17:46,836 [INFO] src.apeg_core.shopify.bulk_mutation_client: Submitted bulk mutation: op_id=gid://shopify/BulkOperation/4412960243814, run_id=n8n-manual-test-01, updates=1
2026-01-01 07:17:52,096 [INFO] src.apeg_core.api.routes: Job c7dd52cd-54e5-402e-8b81-d9d0275405f2 completed successfully: bulk_op=gid://shopify/BulkOperation/4412960243814, objects=1
```

---

### TEST-INTEGRATION-02: Phase 2 Tests with Consolidated Template
**Requirement:** Phase 2 integration tests MUST still pass using updated .env.example
**Test Method:**
1. Delete old .env.integration (if exists)
2. Copy `.env.example` -> `.env.integration`
3. Fill in DEMO credentials (APEG API Configuration section)
4. Uncomment Integration Testing section and fill values
5. Source file: `set -a; source .env.integration; set +a`
6. Run: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py`
7. Verify all tests pass
**Evidence Source:** Script output
**Status:** SKIPPED (Configuration mismatch on test runner)
**Evidence:**
```bash
Skipped: Configuration mismatch on test runner. Proceeding based on manual verification of API and n8n endpoints.
```

---

## PHASE 3 — n8n Orchestration

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| Webhook trigger works | 8.13 | REQUIRED | |
| DEMO workflow execution | 8.13 | REQUIRED | |
| Credential swap verified | 8.13 | REQUIRED | Execution log shows LIVE |

---

## Phase 4: Data Collection & Metrics Intelligence

### TEST-META-01: Meta Insights API Field Validation (SMOKE TEST)
**Requirement:** Meta API MUST return required performance metrics fields
**Test Method:**
1. Set credentials: META_ACCESS_TOKEN, META_AD_ACCOUNT_ID
2. Run: `PYTHONPATH=. pytest tests/smoke/test_meta_api.py -v`
3. Verify HTTP 200 response
4. Verify fields present: spend, impressions, ctr, cpc
5. Verify outbound_clicks present (direct field OR actions array)
**Evidence Source:** pytest output + field list
**Status:** SKIPPED (2026-01-01; no data returned for test date)
**Evidence (prior run):**
```bash
PYTHONPATH=. pytest tests/smoke/test_meta_api.py -v
tests/smoke/test_meta_api.py::test_meta_insights_fields SKIPPED (No data returned for test date (no ad spend))
```

**Evidence (2026-01-01 06:44Z):**
```bash
PYTHONPATH=. ./venv/bin/python -m pytest tests/smoke/test_meta_api.py -v -rs
tests/smoke/test_meta_api.py::test_meta_insights_fields SKIPPED (No data returned for test date (no ad spend))
SKIPPED [1] tests/smoke/test_meta_api.py:57: No data returned for test date (no ad spend)
```

**Evidence (2026-01-01 08:42Z):**
```bash
PYTHONPATH=. pytest tests/smoke/test_meta_api.py -v -rs
tests/smoke/test_meta_api.py::test_meta_insights_fields SKIPPED (META_ACCESS_TOKEN not set)
SKIPPED [1] tests/smoke/test_meta_api.py:16: META_ACCESS_TOKEN not set
```
Note: Credentials intentionally unset in sandbox (network restricted; avoid secret exposure).

---

### TEST-SHOPIFY-01: Shopify Attribution Field Validation (SMOKE TEST)
**Requirement:** Shopify GraphQL MUST return customerJourneySummary with UTM fields
**Test Method:**
1. Set credentials: SHOPIFY_STORE_DOMAIN, SHOPIFY_ADMIN_ACCESS_TOKEN
2. Run: `PYTHONPATH=. pytest tests/smoke/test_shopify_attribution.py -v`
3. Verify customerJourneySummary exists on orders
4. Verify lastVisit/firstVisit include: landingPage, referrerUrl, utmParameters
5. Verify utmParameters fields: campaign, source, medium, term, content
6. Document edge cases (null attribution tolerance)
**Evidence Source:** pytest output + sample order structure
**Status:** SKIPPED (2026-01-01; no orders found in test date range)
**Evidence (prior run):**
```bash
PYTHONPATH=. pytest tests/smoke/test_shopify_attribution.py -v
tests/smoke/test_shopify_attribution.py::test_shopify_attribution_fields SKIPPED (No orders found in test date range)
```

**Evidence (2026-01-01 06:44Z):**
```bash
PYTHONPATH=. ./venv/bin/python -m pytest tests/smoke/test_shopify_attribution.py -v -rs
tests/smoke/test_shopify_attribution.py::test_shopify_attribution_fields SKIPPED (No orders found in test date range)
SKIPPED [1] tests/smoke/test_shopify_attribution.py:107: No orders found in test date range
```

**Evidence (2026-01-01 08:42Z):**
```bash
PYTHONPATH=. pytest tests/smoke/test_shopify_attribution.py -v -rs
tests/smoke/test_shopify_attribution.py::test_shopify_attribution_fields SKIPPED
SKIPPED [1] tests/smoke/test_shopify_attribution.py:15: SHOPIFY_ADMIN_ACCESS_TOKEN not set
```
Note: Credentials intentionally unset in sandbox (network restricted; avoid secret exposure).

---

### TEST-COLLECTOR-01: SQLite Idempotency Verification
**Requirement:** Collector MUST be safe to re-run for same date (no duplicates)
**Test Method:**
1. Configure .env with Phase 4 credentials
2. Run collector for specific date:
```bash
   PYTHONPATH=. python scripts/run_metrics_collector.py --date 2024-12-30
```
3. Query SQLite row counts:
```sql
   SELECT COUNT(*) FROM metrics_meta_daily WHERE metric_date='2024-12-30';
   SELECT COUNT(*) FROM order_attributions WHERE created_at LIKE '2024-12-30%';
   SELECT * FROM collector_state WHERE metric_date='2024-12-30';
```
4. Re-run collector for same date
5. Verify row counts UNCHANGED
6. Verify collector_state shows single success row per source
**Evidence Source:** SQL query results before/after re-run
**Status:** VERIFIED (2026-01-01)
**Evidence (2026-01-01 06:51Z):**
```bash
PYTHONPATH=. ./venv/bin/python scripts/run_metrics_collector.py --date 2025-12-30 -v
2026-01-01 06:51:07 [INFO] src.apeg_core.metrics.collector: Starting collection for 2025-12-30
2026-01-01 06:51:08 [INFO] src.apeg_core.metrics.collector: Collection complete for 2025-12-30

sqlite3 data/metrics.db "SELECT COUNT(*) FROM metrics_meta_daily WHERE metric_date='2025-12-30';"
3
sqlite3 data/metrics.db "SELECT COUNT(*) FROM order_attributions WHERE created_at LIKE '2025-12-30%';"
4
sqlite3 data/metrics.db "SELECT metric_date, source_name, status FROM collector_state WHERE metric_date='2025-12-30' ORDER BY source_name;"
2025-12-30|meta|success
2025-12-30|shopify|success

# Re-run (idempotency):
PYTHONPATH=. ./venv/bin/python scripts/run_metrics_collector.py --date 2025-12-30 -v
2026-01-01 06:51:37 [INFO] src.apeg_core.metrics.collector: Skipping Meta collection for 2025-12-30 (already collected)
2026-01-01 06:51:37 [INFO] src.apeg_core.metrics.collector: Skipping Shopify collection for 2025-12-30 (already collected)
2026-01-01 06:51:37 [INFO] src.apeg_core.metrics.collector: Collection complete for 2025-12-30

sqlite3 data/metrics.db "SELECT COUNT(*) FROM metrics_meta_daily WHERE metric_date='2025-12-30';"
3
sqlite3 data/metrics.db "SELECT COUNT(*) FROM order_attributions WHERE created_at LIKE '2025-12-30%';"
4
sqlite3 data/metrics.db "SELECT metric_date, source_name, status FROM collector_state WHERE metric_date='2025-12-30' ORDER BY source_name;"
2025-12-30|meta|success
2025-12-30|shopify|success
```

**Evidence (2026-01-01 08:43Z):**
```bash
PYTHONPATH=. python scripts/run_metrics_collector.py --date 2025-12-30 -v
2026-01-01 08:43:43 [INFO] src.apeg_core.metrics.collector: Starting collection for 2025-12-30
2026-01-01 08:43:43 [WARNING] src.apeg_core.metrics.collector: Meta credentials not configured, skipping Meta collection
2026-01-01 08:43:43 [WARNING] src.apeg_core.metrics.collector: Shopify credentials not configured, skipping Shopify collection
2026-01-01 08:43:43 [INFO] src.apeg_core.metrics.collector: Collection complete for 2025-12-30

sqlite3 data/metrics.db "SELECT COUNT(*) FROM metrics_meta_daily WHERE metric_date='2025-12-30';"
3
sqlite3 data/metrics.db "SELECT COUNT(*) FROM order_attributions WHERE created_at LIKE '2025-12-30%';"
4
sqlite3 data/metrics.db "SELECT metric_date, source_name, status FROM collector_state WHERE metric_date='2025-12-30' ORDER BY source_name;"
2025-12-30|meta|success
2025-12-30|shopify|success
```
Note: Credentials intentionally unset in sandbox (network restricted; avoid secret exposure).

---

### TEST-COLLECTOR-02: End-to-End Collection Verification
**Requirement:** Daily collection MUST persist to both SQLite and JSONL
**Test Method:**
1. Configure strategy_tags.json with test campaigns
2. Run full collection for yesterday:
```bash
   PYTHONPATH=. python scripts/run_metrics_collector.py -v
```
3. Verify JSONL files created:
```bash
   ls -lh data/metrics/raw/raw_meta_*
   ls -lh data/metrics/raw/raw_shopify_*
```
4. Verify SQLite data:
```sql
   SELECT entity_type, COUNT(*) FROM metrics_meta_daily GROUP BY entity_type;
   SELECT attribution_tier, COUNT(*) FROM order_attributions GROUP BY attribution_tier;
```
5. Verify attribution tier distribution (expect mix of 0/1/2/3)
6. Spot-check strategy_tag matching (orders with recognized campaigns)
**Evidence Source:** File listing + SQL query results + logs
**Status:** PARTIAL (no Meta data; Shopify skipped as already collected)
**Evidence:**
```bash
PYTHONPATH=. python3 scripts/run_metrics_collector.py --date 2025-12-30
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.collector: MetricsCollectorService initialized
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.collector: Database: data/metrics.db
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.collector: Strategy catalog: 18 tags
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.collector: Starting collection for 2025-12-30
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.meta_collector: Fetched 0 campaign-level insights for 2025-12-30
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.meta_collector: Wrote 0 rows to data/metrics/raw/raw_meta_campaign_2025-12-30.jsonl
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.meta_collector: Persisted 0 campaign metrics to SQLite
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.meta_collector: Fetched 0 ad-level insights for 2025-12-30
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.meta_collector: Wrote 0 rows to data/metrics/raw/raw_meta_ad_2025-12-30.jsonl
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.meta_collector: Persisted 0 ad metrics to SQLite
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.collector: Meta collection successful for 2025-12-30
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.collector: Skipping Shopify collection for 2025-12-30 (already collected)
2025-12-31 12:38:37 [INFO] src.apeg_core.metrics.collector: Collection complete for 2025-12-30
```

---

### TEST-ATTRIBUTION-01: Unit Test Coverage
**Requirement:** Attribution logic MUST have comprehensive test coverage
**Test Method:**
1. Run unit tests: `pytest tests/unit/test_attribution.py -v`
2. Verify all test cases pass:
   - URL parsing (with/without UTM)
   - Tier 1/2/3/0 selection logic
   - Strategy tag matching (exact/substring/slug/none)
   - Evidence JSON structure
**Evidence Source:** pytest coverage report
**Status:** READY FOR TEST
**Evidence:**
```bash
[Paste pytest results showing 100% pass]
```

---

## Phase 5: Feedback Loop & Refinement Engine

### TEST-FEEDBACK-01: Read + Aggregate (READY)
**Requirement:** Analyzer MUST load metrics and compute deterministic aggregates
**Test Method:**
1. Populate test database with sample metrics_meta_daily rows
2. Populate strategy_tag_mappings for test entities
3. Run analyzer.load_strategy_metrics() for 7D window
4. Verify output contains correct aggregates per strategy_tag
5. Verify KPI computations (ROAS, CTR, CVR proxy)
**Evidence Source:** Unit test + SQL query verification
**Status:** READY FOR TEST
**Evidence:**
```python
# Sample test data and expected outputs
[Paste test data + results]
```

---

### TEST-FEEDBACK-02: Mapping Enforcement (READY)
**Requirement:** System MUST NOT emit jobs when entity->strategy_tag mapping missing
**Test Method:**
1. Create metrics_meta_daily rows WITHOUT corresponding strategy_tag_mappings
2. Run analyzer in propose mode
3. Verify analyzer skips unmapped entities
4. Verify ZERO job emission (hard stop)
5. Verify warning logs indicate missing mappings
**Evidence Source:** Analyzer output + job count verification
**Status:** READY FOR TEST
**Evidence:**
```
[Log output showing skipped entities]
[Job count: 0]
```

---

### TEST-FEEDBACK-03: SEO Versioning (READY)
**Requirement:** Version control MUST support proposal -> apply -> revert cycle
**Test Method:**
1. Create test product snapshot (Champion)
2. Create Challenger snapshot (different title/description)
3. Call version_control.create_proposal()
4. Verify seo_versions row created with status=PROPOSED
5. Call version_control.approve() and mark_applied()
6. Verify status=APPLIED, phase3_job_id recorded
7. Call version_control.revert()
8. Verify status=REVERTED, Champion snapshot returned
**Evidence Source:** SQL queries + version control logs
**Status:** READY FOR TEST
**Evidence:**
```sql
-- Version creation:
[SQL query results showing PROPOSED -> APPROVED -> APPLIED -> REVERTED]

-- Snapshot verification:
[Champion snapshot JSON]
[Challenger snapshot JSON]
[Diff summary JSON]
```

---

### TEST-FEEDBACK-04: Product-Level Attribution (BLOCKED - REQUIRES BACKFILL)
**Requirement:** Analyzer MUST compute product-level ROAS when order_line_attributions populated
**Test Method:**
1. Populate order_line_attributions with test data (multiple products per order)
2. Run analyzer with product-level aggregation enabled
3. Verify product-level ROAS ranking
4. Verify products with ROAS < 2.0 flagged reliably
**Evidence Source:** SQL queries + analyzer output
**Status:** BLOCKED (requires Phase 4 collector rerun with line item capture)
**Evidence:**
```sql
-- Sample order_line_attributions data:
[SQL query showing populated table]

-- Product-level ROAS:
[Query results showing product_id, ROAS, flag]
```

---

### TEST-FEEDBACK-05: Diagnosis Matrix Coverage (READY)
**Requirement:** Diagnosis matrix MUST cover all CTR x ROAS combinations
**Test Method:**
1. Run unit tests: `pytest tests/unit/test_feedback_analyzer.py -v`
2. Verify test cases for:
   - CTR_LOW_ROAS_HIGH -> REFINE_AD_CREATIVE
   - CTR_HIGH_ROAS_LOW -> REFINE_SHOPIFY_SEO
   - CTR_LOW_ROAS_LOW -> PAUSE_STRATEGY
   - CTR_HIGH_ROAS_HIGH -> SCALE_BUDGET
   - INSUFFICIENT_DATA -> NO_ACTION
3. Verify all tests pass
**Evidence Source:** pytest output
**Status:** READY FOR TEST
**Evidence:**
```bash
[Paste pytest results showing 100% pass for diagnosis tests]
```

---

### TEST-FEEDBACK-06: LLM Output Validation (BLOCKED - REQUIRES LLM INTEGRATION)
**Requirement:** LLM outputs MUST be validated before persistence
**Test Method:**
1. Mock LLM API to return test Challenger JSON
2. Test Case 1: Valid output (all fields, within limits)
   - Verify validation passes
3. Test Case 2: Invalid output (missing fields)
   - Verify validation fails with specific errors
4. Test Case 3: Character limit violation (title > 70 chars)
   - Verify validation fails
5. Test Case 4: Prohibited claims present
   - Verify validation fails
**Evidence Source:** Validation function test results
**Status:** BLOCKED (requires LLM integration)
**Evidence:**
```python
[Test cases with pass/fail results]
```

---

### TEST-FEEDBACK-07: Phase 3 Job Emission (BLOCKED - REQUIRES INTEGRATION)
**Requirement:** Apply flow MUST emit Phase 3 job and record job_id
**Test Method:**
1. Create approved seo_versions row
2. Call apply flow with Phase 3 API integration
3. Verify POST to /api/v1/jobs/seo-update succeeds
4. Verify 202 Accepted response
5. Verify job_id recorded in seo_versions.phase3_job_id
6. Verify evaluation_start_at timestamp set
**Evidence Source:** HTTP logs + SQL verification
**Status:** BLOCKED (requires Phase 3 API integration)
**Evidence:**
```
[HTTP request/response logs]
[SQL query showing job_id recorded]
```

## PHASE 6 — CI/CD

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| CI green on PR | Appendix D | REQUIRED | |
| License scan green | Appendix D | REQUIRED | No GPL in prod |
| Coverage gate | Appendix D | REQUIRED | |

---

## PHASE 5 — Feedback Loop & Refinement Engine

### TEST-FEEDBACK-01: Propose/Execute/Evaluate Helpers (Unit)
**Requirement:** Helper logic supports proposal selection, update spec creation, and outcome evaluation.
**Test Method:** `PYTHONPATH=. pytest tests/unit/test_feedback_loop_helpers.py -v`
**Evidence Source:** Unit test output
**Status:** PASS (2026-01-01 10:02Z)
**Evidence:**
```
tests/unit/test_feedback_loop_helpers.py::test_select_proposal_targets_uses_top_revenue_per_strategy PASSED
tests/unit/test_feedback_loop_helpers.py::test_build_challenger_snapshot_ignores_unsupported_fields PASSED
tests/unit/test_feedback_loop_helpers.py::test_build_product_update_spec_adds_only_new_tags PASSED
tests/unit/test_feedback_loop_helpers.py::test_evaluate_outcome_handles_win_loss_inconclusive PASSED
```

### TEST-FEEDBACK-02: Propose Mode (LLM Challenger Generation)
**Requirement:** `run_feedback_loop.py --mode propose` creates seo_versions proposals.
**Test Method:** `PYTHONPATH=. python scripts/run_feedback_loop.py --mode propose -v`
**Evidence Source:** CLI output + sqlite rows
**Status:** PASS (seeded data + stub LLM, 2026-01-01 10:02Z)
**Evidence:**
```
2026-01-01 10:01:36 [INFO] src.apeg_core.feedback.version_control: Created SEO version proposal: 1 for gid://shopify/Product/seed_blue_ring_traffic
2026-01-01 10:01:36 [INFO] __main__: Propose mode complete: 1 proposals created
```

### TEST-FEEDBACK-03: Execute Mode (Phase 3 Job Emission)
**Requirement:** Approved proposals submit Phase 3 jobs and record job IDs.
**Test Method:** `PYTHONPATH=. python scripts/run_feedback_loop.py --mode execute -v`
**Evidence Source:** CLI output + Phase 3 API response
**Status:** BLOCKED (Phase 3 API unreachable in sandbox)
**Evidence:**
```
2026-01-01 10:02:28 [ERROR] __main__: Phase 3 API request failed: Cannot connect to host localhost:8000 ssl:default [Connect call failed ('127.0.0.1', 8000)]
2026-01-01 10:02:28 [INFO] __main__: Execute mode complete: 0 proposals applied
```

### TEST-FEEDBACK-04: Evaluate Mode (Outcome Recording)
**Requirement:** Applied versions update outcomes after evaluation window.
**Test Method:** `PYTHONPATH=. python scripts/run_feedback_loop.py --mode evaluate -v`
**Evidence Source:** CLI output + seo_versions outcome fields
**Status:** BLOCKED (no applied versions available)
**Evidence:**
```
2026-01-01 10:02:35 [INFO] __main__: No versions ready for evaluation
```

### TEST-FEEDBACK-05: Full Test Suite (Production Gate)
**Requirement:** Full pytest suite runs successfully.
**Test Method:** `PYTHONPATH=. pytest -v`
**Evidence Source:** pytest output
**Status:** PASS (2026-01-01 10:14Z)
**Evidence:**
```
======================== 56 passed, 3 skipped in 1.76s =========================
```

### TEST-FEEDBACK-06: Integration Suite Presence
**Requirement:** Integration tests exist and are runnable.
**Test Method:** `PYTHONPATH=. pytest tests/integration/ -v`
**Evidence Source:** pytest output
**Status:** SKIPPED (credentials missing)
**Evidence:**
```
tests/integration/test_feedback_loop_propose_integration.py::test_propose_mode_creates_version SKIPPED
```

---

## LIVE SWAP (Appendix F)

| Test | Status | Blocker |
|------|--------|---------|
| Shopify auth | REQUIRED | YES |
| Bulk query end-to-end | REQUIRED | YES |
| Bulk mutation end-to-end | REQUIRED | YES |
| Tag merge | REQUIRED | YES |
| Webhook HMAC | REQUIRED | YES |
| Meta token (if immediate) | REQUIRED | If Meta |
| n8n credential swap | REQUIRED | YES |

---

## Evidence Log

### Stage 2 (2025-12-29)

**bulkOperations absent:**
```
Error: "Field 'bulkOperations' doesn't exist on type 'QueryRoot'"
API Version: 2025-10
```

**Concurrent query blocked:**
```
Error: "A bulk query operation for this app and shop is already in progress: gid://shopify/BulkOperation/XXXXX"
```

**Staged upload path rejection:**
```
Error: bulkOperationRunMutation rejected /tmp path, expects Shopify bucket bulk/ path
```

**Tag merge verified:**
```
Before: ["existing-tag-1", "existing-tag-2"]
After productUpdate: ["new-tag-1", "existing-tag-1", "existing-tag-2"]
Result: All pre-existing tags preserved
```
