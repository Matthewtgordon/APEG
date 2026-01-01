# PROJECT_PLAN_ACTIVE.md
# EcomAgent + APEG Execution Plan

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2025-12-29  
**Current Phase:** PHASE 0

---
## RETAIN FORMAT DO NOT RESTRUCTURE
## PHASE TRANSITION GATE (MANDATORY)

**Environment Parity Check:** PASS required before marking any phase complete.

**Purpose:** Prevent environment variable drift that causes runtime failures.

**Check Procedure:**
```bash
# Verify .env was created from latest .env.example
grep -R "APEG_API_KEY" .env*.example

# Expected output: At least one match showing APEG_API_KEY exists
# .env.example:XX:APEG_API_KEY=...
```

**Manual Verification:**
1. Open `.env.example` and your active `.env` (or `.env.integration`, `.env.production`)
2. Confirm ALL variables in "APEG API Configuration" section exist in active env
3. Confirm APEG_API_KEY has a valid value (not placeholder)

**Evidence Required:**
- Paste command output into ACCEPTANCE_TESTS.md under TEST-ENV-01
- Record PASS or FAIL with timestamp

**Blocking Rule:** No phase can be marked complete until Environment Parity Check shows PASS.

---
## PHASE 0 — CONFIG + CUTOVER READINESS ⬅️ ACTIVE

**Spec Anchors:** Section 1.8, Appendix F, Security section

### PHASE 0: Documentation Baseline

- [X] Done 12.30: Documentation baseline corrections (spec v1.4.1 + safety locks + env standardization)

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| `.env.example` (no secrets) | [ ] ToDo: | 1.8 |
| `ENVIRONMENT.md` | [ ] ToDo: | 1.8, Appendix F |
| Config loader + validation | [ ] ToDo: | 1.8 |
| Secrets via env/secret store only | [ ] ToDo: | 1.8 |

**Acceptance Tests:**
- [ ] ToDo: Shopify auth smoke: `{ shop { name } }` returns store name
- [ ] ToDo: Meta token debug: valid + required scopes
- [ ] ToDo: n8n credential mapping verified (demo credential ID documented)

## PHASE 0 — EXECUTABLE START PLAN

- [ ] ToDo: Confirm Shopify app creation path (Dev Dashboard required for new apps after 2026-01-01; existing legacy custom apps unaffected).
- [ ] ToDo: Update `.env.example` with any new required keys (no secrets).
- [ ] ToDo: Create `.env` only if missing.
- [ ] ToDo: If `.env` exists and must be changed, run backup first:
```bash
      cp .env .env.bak.$(date +%Y%m%d-%H%M%S)
```
- [ ] ToDo: Run Shopify auth smoke test (GraphQL: { shop { name } }) and paste evidence into ACCEPTANCE_TESTS.
- [ ] ToDo: Record n8n credential IDs (DEMO) and paste evidence into ACCEPTANCE_TESTS.
- [ ] ToDo: Decide Meta timing:
    - If Phase 4 planned in next sprint: run token debug now and paste evidence into ACCEPTANCE_TESTS.
    - Else: mark Meta token debug as DEFERRED in PROJECT_PLAN_ACTIVE and ACCEPTANCE_TESTS.

---

## PHASE 1 — DETERMINISTIC SHOPIFY BACKBONE

**Spec Anchors:** Section 5.6, Section 5.10, Section 2.4.2

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| BulkJob model (id, type, status, shop_domain) | [ ] ToDo: | 5.6 |
| Distributed lock (1 query + 1 mutation per shop) | [ ] ToDo: | 5.10 |
| Poller: `node(id:) ... on BulkOperation` | [ ] ToDo: | 5.6 |
| Staged upload wrapper (hard gate on failure) | [ ] ToDo: | 5.5 |

**Acceptance Tests (VERIFIED in Stage 2):**
- [X] Done 12.29: Bulk query → COMPLETED via node(id:) polling
- [X] Done 12.29: Bulk mutation → COMPLETED via staged upload path
- [X] Done 12.29: Upload hard-gate: non-2xx prevents runMutation
- [X] Done 12.29: Tag merge preserves existing tags

---

### PHASE 1: Core Async Engine

- [X] Done 12.30: Shopify Bulk Client (schemas + async client + Redis locks + tests)
- [ ] ToDo: JSONL Parser (async streaming from Shopify bulk result URLs)
- [ ] ToDo: Integration Tests (real Shopify API + Redis, gated by .env credentials)

## PHASE 2 — SHOPIFY MUSCLE LAYER (SAFE WRITES)

### PHASE 2: Bulk Mutations & Safe Write (VERIFIED - Integration PASS 12.30)

- [X] Done 12.30: Bulk Mutation Client (staged upload + safe tag merge + unit tests)
- [X] Done 12.30: verify_phase2_safe_writes.py PASS (safe write + staged upload + cleanup)
- [ ] ToDo: Error recovery patterns (partialDataUrl handling)

**Spec Anchors:** Section 2.4.2, product update rules

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| Tag hydration tool (fetch → union → update) | [ ] ToDo: | 2.4.2 |
| SEO update tool (ProductInput.seo) | [ ] ToDo: | 2.3 |
| Audit logging for all writes | [ ] ToDo: | 9.x |

**Acceptance Tests:**
- [ ] ToDo: Write ops in DEMO with rollback plan
- [ ] ToDo: Audit log captures before/after state

---

## PHASE 3 — N8N ORCHESTRATION BINDINGS

**Spec Anchors:** Section 8.13, workflow triggers

### PHASE 3: n8n Orchestration Bindings

#### Part 1: FastAPI Backend (COMPLETE)
- [X] Done 12.30: FastAPI endpoint (POST /api/v1/jobs/seo-update)
- [X] Done 12.30: API key authentication (X-APEG-API-KEY → 401 on invalid)
- [X] Done 12.30: Background task dispatch (FastAPI BackgroundTasks)
- [X] Done 12.30: Safe-write pipeline integration (Phase 2 client)
- [X] Done 12.30: aiohttp timeout configuration (30s connect, 300s total)
- [X] Done 12.30: PYTHONPATH execution documentation

#### Part 2: n8n Integration + Environment Parity (IN PROGRESS)
- [X] Done 12.30: Environment parity enforcement (BLOCKER - must pass before phase complete)
  - [X] Done 12.30: Consolidate .env.example (single canonical template)
  - [X] Done 12.30: Deprecate .env.integration.example
  - [X] Done 12.30: Section 1.8 update (environment governance)
  - [X] Done 12.30: TEST-ENV-01 execution + PASS evidence
- [X] Done 12.30: n8n workflow configuration
  - [X] Done 12.30: Create N8N_WORKFLOW_CONFIG.md with corrections
  - [X] Done 12.30: HTTP Request credential setup (Header Auth within HTTP Request)
  - [X] Done 12.30: Array typing pattern (products field)
  - [X] Done 12.30: Docker networking guidance (no localhost assumption)
- [ ] ToDo: n8n verification tests (remaining)
  - [X] Done 12.30: TEST-N8N-01: Auth failure (401) - negative test
  - [X] Done 12.30: TEST-N8N-02: Dry run (202) - happy path
  - [X] Done 01.01: TEST-N8N-03: Live execution - background job proof (bulk op gid://shopify/BulkOperation/4412960243814)
- [X] Done 12.30: Documentation updates
  - [X] Done 12.30: API_USAGE.md: APEG_API_KEY clarity + n8n pointer
  - [X] Done 12.30: Integration test README: template reference updates

#### Part 3: Future Enhancements (BACKLOG)
- [ ] Future: Job status callback endpoint (webhook for completion)
- [ ] Future: Persistent job queue (Celery/RQ)
- [ ] Future: GET /api/v1/jobs/{job_id} status query endpoint

**Phase 3 Completion Criteria:**
1. All tests in ACCEPTANCE_TESTS.md (TEST-API-01 through TEST-N8N-03) recorded as PASS
2. Environment Parity Check (TEST-ENV-01) recorded as PASS
3. n8n workflow executes successfully (minimum: TEST-N8N-02 dry run)
4. Evidence recorded in ACCEPTANCE_TESTS.md for all verification tests

**Acceptance Tests:**
- [X] Done 01.01: Workflow run in DEMO produces correct outputs (n8n-manual-test-01)
- [ ] ToDo: Post-swap: LIVE credential in execution log

---

## PHASE 4 — DATA COLLECTION & METRICS INTELLIGENCE

### PHASE 4: Data Collection & Metrics Intelligence (IN PROGRESS)

#### Part 1: Core Infrastructure (COMPLETE)
- [X] Done 12.31: SQLite schema (metrics_meta_daily, order_attributions, collector_state)
- [X] Done 12.31: Attribution logic (3-tier waterfall algorithm)
- [X] Done 12.31: Meta Insights collector (async, rate-limited)
- [X] Done 12.31: Shopify Orders collector (async, GraphQL)
- [X] Done 12.31: Orchestrator service (daily batch coordinator)
- [X] Done 12.31: Strategy tag catalog template
- [X] Done 12.31: CLI entry point (run_metrics_collector.py)

#### Part 2: Validation & Testing (BLOCKED - REQUIRES CREDENTIALS)
- [ ] ToDo: Meta API smoke test execution (TEST-META-01) — SKIPPED 01.01 (no ad spend data; rerun when data available)
  - Validate outbound_clicks field availability
  - Confirm spend/impressions/ctr/cpc fields
  - Record evidence in ACCEPTANCE_TESTS.md
- [ ] ToDo: Shopify attribution smoke test (TEST-SHOPIFY-01) — SKIPPED 01.01 (no orders in test date range; rerun when orders exist)
  - Validate customerJourneySummary fields
  - Confirm UTM parameters structure
  - Record edge case behavior
- [X] Done 01.01: SQLite idempotency test (TEST-COLLECTOR-01)
  - Run collector twice for same date
  - Verify no duplicates, stable row counts
  - Confirm collector_state behavior
- [ ] ToDo: End-to-end collection test (TEST-COLLECTOR-02)
  - Full daily collection (Meta + Shopify)
  - Verify JSONL + SQLite writes
  - Validate attribution tier distribution

#### Part 3: Production Deployment (BACKLOG)
- [ ] Future: Scheduler implementation (cron/systemd)
- [ ] Future: Meta ad account timezone API retrieval
- [ ] Future: Webhook notifications on collection completion
- [ ] Future: Metrics dashboard (query SQLite for insights)

**Phase 4 Completion Criteria:**
1. All smoke tests executed with PASS (TEST-META-01, TEST-SHOPIFY-01)
2. Idempotency test PASS (TEST-COLLECTOR-01)
3. End-to-end collection test PASS (TEST-COLLECTOR-02)
4. Strategy tag catalog populated with production campaigns
5. Evidence recorded in ACCEPTANCE_TESTS.md for all tests

---

## PHASE 5 — FEEDBACK LOOP & REFINEMENT ENGINE

### PHASE 5: Feedback Loop & Refinement Engine (IN PROGRESS)

#### Part 1: Core Analysis & Decision Engine (COMPLETE)
- [X] Done 12.31: Feedback database schema (seo_versions, feedback_runs, feedback_actions)
- [X] Done 12.31: Product-level attribution (order_line_attributions table)
- [X] Done 12.31: Strategy tag mapping resolver (multiple methods)
- [X] Done 12.31: Analyzer module (metrics aggregation, diagnosis matrix)
- [X] Done 12.31: Version control module (Champion/Challenger, rollback)
- [X] Done 12.31: LLM prompt builders (schema validation)
- [X] Done 12.31: CLI entry point (analysis mode functional)
- [X] Done 12.31: Unit tests (diagnosis matrix, analyzer logic)

#### Part 2: LLM Integration & Job Emission (BLOCKED)
- [ ] ToDo: Claude API integration for Challenger generation
  - Requires ANTHROPIC_API_KEY configuration
  - Implement async LLM client with retry logic
  - Integrate prompt builder + output validation
- [ ] ToDo: Phase 3 job emission implementation
  - POST to /api/v1/jobs/seo-update
  - Track phase3_job_id in seo_versions
  - Rollback job emission (restore Champion)
- [ ] ToDo: Propose mode implementation
  - Load candidates from analyzer
  - Generate Challengers via LLM
  - Create seo_versions proposals
  - Require approval workflow
- [ ] ToDo: Execute mode implementation
  - Approve -> emit Phase 3 jobs
  - Mark as applied with evaluation window
  - Record job_id

#### Part 3: Data Dependencies (BLOCKED - REQUIRES BACKFILL)
- [ ] ToDo: Populate strategy_tag_mappings table
  - Method A: Track APEG ad creation (future)
  - Method B: Parse existing campaign/ad names
  - Method C: Fetch utm_campaign from ad URLs
- [ ] ToDo: Backfill order_line_attributions
  - Rerun Phase 4 Shopify collector with updated GraphQL query
  - Verify product-level ROAS computation
  - Record evidence in ACCEPTANCE_TESTS.md (TEST-FEEDBACK-04)

#### Part 4: Evaluation Engine (BACKLOG)
- [ ] Future: Outcome evaluation (compare pre/post windows)
- [ ] Future: Winner promotion (supersede Champion with Challenger)
- [ ] Future: Auto-rollback on LOSS outcome
- [ ] Future: Budget automation (scale recommendations -> execution)

**Phase 5 Completion Criteria:**
1. All acceptance tests pass (TEST-FEEDBACK-01 through TEST-FEEDBACK-04)
2. LLM integration functional (Challenger generation working)
3. Phase 3 job emission working (apply + rollback verified)
4. strategy_tag_mappings populated (at least Method B coverage)
5. order_line_attributions populated (backfill complete)
6. Evidence recorded in ACCEPTANCE_TESTS.md

---

## PHASE 6 — HARDENING + CI/CD

**Spec Anchors:** Appendix D (CI), license scan

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| CI workflows (tests + license scan) | [ ] ToDo: | Appendix D |
| Coverage gate | [ ] ToDo: | Appendix D |
| GPL denylist enforcement | [ ] ToDo: | Section 1.7 |

**Acceptance Tests:**
- [ ] ToDo: CI green on PR
- [ ] ToDo: License scan green (no GPL in prod deps)

---

## LIVE SWAP CHECKLIST

See Appendix F in spec. Execute only when:
- [ ] ToDo: All Phase 0-3 acceptance tests PASS in DEMO
- [ ] ToDo: Smoke tests documented in ACCEPTANCE_TESTS.md
- [ ] ToDo: Credential swap procedure rehearsed

---

## AGENT ALIGNMENT RULE

Every PR must reference:
1. Spec section(s)
2. Phase item
3. Acceptance test(s)

If test contradicts spec → patch spec first via CHANGELOG, then code.
