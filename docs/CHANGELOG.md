# CHANGELOG.md
# Spec Fixes + Test Evidence Log

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2024-12-30

---

## [2024-12-30] Phase 1: Shopify Bulk Client Implementation

### Added
- `src/apeg_core/schemas/bulk_ops.py`: BulkOperation Pydantic model with terminal state helpers
- `src/apeg_core/shopify/exceptions.py`: Custom exception hierarchy for bulk operations
- `src/apeg_core/shopify/bulk_client.py`: Async ShopifyBulkClient with Redis concurrency locks
- `tests/unit/test_bulk_client_mock.py`: Mock-based unit tests for bulk client

### Features
- Redis-based "1 concurrent job per shop" enforcement with lock TTL refresh
- Defensive retry logic: Retry-After header support, exponential backoff with jitter
- GraphQL operations: bulkOperationRunQuery (submit), node(id) polling (no deprecated currentBulkOperation)
- Terminal state detection: COMPLETED (with url validation), FAILED/CANCELED/EXPIRED (with partial_data_url)

### Evidence Source
- Technical Implementation Brief (Stage 2 Research Log derivatives)
- Shopify Admin GraphQL API documentation (bulk operations)

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
| customerJourney retention | Locate official doc (not blocking) |
| OpenAPI expansion | Design work when APEG finalized |

---

## Blocking Issues

| Item | Resolution Path |
|------|-----------------|
| Etsy GPL licensing | Microservice isolation or custom REST before Phase 5 |
