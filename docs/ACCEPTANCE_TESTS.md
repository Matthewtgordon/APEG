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

## Phase 2: Shopify Bulk Mutations

### TEST-MUTATION-01: Staged Upload Workflow (4-Step Dance)
**Requirement:** Complete stagedUploadsCreate → multipart upload → bulkOperationRunMutation → poll
**Test Method:**
1. Run mock test: `pytest tests/unit/test_bulk_mutation_client_mock.py::test_staged_uploads_create_success -v`
2. Verify StagedTarget model populated with url + parameters
3. Verify staged_upload_path extracted from "key" parameter
**Evidence Source:** Unit test execution log
**Status:** READY FOR TEST

### TEST-MUTATION-02: Multipart File Ordering
**Requirement:** File field MUST be last in multipart/form-data (prevents 403)
**Test Method:**
1. Run mock test: `pytest tests/unit/test_bulk_mutation_client_mock.py::test_upload_jsonl_multipart_ordering -v`
2. Inspect code: `grep -A 10 "add_field.*file" src/apeg_core/shopify/bulk_mutation_client.py`
3. Verify file field added AFTER parameter loop
**Evidence Source:** Code inspection + unit test
**Status:** READY FOR TEST

### TEST-MUTATION-03: Safe Tag Merge (Union Pattern)
**Requirement:** Tags MUST be read-before-write; never blindly overwrite
**Test Method:**
1. Run mock test: `pytest tests/unit/test_bulk_mutation_client_mock.py::test_merge_product_updates_safe_write -v`
2. Verify merged tags = current_tags ∪ incoming_tags
3. Verify existing tags not removed
**Evidence Source:** Unit test execution log
**Status:** READY FOR TEST

### TEST-MUTATION-04: JSONL Schema Compliance
**Requirement:** Each JSONL line uses {"product": {...}} format matching GraphQL variables
**Test Method:**
1. Run mock test: `pytest tests/unit/test_bulk_mutation_client_mock.py::test_product_update_input_to_jsonl_dict -v`
2. Verify output matches: `{"product": {"id": "...", "tags": [...], "seo": {...}}}`
**Evidence Source:** Unit test execution log
**Status:** READY FOR TEST

### TEST-MUTATION-05: Mutation Lock Enforcement
**Requirement:** Only 1 concurrent bulk mutation per shop
**Test Method:**
1. Run mock test: `pytest tests/unit/test_bulk_mutation_client_mock.py::test_run_product_update_bulk_lock_failure -v`
2. Verify ShopifyBulkMutationLockedError raised when lock unavailable
**Evidence Source:** Unit test execution log
**Status:** READY FOR TEST

### TEST-MUTATION-06: GraphQL String Verbatim Compliance
**Requirement:** Use exact GraphQL strings from spec (no modifications)
**Test Method:**
1. Inspect: `grep -A 5 "MUTATION_PRODUCT_UPDATE" src/apeg_core/shopify/bulk_mutation_client.py`
2. Verify mutation matches spec: `mutation call($product: ProductUpdateInput!) { productUpdate(...) }`
3. Inspect: `grep -A 10 "MUTATION_STAGED_UPLOADS_CREATE" src/apeg_core/shopify/bulk_mutation_client.py`
4. Verify resource=BULK_MUTATION_VARIABLES, httpMethod=POST
**Evidence Source:** Code inspection
**Status:** READY FOR TEST

---

## PHASE 2 — Safe Writes

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| Tag hydration (fetch→union→update) | 2.4.2 | REQUIRED | |
| SEO update via ProductInput.seo | 2.3 | REQUIRED | |
| Audit log before/after | 9.x | REQUIRED | |
| Rollback procedure tested | Appendix F | REQUIRED | |

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
