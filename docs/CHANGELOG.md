# CHANGELOG.md
# Spec Fixes + Test Evidence Log

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2024-12-30

---

## [2024-12-30] Phase 0 & 1: Documentation Baseline + Core Engine

### Phase 0: Documentation Baseline Corrections
**Changed:**
- Spec version bumped to 1.4.1
- Section 1.7: Added Shopify custom app creation constraint (post-2026-01-01)
- Section 7: Corrected CustomerJourney semantics (30-day attribution window)
- Standardized env var: `SHOPIFY_API_TOKEN` → `SHOPIFY_ADMIN_ACCESS_TOKEN` (canonical)
- Applied Safety Lock language for `.env` operations (backup before overwrite)
- Added Phase 0 Executable Start Plan checklist

**Evidence Source:**
- Stage 2 Research Log (Shopify policy updates)
- Safety requirements documentation

### Phase 1: Shopify Bulk Client Implementation
**Added:**
- `src/apeg_core/schemas/bulk_ops.py`: BulkOperation Pydantic model with terminal state helpers
- `src/apeg_core/shopify/exceptions.py`: Custom exception hierarchy for bulk operations
- `src/apeg_core/shopify/bulk_client.py`: Async ShopifyBulkClient with Redis concurrency locks
- `tests/unit/test_bulk_client_mock.py`: Mock-based unit tests for bulk client

**Features:**
- Redis-based "1 concurrent job per shop" enforcement with lock TTL refresh
- Defensive retry logic: Retry-After header support, exponential backoff with jitter
- GraphQL operations: `bulkOperationRunQuery` (submit), `node(id)` polling (no deprecated currentBulkOperation)
- Terminal state detection: COMPLETED (with url validation), FAILED/CANCELED/EXPIRED (with partial_data_url)

**Evidence Source:**
- Technical Implementation Brief (Phase 1)
- Shopify Admin GraphQL API documentation (bulk operations)

---

## [2024-12-30] Phase 2: Bulk Mutations & Safe Tag Hydration

### Added
- `src/apeg_core/schemas/bulk_ops.py`: Extended with StagedTarget, ProductUpdateInput, ProductCurrentState models
- `src/apeg_core/shopify/bulk_mutation_client.py`: ShopifyBulkMutationClient with staged upload workflow
- `src/apeg_core/shopify/exceptions.py`: ShopifyBulkMutationLockedError, ShopifyStagedUploadError
- `tests/unit/test_bulk_mutation_client_mock.py`: Mock-based unit tests for mutation client
- `docs/PHASE2_INTEGRATION_TEST_PLAN.md`: Integration test plan for safe-write validation

### Features
- 4-step Staged Upload Dance: stagedUploadsCreate → multipart upload → bulkOperationRunMutation → poll
- Safe tag hydration: fetch_current_product_state() + merge_product_updates() (union merge pattern)
- Multipart form ordering enforcement: file field LAST (prevents 403 errors)
- Redis mutation lock (1 concurrent mutation per shop, 1-hour TTL)
- Reuses Phase 1 ShopifyBulkClient for polling and retry logic

### Evidence Source
- Technical Implementation Brief (Shopify Staged Upload documentation derivatives)
- Shopify Admin GraphQL API: stagedUploadsCreate, bulkOperationRunMutation, productUpdate

---

## [2024-12-30] Phase 2 Integration Test Harness

### Added
- `tests/integration/verify_phase2_safe_writes.py`: Real Shopify API integration tests
- `tests/integration/README.md`: Integration test documentation
- `.env.integration.example`: Template for integration test environment

### Features
- Three-tier safety gates: APEG_ENV=DEMO + store allowlist + explicit write flag
- Safe tag merge validation: read-merge-write pattern verification
- Staged upload dance validation: end-to-end workflow test
- Cleanup guarantee: created test products MUST be deleted (even on failure)
- Exit code semantics: 0=pass, 1=test fail, 2=safety gate fail

### Test Scenarios
- Scenario 1: Safe tag merge preserves original tags while adding new tags
- Scenario 2: Staged upload dance completes without 403/400 errors

### Evidence Source
- Phase 2 Integration Test Harness Spec (contribution document)
- PHASE2_INTEGRATION_TEST_PLAN.md (test plan reference)

---

## [1.4] - 2025-12-29

### Added
- **Section 1.8:** Config surface area (Shopify, Meta, n8n, Infra vars)
- **Section 6.12:** Meta Ads deployment config + smoke tests
- **Section 8.13:** n8n credential swap checklist
- **Appendix F:** Demo→Live swap runbook

### Changed
- **Section 5.5:** Upload hard gate (prevents "JSONL file not found")

---

## [1.3] - 2025-12-29 (Stage 2 Runtime Verification)

### Changed
- **Section 5.6:** Replaced `bulkOperations(...)` with `node(id:)` polling
  - Evidence: "Field 'bulkOperations' doesn't exist on type 'QueryRoot'"
- **Section 5.10:** Shop-specific distributed locks
  - Evidence: "already in progress" on concurrent start
- **Section 2.4.2:** Tag MERGE marked VERIFIED
- **Section 7:** customerJourney "do not gate build/deploy"
- **Section 5.5:** stagedUploadPath guardrail

---

## [1.2] - 2025-12-29 (Lane A/B Audit)

### Changed
- SHOPIFY_API_VERSION: '2024-10' → '2025-10'
- Bulk concurrency: "1 query + 1 mutation per shop"
- Fixed HMAC import bug
- license-scan.yml installs deps before scanning
- PostgresSaver setup (not SQLite DDL)

### Added
- 2026-01-01 custom app creation note
- customerJourney retention UNVERIFIED
- Meta error code citations (80004, 368)

---

## [1.1] - 2025-12-29 (Initial Audit)

### Added
- **Section 1.7:** GPL/etsyv3 licensing blocker
- **Section 2.4.2:** Explicit tag merge policy
- **Appendix D:** Machine-readable artifact stubs
- Developer Changelog monitoring note
- MCP clarification

---

## Evidence Links

| Change | Test | Result |
|--------|------|--------|
| node(id:) polling | Stage 2 Test 1 | PASS |
| Sequential lock | Stage 2 Test 1B | PASS |
| Staged upload | Stage 2 Test 3 | PASS |
| Tag merge | Stage 2 Test 2 | PASS |

---

## Pending Verification

| Item | Action Required |
|------|-----------------|
| OpenAPI expansion | Design work when APEG finalized |

---

## Blocking Issues

| Item | Resolution Path |
|------|-----------------|
| Etsy GPL licensing | Microservice isolation or custom REST before Phase 5 |