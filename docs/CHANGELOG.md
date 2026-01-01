# CHANGELOG.md
# Spec Fixes + Test Evidence Log

> **📍 Quick Links:** [Main README](../README.md) | [Project Plan](PROJECT_PLAN_ACTIVE.md) | [Docs Index](README.md)

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2024-12-31

## 📋 About This Document

This changelog tracks:
- Specification updates and version changes
- Feature implementations and phase completions
- Bug fixes and critical patches
- Test evidence and verification results
- Known limitations and blockers

**Format:** Entries are organized by date (newest first) with phase context.

---

## [2024-12-31] Phase 5: Feedback Loop & Refinement Engine (PARTIAL - ANALYSIS CORE)

### Added - Core Infrastructure
- `src/apeg_core/feedback/schema.py`: Feedback loop database schema
  - seo_versions table (Champion/Challenger snapshots with rollback)
  - feedback_runs table (run tracking and audit)
  - feedback_actions table (action logging)
- `src/apeg_core/feedback/analyzer.py`: Decision engine
  - Strategy-level metrics aggregation
  - Diagnosis matrix (CTR x ROAS -> action recommendations)
  - Candidate selection (underperformers + winners)
  - KPI computation (ROAS, CVR proxy, click proxy)
- `src/apeg_core/feedback/version_control.py`: SEO version management
  - Champion/Challenger snapshot persistence
  - Byte-perfect rollback capability
  - Evaluation outcome tracking
  - Diff computation
- `src/apeg_core/feedback/mapping.py`: Strategy tag mapping resolver
  - Method A: Explicit APEG tracking (strategy_tag_mappings table)
  - Method B: Naming convention parsing
  - Method C: UTM fetch (stub for future)
  - Confidence scoring
- `src/apeg_core/feedback/prompts.py`: LLM prompt builders
  - SEO Challenger generation prompts
  - Strict JSON schema validation
  - Character limit enforcement
  - Prohibited claims checking
- `scripts/run_feedback_loop.py`: CLI entry point
  - Analysis mode (candidate identification)
  - Propose mode (stub - requires LLM integration)
  - Execute mode (stub - requires Phase 3 API integration)
  - Evaluate mode (stub - requires outcome tracking)

### Added - Database Schema
- order_line_attributions (CRITICAL): Product-level attribution
  - Enables product-level ROAS computation
  - Inherits attribution from order-level
  - Line revenue per product/variant
- strategy_tag_mappings: Meta entity -> strategy_tag mapping
  - Supports multiple resolution methods
  - Confidence scoring per mapping
  - Metadata for debugging
- seo_versions: Version control for SEO changes
  - Champion/Challenger snapshot pairs
  - Decision context (metrics, diagnosis, thresholds)
  - Phase 3 job tracking
  - Evaluation windows and outcomes
- feedback_runs: Run audit trail
- feedback_actions: Action-level logging

### Added - Configuration
- `.env.example`: Phase 5 Feedback Loop section
  - FEEDBACK_ENABLED, FEEDBACK_WINDOW_DAYS
  - Minimum data thresholds (spend, impressions, clicks, orders)
  - Diagnosis thresholds (CTR_BAD/GOOD, ROAS_BAD/GOOD)
  - Safety limits (MAX_ACTIONS_PER_RUN)
  - Approval workflow config
  - Decision logging directory

### Features - Diagnosis Matrix
- CTR Low + ROAS High: Refine ad creative
- CTR High + ROAS Low: Refine Shopify SEO
- CTR Low + ROAS Low: Pause strategy
- CTR High + ROAS High: Scale budget
- Insufficient Data: No action

### Features - Version Control
- Champion/Challenger pattern with snapshot pairs
- Byte-perfect rollback (raw snapshot reuse)
- Evaluation windows and outcomes (WIN/LOSS/INCONCLUSIVE/PENDING)
- Status lifecycle: PROPOSED -> APPROVED -> APPLIED -> REVERTED/SUPERSEDED

### Testing
- Unit tests: Diagnosis matrix logic (3 scenarios) + analyzer baseline
- Acceptance tests defined: TEST-FEEDBACK-01 through TEST-FEEDBACK-07

### Known Limitations (Phase 5 Partial)
- LLM integration incomplete (Challenger generation requires Claude API)
- Phase 3 job emission incomplete (apply/rollback require API integration)
- strategy_tag_mappings requires population (manual or automated)
- order_line_attributions requires backfill (rerun Phase 4 collector)
- Evaluation engine not implemented (outcome tracking future work)

### Blockers Resolved
- Product-level attribution: order_line_attributions table added
- Strategy tag mapping: Mapping resolver with multiple methods
- Line item capture: Shopify GraphQL query updated (requires rerun of Phase 4 collector)

### Evidence Source
- Phase 5 Technical Specification
- Diagnosis matrix validated against industry benchmarks (CTR ~1.5%, ROAS ~2-3x)

## [2024-12-31] Phase 4: Data Collection & Metrics Intelligence

### Added - Core Infrastructure
- `src/apeg_core/metrics/schema.py`: SQLite schema with WAL mode
  - metrics_meta_daily table (Meta Ads campaign + ad granularity)
  - order_attributions table (Shopify orders with attribution)
  - collector_state table (idempotency tracking)
  - Indexes for common query patterns
- `src/apeg_core/metrics/attribution.py`: Waterfall attribution algorithm
  - Tier 1: customerJourneySummary.utmParameters (Shopify native)
  - Tier 2: landingPage URL parsing
  - Tier 3: referrerUrl URL parsing
  - Strategy tag matching (exact, substring, slug normalization)
- `src/apeg_core/metrics/meta_collector.py`: Async Meta Marketing API collector
  - Campaign and ad-level insights
  - Rate limiting with semaphore (5 concurrent requests)
  - Pagination handling
  - Fallback for outbound_clicks from actions array
- `src/apeg_core/metrics/shopify_collector.py`: Async Shopify orders collector
  - GraphQL query with customerJourneySummary
  - Attribution waterfall application
  - Strategy tag matching integration
- `src/apeg_core/metrics/collector.py`: Orchestrator service
  - Daily batch collection coordinator
  - Idempotency via collector_state table
  - Backfill gap detection (last 3 days)
  - Timezone-aware \"yesterday\" calculation
- `scripts/run_metrics_collector.py`: CLI entry point
  - Single date collection
  - Date range backfill
  - Verbose logging option

### Added - Configuration
- `.env.example`: Phase 4 Metrics Collection section
  - METRICS_DB_PATH, METRICS_RAW_DIR
  - META_ACCESS_TOKEN, META_AD_ACCOUNT_ID
  - STRATEGY_TAG_CATALOG path
  - METRICS_TIMEZONE, METRICS_COLLECTION_TIME
  - METRICS_BACKFILL_DAYS
- `data/metrics/strategy_tags.json`: Strategy tag catalog template
  - Birthstone campaigns (January-December)
  - Seasonal campaigns (holiday_gifts, artisan_collection)
  - Test tags (apeg_seo_test, apeg_phase3_test)

### Added - Testing
- `tests/unit/test_attribution.py`: Comprehensive attribution logic tests
  - URL parsing with/without UTM parameters
  - Tier 1/2/3/0 attribution selection
  - Strategy tag matching (exact, substring, slug)
  - Evidence JSON structure validation
- `tests/smoke/test_meta_api.py`: Meta API field validation (TEST REQUIRED)
  - Validates spend, impressions, ctr, cpc fields
  - Checks outbound_clicks (direct or actions array)
  - Requires valid Meta credentials
- `tests/smoke/test_shopify_attribution.py`: Shopify attribution validation
  - Validates customerJourneySummary structure
  - Checks lastVisit/firstVisit UTM fields
  - Edge case tolerance for null attribution

### Features
- Idempotent Daily Ingestion: Safe to re-run for same date window
- Dual Persistence: SQLite (queryable) + JSONL (immutable audit)
- Deterministic Attribution: 3-tier waterfall with confidence scoring
- Strategy Tag Linking: utm_campaign -> strategy_tag matching
- Backfill Support: Auto-detect and fill gaps on startup
- Credential Safety: No secrets in logs (tokens redacted)

### Data Flow
1. Determine target date (yesterday in account timezone)
2. Check collector_state for idempotency
3. Meta: Fetch campaign + ad insights -> SQLite + JSONL
4. Shopify: Fetch orders -> Apply attribution -> SQLite + JSONL
5. Record success in collector_state

### Known Limitations (Documented)
- Meta API field validation is TEST REQUIRED (official docs unavailable due to 429)
- Shopify UTM completeness varies (known edge cases with null attribution)
- Single writer pattern (one async task writes to SQLite)
- No automatic retry on failure (manual resubmission required)
- Strategy tag catalog must exist before collector runs

### Evidence Source
- Phase 4 Technical Implementation Brief
- Shopify customerJourneySummary documentation (verified)
- Meta Marketing API field references (third-party, requires smoke test)

## [2024-12-30] Phase 3 Part 2: n8n Configuration + Environment Parity (REVISED)

### Critical Fixes
- Environment Variable Drift: Consolidated .env.integration.example into .env.example (single canonical template)
- n8n Credential Confusion: Clarified Header Auth is within HTTP Request credential (not standalone)
- Array Typing (422 Prevention): Added explicit products array handling pattern for n8n
- Docker Networking: Fixed localhost assumption with LAN IP / Tailscale guidance

### Added
- `docs/N8N_WORKFLOW_CONFIG.md`: Complete n8n workflow configuration guide
  - HTTP Request credential setup (Header Auth within HTTP Request - NOT standalone)
  - Array typing pattern (prevent 422 from stringified products)
  - Docker network configuration (LAN IP, not localhost)
  - Expression mode field mapping (avoid drag-and-drop issues)
  - End-to-end dry run verification test
  - Comprehensive troubleshooting guide
- Environment Parity Gate: Mandatory phase transition blocker in PROJECT_PLAN_ACTIVE.md
- ACCEPTANCE_TESTS.md: n8n verification tests (TEST-N8N-01 through TEST-N8N-05)
- ACCEPTANCE_TESTS.md: Environment parity check (TEST-ENV-01) - BLOCKING

### Changed
- `docs/integration-architecture-spec-v1.4.1.md` Section 1.8: FULL REPLACEMENT
  - Added Environment Governance subsection
  - Added APEG_API_KEY to canonical config surface area
  - Enforced single canonical template (.env.example)
  - Added phase transition blocker for parity check
  - Added Network Configuration variables (APEG_API_BASE_URL)
  - Deprecated multiple .env.*.example templates
- `.env.example`: COMPLETE CONSOLIDATION
  - Added APEG API Configuration section with APEG_API_KEY
  - Added Integration Testing section (commented, for DEMO)
  - Added Network Configuration section (optional, for production)
  - Added Future Integrations placeholders (commented)
  - Now single source of truth for all environments
- `.env.integration.example`: DEPRECATED (deleted OR replaced with pointer)
- `docs/API_USAGE.md`: Major improvements
  - Added \"What is APEG_API_KEY?\" section with generation guidance
  - Clarified user-defined secret (not system-provided)
  - Added security warnings (do not reuse Shopify tokens)
  - Replaced n8n example with pointer to N8N_WORKFLOW_CONFIG.md
  - Added array typing quick reference
- `tests/integration/README.md`: Updated to reference .env.example as canonical template
- `docs/PROJECT_PLAN_ACTIVE.md`:
  - Added Phase Transition Gate (Environment Parity Check) - BLOCKING
  - Reorganized Phase 3 into Part 1 (complete), Part 2 (in progress), Part 3 (backlog)
  - Updated completion criteria to include parity check requirement

### Security
- APEG_API_KEY generation guidance: `openssl rand -hex 32`
- User-defined secret pattern (not system token reuse)
- n8n credential encryption key requirement (N8N_ENCRYPTION_KEY)
- Explicit warnings against placeholder values in production

### Phase 3 Workflow Corrections
- n8n -> APEG: LAN IP / Tailscale (NOT localhost in Docker)
- HTTP Request credential -> Header Auth subtype (NOT standalone)
- products field: Array type enforcement (prevent 422)
- Expression mode: Explicit (fx) instructions (avoid drag-and-drop)

### Architectural Improvements
- Environment Governance: Single canonical template enforced
- Phase Transition Gate: Prevents drift-related failures
- Template Parity Rule: All APEG API vars must exist in .env.example
- Network Configuration: APEG_API_BASE_URL guidance (n8n env, not APEG env)

### Evidence Source
- Phase 3 Part 2 Technical Implementation Brief (REVISED)
- Spec Addendum Package (LANE A-D corrections)
- n8n HTTP Request credential documentation verification
- Docker networking behavior verification (host.docker.internal constraints)

## [2024-12-30] Phase 3: n8n API Layer (REVISED)

### Added
- `src/apeg_core/api/auth.py`: API key authentication using FastAPI APIKeyHeader (401 on missing/invalid)
- `src/apeg_core/api/routes.py`: POST /api/v1/jobs/seo-update with BackgroundTasks and aiohttp timeouts
- `src/apeg_core/main.py`: FastAPI application factory (with SAFETY LOCK: create only if missing)
- `tests/unit/test_api_auth.py`: Unit tests for 401 behavior on missing/invalid API key
- `tests/unit/test_api_routes.py`: Unit tests for job submission (401/400/202 responses)
- `docs/API_USAGE.md`: API documentation with PYTHONPATH command and BackgroundTasks limitation

### Features
- HTTP contract for n8n: immediate 202 response with background execution
- API key authentication: X-APEG-API-KEY header validation (401 with WWW-Authenticate)
- Shop domain validation: rejects cross-store write attempts (400)
- Safe-write tag merging: (current ∪ tags_add) - tags_remove
- Dry run mode: validate payload without executing Shopify writes
- Exception-safe background tasks: failures logged, never crash server
- aiohttp timeouts: 30s connect, 300s total
- Request/response models: rigid Pydantic schemas for n8n
- PYTHONPATH execution documentation: prevents import errors

### Security
- APIKeyHeader security dependency (FastAPI standard pattern)
- 401 Unauthorized with WWW-Authenticate header for missing/invalid keys
- Shop domain validation prevents cross-store operations

### Limitations (Documented)
- Background tasks are in-process and not persisted
- Server restart will interrupt running jobs
- No automatic retry or status callback (future enhancement)

### Evidence Source
- Phase 3 Technical Implementation Brief (Revised)
- FastAPI BackgroundTasks documentation
- FastAPI security documentation (APIKeyHeader)

## [2024-12-30] Phase 2 Closeout: Integration Verification PASS

### Verified
- 12.30 Phase 2 integration verification PASS; safe write + staged upload dance + cleanup

### Evidence
- Command: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py`

## [2024-12-30] Phase 2 Schema Fix: Complete groupObjects Removal

### Fixed (CRITICAL)
- **Schema Validation Error**: Removed ALL instances of `groupObjects`
  from bulkOperationRunMutation
- Removed `$groupObjects` variable declaration from GraphQL mutation string
- Removed `groupObjects:` argument from mutation call
- Removed `group_objects` parameter from Python method signature
- Removed `"groupObjects"` from variables payload

### Root Cause
- `groupObjects` is query-only (accepted by `bulkOperationRunQuery`)
- It is NOT accepted by `bulkOperationRunMutation` in current API schema
- Error was: "Field 'groupObjects' doesn't exist on type 'BulkOperationRunMutationInput'"
- Secondary error: "Variable $groupObjects is declared but not used"

### Changed Files
- `src/apeg_core/shopify/graphql_strings.py`: MUTATION_BULK_OPERATION_RUN_MUTATION (removed both declaration and argument)
- `src/apeg_core/shopify/bulk_mutation_client.py`: _bulk_operation_run_mutation (removed parameter and payload entry)
- `docs/integration-architecture-spec-v1.4.1.md`: Removed all mutation-context groupObjects references
- `docs/PROJECT_PLAN_ACTIVE.md`: Marked Phase 2 as VERIFIED after integration test pass

### Verification Steps
1. Code sweep: `rg -n "groupObjects|$groupObjects|group_objects" src/apeg_core/` (expect: 0 hits)
2. Integration test: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py` (expect: exit 0)

### Status
- Code fix: COMPLETE
- Integration verification: PENDING (requires DEMO store + Redis)

## [2024-12-30] Phase 2 Schema Fix: Remove groupObjects

### Fixed
- **CRITICAL**: Removed invalid `groupObjects` parameter
  from bulkOperationRunMutation
- Schema validation now passes (groupObjects is query-only, not accepted for mutations)
- Aligned JSONL Content-Type to `text/jsonl` throughout code and documentation
- Spec version consistency: all references now show 1.4.1

### Changed
- `src/apeg_core/shopify/graphql_strings.py`: MUTATION_BULK_OPERATION_RUN_MUTATION (removed groupObjects)
- `src/apeg_core/shopify/bulk_mutation_client.py`: _bulk_operation_run_mutation signature (removed group_objects param)
- `docs/integration-architecture-spec-v1.4.1.md`: Removed groupObjects from mutation examples
- `docs/integration-architecture-spec-v1.4.1.md`: Fixed Content-Type examples (application/jsonl → text/jsonl)

### Evidence Source
- Live API schema validation error (groupObjects not accepted)
- Shopify Admin GraphQL schema documentation (bulkOperationRunMutation)

### Verification
- Integration test status: PENDING (run after patch)
- Command: `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py`

## [2024-12-30] Phase 2: Bulk Mutations + Safe Writes (CRITICAL BUG FIX)

### Critical Bug Fix
- **GraphQL root error handling**: ALL GraphQL responses now check root ["errors"] BEFORE accessing ["data"]
- Prevents `KeyError: 'data'` crashes when Shopify returns errors without data payload
- Applied to Phase 1 `ShopifyBulkClient._post_graphql()` and all Phase 2 operations

### Added
- `src/apeg_core/shopify/graphql_strings.py`: Canonical GraphQL query/mutation strings
- `src/apeg_core/shopify/bulk_mutation_client.py`: ShopifyBulkMutationClient with staged upload
- `src/apeg_core/schemas/bulk_ops.py`: Extended with mutation models (ProductUpdateSpec, StagedTarget, BulkOperationRef)
- `tests/unit/test_graphql_error_handling.py`: Regression test for root error handling
- `tests/unit/test_bulk_mutation_client.py`: Mock tests for mutation client

### Features
- 4-step Staged Upload Dance: stagedUploadsCreate → multipart upload → bulkOperationRunMutation → poll
- Safe tag hydration: fetch_current_tags() + merge (current ∪ tags_add) - tags_remove
- Multipart form ordering enforcement: parameters first, file field LAST (prevents 403 errors)
- Redis mutation lock (1 concurrent mutation per shop, 30min TTL)
- Audit logging: run_id, bulk_op_id, update_count, status transitions

### Evidence Source
- Phase 2 Technical Specification (APEG FORMAT)
- Shopify Admin GraphQL API: stagedUploadsCreate, bulkOperationRunMutation, productUpdate
- Root error handling bug discovered in production testing

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
