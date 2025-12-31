# ACCEPTANCE_TESTS.md
# Spec → Test Mapping

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2025-12-29

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
**Status:** READY FOR TEST
**Evidence:**
```bash
# Command output:
[Paste grep results here]

# Manual inspection:
[PASS/FAIL] - .env.example contains complete APEG API Configuration section
[PASS/FAIL] - Active .env contains APEG_API_KEY with non-placeholder value
[PASS/FAIL] - .env.integration.example is deleted OR deprecated OR contains APEG_API_KEY

# Overall Result: [PASS/FAIL]
# Date: [YYYY-MM-DD]
```

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
**Status:** BLOCKED (requires n8n instance + APEG running)
**Evidence:**
```
[Screenshot or error message paste showing 401]
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
**Status:** BLOCKED (requires n8n instance + APEG running)
**Evidence:**
```json
// n8n Response:
{
  "statusCode": 202,
  "body": {
    "job_id": "...",
    "status": "queued",
    "run_id": "n8n-test-dryrun",
    "received_count": 1
  }
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
**Status:** READY FOR TEST (after n8n instance setup)
**Evidence:**
```
[Execution screenshot showing 202 response despite string input]
```

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
**Status:** BLOCKED (requires DEMO store credentials)
**Evidence:**
```
Execution time: Xs
APEG Logs:
[Paste bulk operation logs]
Shopify Admin: [Screenshot showing test tag]
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
**Status:** READY FOR TEST (after template consolidation)
**Evidence:**
```bash
[Paste execution output]
```

---

## PHASE 3 — n8n Orchestration

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| Webhook trigger works | 8.13 | REQUIRED | |
| DEMO workflow execution | 8.13 | REQUIRED | |
| Credential swap verified | 8.13 | REQUIRED | Execution log shows LIVE |

---

## PHASE 4 — Meta Ads

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| Token debug valid + scopes | 6.12 | REQUIRED | |
| Ad account read | 6.12 | REQUIRED | |
| PAUSED campaign create | 6.12 | OPTIONAL | |
| Interest ID lookup | 6.4 | REQUIRED | |

---

## PHASE 5 — CI/CD

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| CI green on PR | Appendix D | REQUIRED | |
| License scan green | Appendix D | REQUIRED | No GPL in prod |
| Coverage gate | Appendix D | REQUIRED | |

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
