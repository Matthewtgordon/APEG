# CHANGELOG.md
# Spec Fixes + Test Evidence Log

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2024-12-30

---

## [1.4.1] - 2024-12-30

### Documentation Baseline Corrections

### Changed
- SPEC-HDR-01: Bumped spec version to 1.4.1
- SPEC-01-07: Verified Section 1.7 Shopify constraint language
- SPEC-07-01: Corrected CustomerJourney semantics (attribution window)
- DOCS-AT-TR-01: Added explicit evidence sources to acceptance tests
- DOCS-CL-01: Moved Legacy App + CustomerJourney to Verified/Closed
- DOCS-PP-FMT-01: Standardized all checklist formatting
- DOCS-PP-SAFE-01: Added Safety Lock language for .env operations
- DOCS-PP-02: Inserted Phase 0 Executable Start Plan

### Evidence
- All changes verified via grep commands in Step 1-8 verification blocks

### Verified / Closed
- Legacy custom app creation constraint (Stage 2 Research Log)
- CustomerJourney 30-day attribution window semantics (Stage 2 Research Log)

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
