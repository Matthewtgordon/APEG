# APEG Project Execution Plan - Draft 1

**Created:** 2026-01-01
**Author:** Claude Sonnet 4.5 (Project Audit & Planning)
**Status:** READY_FOR_EXECUTION
**Phase Scope:** Complete Phases 1-5 (Data/Metrics Foundation)
**Future Scope:** Phases 7+ (EcomAgent Integration, Advertising Agent, Google Sheets)

**Reference Documents:**
- `.agent/AGENTS.md` - Project context, invariants, commands
- `.agent/PLANS.md` - ExecPlan protocol for autonomous execution
- `docs/PROJECT_PLAN_ACTIVE.md` - Current phase tracking
- `docs/integration-architecture-spec-v1.4.1.md` - Complete system vision (10,337 lines)

---

## Purpose / Big Picture

**AFTER completing this plan**, the APEG system will have:
1. A fully operational metrics collection and feedback loop (Phases 1-5 complete)
2. Empty tables populated with real data (strategy_tag_mappings, order_line_attributions)
3. Functional LLM-driven SEO refinement engine with job emission to Shopify
4. Automated daily metrics collection with CI/CD pipeline
5. Clean, maintainable documentation without redundancy
6. Clear roadmap for future integrations (EcomAgent, Advertising Agent, Google Sheets)

**BEFORE this plan**, the system has:
- Excellent infrastructure (Phases 1-3 complete, 4-5 partial)
- Empty data tables blocking Phase 5 execution
- LLM integration structure without implementation
- No automation (manual collection, no CI/CD)
- Documentation spread across 10K+ line aspirational spec

**User-Visible Outcome:**
An autonomous agent can execute Phases 1-5 to completion, handle blockers gracefully by documenting and deferring them, and leave clear handoff for human review or future phases.

---

## Autonomous Execution Workflow

### For Agents Joining This Project

**Step 1: Read Context Documents (Required)**
```bash
# Read in this order:
1. /home/matt/repos/APEG/.agent/AGENTS.md        # Project invariants, commands, boundaries
2. /home/matt/repos/APEG/.agent/PLANS.md         # ExecPlan protocol
3. This file                                       # Execution plan
```

**Step 2: Verify Environment**
```bash
cd /home/matt/repos/APEG
source .venv/bin/activate                         # REQUIRED before any Python commands
PYTHONPATH=. pytest -v                            # Baseline test verification
```

**Step 3: Check Current State**
```bash
git status                                         # Uncommitted changes?
cat docs/PROJECT_PLAN_ACTIVE.md | grep "PHASE"   # Current phase status
```

**Step 4: Execute from Progress Section**
- Find first unchecked `[ ]` item in "Progress - Current Work" below
- Execute that task following the detailed instructions
- Update Progress section with timestamp: `[x] (2026-01-01 HH:MMZ) Task description`
- Commit changes with descriptive message
- Continue to next item

**Step 5: Handle Blockers (See "Blocker Handling Protocol" Below)**

**Step 6: Update This Document**
- Add discoveries to "Surprises & Discoveries"
- Add decisions to "Decision Log"
- Update completion status in Progress

---

## Blocker Handling Protocol

### Critical Rule: DO NOT HALT ALL WORK

When you encounter a blocker, follow this decision tree:

```
BLOCKER ENCOUNTERED
    │
    ├─ Is it a HARD blocker? (Missing credentials, broken dependency, data corruption)
    │   ├─ YES → Mark task as BLOCKED in Progress
    │   │        Document in "Blockers & Deferred Items" section
    │   │        SKIP to next independent task
    │   │        Create GitHub issue with details
    │   │        CONTINUE with other work
    │   │
    │   └─ NO → It's a SOFT blocker
    │
    ├─ Is it a missing external resource? (API credentials, test data, external service)
    │   ├─ YES → Mark as DEFERRED in Progress
    │   │        Document workaround or stub implementation
    │   │        CONTINUE with next task
    │   │
    │   └─ NO → It's an implementation challenge
    │
    └─ Can you solve it within 30 minutes?
        ├─ YES → Solve it, document in Decision Log, CONTINUE
        ├─ NO  → Mark as NEEDS_RESEARCH in Progress
                 Document what's needed in "Blockers & Deferred Items"
                 SKIP to next task
                 Flag for human review
```

### Examples

**HARD Blocker - SKIP:**
```
Task: Run Meta API smoke tests
Blocker: No Meta credentials configured, sandbox blocks network access
Action:
  - [~] (BLOCKED: META_ACCESS_TOKEN not configured; network restricted in sandbox)
  - Document in Blockers section
  - Skip to next task: "Populate strategy_tag_mappings"
```

**SOFT Blocker - DEFER:**
```
Task: Implement Claude API client
Blocker: No ANTHROPIC_API_KEY in environment
Action:
  - [ ] (DEFERRED: Stub implementation created; real API calls require ANTHROPIC_API_KEY)
  - Create stub that returns mock responses
  - Document integration point for future completion
  - Continue with job emission wiring
```

**Implementation Challenge - RESEARCH:**
```
Task: Optimize database query performance
Blocker: Query takes 5 seconds, need caching strategy
Action:
  - [ ] (NEEDS_RESEARCH: Query slow; evaluate Redis cache vs SQL index vs materialized view)
  - Document problem and options in Decision Log
  - Skip to next task
  - Flag for architect review
```

### Recovery from Blockers

**When blocked items are unblocked:**
1. Search for `BLOCKED` or `DEFERRED` in Progress section
2. Re-attempt blocked task
3. If successful: Update status to `[x]` with timestamp
4. If still blocked: Document new findings, keep BLOCKED status

---

## Executive Summary

### Current State (Verified)
APEG is a **well-architected e-commerce automation system at ~65-70% completion**. The project demonstrates excellent engineering discipline with comprehensive documentation, rigorous testing, and phased execution methodology.

**Core Strengths:**
- ✅ Solid foundational infrastructure (Phases 1-3 nearly operational)
- ✅ Comprehensive specification (10,337 lines) and test evidence logging
- ✅ 52 unit tests passing with good coverage
- ✅ Async architecture properly designed with Redis distributed locking
- ✅ Recent development activity (active through Jan 1, 2026)

**Critical Gaps Identified:**
- ❌ **Data layer incomplete**: Empty strategy_tag_mappings and order_line_attributions tables
- ❌ **Phase 5 integration layer**: LLM client and job emission not implemented
- ❌ **Documentation redundancy**: ~300KB of duplicate research documents
- ❌ **Operational maturity**: No CI/CD, scheduler, or deployment automation
- ❌ **Phase 6 completely undefined**: No specification exists yet

**Overall Assessment:** Project has excellent technical foundations but needs **data activation** and **execution layer completion** to become fully operational.

---

## Progress - Current Work (Phases 1-5)

**Instructions:** Update this section with timestamps at EVERY stopping point. Mark completed items with `[x]`, blocked items with `[~]`, and deferred items appropriately.

### Phase 0 - Environment & Configuration (90% Complete)

- [x] (2026-01-01 00:00Z) Documentation baseline established (spec v1.4.1)
- [x] (2026-01-01 00:00Z) .env.example consolidated as canonical template
- [x] (2026-01-01 00:00Z) Environment parity enforcement mechanism added
- [ ] Run Shopify auth smoke test: `{ shop { name } }`
- [ ] Document n8n credential IDs (DEMO environment)
- [ ] Resolve .env vs .env.example discrepancies (extra keys: APEG_API_BASE_URL, etc.)

### Phase 1-2 - Shopify Bulk Operations (100% Complete)

- [x] (2025-12-29) Bulk query client implemented (bulk_client.py: 382 lines)
- [x] (2025-12-29) Bulk mutation client implemented (bulk_mutation_client.py: 401 lines)
- [x] (2025-12-30) Safe tag merge verified (integration test PASS)
- [x] (2025-12-30) Critical bug fixes (root GraphQL error handling, groupObjects removal)
- [x] (2026-01-01) Unit tests passing (mock-based tests for bulk clients)

### Phase 3 - n8n API Integration (95% Complete)

- [x] (2025-12-30) FastAPI endpoint created: POST /api/v1/jobs/seo-update
- [x] (2025-12-30) API key authentication implemented (X-APEG-API-KEY)
- [x] (2025-12-30) Background task dispatch working
- [x] (2026-01-01) TEST-N8N-01: Auth failure (401) - PASS
- [x] (2026-01-01) TEST-N8N-02: Dry run (202) - PASS
- [x] (2026-01-01) TEST-N8N-03: Live execution - PASS (bulk op gid://shopify/BulkOperation/4412960243814)
- [~] (BLOCKED: n8n unavailable in sandbox) TEST-N8N-04: Array typing test

### Phase 4 - Metrics Collection (75% Complete)

- [x] (2025-12-31) SQLite schema created (5 tables)
- [x] (2025-12-31) Meta Insights collector implemented (meta_collector.py: 254 lines)
- [x] (2025-12-31) Shopify Orders collector implemented (shopify_collector.py: 378 lines)
- [x] (2025-12-31) 3-tier attribution algorithm implemented (attribution.py: 249 lines)
- [x] (2025-12-31) Strategy tag catalog template created (18 tags)
- [x] (2026-01-01) TEST-COLLECTOR-01: Idempotency test - PASS
- [~] (BLOCKED: No ad spend data) TEST-META-01: Meta API smoke test
- [~] (BLOCKED: No orders in test range) TEST-SHOPIFY-01: Shopify attribution smoke test
- [ ] Populate strategy_tag_mappings table (Method B: name parsing)
- [ ] Backfill order_line_attributions (rerun collector with line items)
- [ ] Run collectors against production data (last 30 days)
- [ ] Implement scheduler (systemd timer or cron)

### Phase 5 - Feedback Loop (60% Complete)

- [x] (2025-12-31) Feedback database schema created (3 tables)
- [x] (2025-12-31) Analyzer module implemented (analyzer.py: 427 lines)
- [x] (2025-12-31) Version control module implemented (version_control.py: 218 lines)
- [x] (2025-12-31) Strategy tag mapping resolver (mapping.py: 157 lines)
- [x] (2025-12-31) LLM prompt builders (prompts.py: 126 lines)
- [x] (2026-01-01) Unit tests for diagnosis matrix - PASS
- [ ] Implement Claude API client (src/apeg_core/feedback/llm_client.py)
- [ ] Wire up Phase 3 job emission (POST to /api/v1/jobs/seo-update)
- [ ] Implement propose mode (Challenger generation workflow)
- [ ] Implement execute mode (approval → job emission)
- [ ] Test end-to-end feedback loop with real data

### Phase 6 - CI/CD & Hardening (0% Complete - Specification Needed)

- [ ] Create Phase 6 specification (docs/PHASE6_CICD_SPEC.md)
- [ ] Implement GitHub Actions workflow (.github/workflows/ci.yml)
- [ ] Implement license scanning (.github/workflows/license-scan.yml)
- [ ] Create deployment runbook (docs/DEPLOYMENT.md)
- [ ] Document troubleshooting procedures (docs/TROUBLESHOOTING.md)

### Documentation Cleanup

- [ ] Archive redundant research docs (docs/Research/Archive/)
- [ ] Create ADR directory structure (docs/adr/)
- [ ] Consolidate merger feasibility documents
- [ ] Update all completion percentages in documentation
- [ ] Create environment documentation (docs/ENVIRONMENTS.md)

---

## Surprises & Discoveries

**Instructions:** Document unexpected findings during execution. Include evidence and resolution.

### 2026-01-01 Discovery: Spec is Aspirational

- **Observation:** integration-architecture-spec-v1.4.1.md (10,337 lines) describes complete e-commerce automation vision, but only Sections 5, 7, 8 are implemented
- **Evidence:** Sections 2 (Canonical Product Model), 3 (EcomAgent Integration), 4 (Google Sheets Staging), 6 (Advertising Agent) have NO corresponding code files
- **Resolution:** Documented as "Future Phases" below; project is intentionally building data foundation first (smart strategy)
- **Impact:** Clarifies that ~65-70% completion is for Phases 1-5 scope, not full spec scope

### 2026-01-01 Discovery: Empty Data Tables

- **Observation:** strategy_tag_mappings and order_line_attributions tables are empty despite schema being defined
- **Evidence:** Phase 5 tests cannot run without populated data; mapping_enrichment.py exists (112 lines) but not executed
- **Resolution:** Added explicit tasks to populate tables using existing scripts
- **Impact:** Phase 5 blocked until data population complete

### 2026-01-01 Discovery: Environment Parity Drift

- **Observation:** .env contains extra keys not in .env.example (APEG_API_BASE_URL, DEMO_STORE_DOMAIN_ALLOWLIST, etc.)
- **Evidence:** TEST-ENV-01 initially FAILED (2026-01-01 05:58Z) with 17 missing keys, then PASSED (06:44Z) after manual sync
- **Resolution:** Documented discrepancies; needs reconciliation
- **Impact:** Environment setup documentation is inconsistent

---

## Decision Log

**Instructions:** Record every non-trivial decision with rationale. Future agents need context.

### 2026-01-01: Incremental Scope Strategy

- **Decision:** Focus execution on completing Phases 1-5, defer Phases 7+ (EcomAgent integration, etc.)
- **Rationale:** Project has intentionally built data/metrics foundation first before complex integrations. This is sound engineering.
- **Alternatives Considered:**
  - Try to implement full spec (rejected: too ambitious, violates incremental strategy)
  - Mark aspirational features as "missing" (rejected: they're deferred by design, not missing)
- **Impact:** Clear separation between current scope (~65-70% of Phases 1-5) and future work (remaining spec sections)

### 2026-01-01: Blocker Handling Strategy

- **Decision:** Implement "skip and document" strategy for blockers instead of halting all work
- **Rationale:** Many blockers (missing credentials, no test data) are environmental, not code issues. Autonomous agents should continue productive work while documenting blockers.
- **Alternatives Considered:**
  - Halt on any blocker (rejected: wastes agent time, blocks all progress)
  - Ignore blockers (rejected: unsafe, might cause data corruption or broken features)
- **Impact:** Enables autonomous execution with safe fallback for blocked items

### 2026-01-01: Documentation Modularization Strategy

- **Decision:** Structure project plan for later splitting into individual ExecPlans per phase
- **Rationale:** Current plan is comprehensive but will be too large for single-session execution. Agents will need focused ExecPlans for each phase.
- **Alternatives Considered:**
  - Create separate ExecPlans now (rejected: premature, need overview first)
  - Keep as single document forever (rejected: too unwieldy for execution)
- **Impact:** Plan will serve as blueprint for creating EXECPLAN-P4-metrics.md, EXECPLAN-P5-feedback.md, etc.

---

## Blockers & Deferred Items

**Instructions:** Track blocked tasks and reasons. Update when blockers are resolved.

### Hard Blockers (Require External Action)

| Task | Blocker | Required Action | Status | Notes |
|------|---------|-----------------|--------|-------|
| TEST-META-01 (Meta API smoke test) | No ad spend data in test date range | Run ads to generate data OR use production date range | BLOCKED | Collector works, just needs data |
| TEST-SHOPIFY-01 (Shopify attribution test) | No orders in test date range | Place test orders OR use production date range | BLOCKED | Collector works, just needs data |
| TEST-N8N-04 (Array typing test) | n8n instance unavailable in sandbox | Deploy n8n OR test in non-sandbox environment | BLOCKED | Not critical for Phase 3 completion |
| Claude API integration | No ANTHROPIC_API_KEY configured | Obtain API key and add to .env | BLOCKED | Phase 5 core blocker |

### Soft Blockers (Can Work Around)

| Task | Blocker | Workaround | Status | Notes |
|------|---------|------------|--------|-------|
| End-to-end feedback loop test | Empty data tables | Populate tables first, then test | IN_PROGRESS | Tables being populated |
| Production data collection | Requires scheduler | Manual execution acceptable for V1 | DEFERRED | Scheduler is Phase 6+ work |
| Job status tracking | No persistent queue | Fire-and-forget acceptable for V1 | DEFERRED | Enhancement, not blocker |

### Deferred to Future Phases

| Item | Reason for Deferral | Future Phase | Notes |
|------|---------------------|--------------|-------|
| Canonical Product Model | Not needed for metrics/feedback foundation | Phase 7 | Spec Section 2 |
| EcomAgent Integration | Requires asyncio.to_thread wrapper setup | Phase 8 | Spec Section 3 |
| Google Sheets Staging | Requires Google Apps Script, not core functionality | Phase 9 | Spec Section 4 |
| Advertising Agent | Requires Meta Business SDK integration | Phase 10 | Spec Section 6 |
| Etsy Integration | GPL licensing blocker (etsyv3 library) | Phase 11+ | Needs microservice isolation |
| Error recovery patterns | partialDataUrl handling not critical for V1 | Phase 6 | Phase 2 enhancement |
| Metrics dashboard UI | SQLite queries sufficient for V1 | Phase 12 | Nice-to-have |

---

## Spec Section Mapping (What's In Scope vs Future)

### Integration Architecture Spec v1.4.1 (10,337 lines)

| Spec Section | Description | Implementation Status | Current Scope? |
|--------------|-------------|----------------------|----------------|
| **Section 1** | System Overview | ✅ **Documented** - Architecture topology, decisions, constraints | Yes - Complete |
| **Section 2** | Canonical Product Model | ❌ **NOT IMPLEMENTED** - No canonical_product.py file exists | **🔮 FUTURE** |
| **Section 3** | APEG → EcomAgent Integration | ❌ **NOT IMPLEMENTED** - EcomAgent is separate repo, no integration code | **🔮 FUTURE** |
| **Section 4** | N8N Staging Layer (Google Sheets) | ❌ **NOT IMPLEMENTED** - No Google Sheets integration, no Apps Script | **🔮 FUTURE** |
| **Section 5** | Shopify GraphQL Bulk Operations | ✅ **COMPLETE** - bulk_client.py (382 lines), bulk_mutation_client.py (401 lines) | Yes - Phases 1-2 |
| **Section 6** | Advertising Agent Foundation | ❌ **NOT IMPLEMENTED** - No advertising_agent.py, no Meta campaign creation | **🔮 FUTURE** |
| **Section 7** | Metrics Collection & Storage | ✅ **75% COMPLETE** - Collectors implemented, smoke tests blocked on data | Yes - Phase 4 |
| **Section 8** | Feedback Loop Architecture | ⚠️ **60% COMPLETE** - Analysis engine done, LLM integration pending | Yes - Phase 5 |
| **Section 9** | Error Handling Matrix | ✅ **IMPLEMENTED** - Exception hierarchy in exceptions.py | Yes - Phases 1-2 |
| **Section 10** | Testing Strategy | ✅ **COMPLETE** - 52 tests, comprehensive coverage | Yes - All phases |
| **Appendix A** | Migration Checklist | ✅ **DOCUMENTED** - Migration strategy defined | Yes - Complete |
| **Appendix B** | File Structure Reference | ✅ **DOCUMENTED** - Project structure matches | Yes - Complete |
| **Appendix C** | Risk Register + V2 Roadmap | ✅ **DOCUMENTED** - Risks and future work identified | Yes - Complete |
| **Appendix D** | Machine-Readable Artifacts | ⚠️ **PARTIAL** - Some artifacts exist (graphql_strings.py) | Yes - Partial |
| **Appendix E** | Change Resolution Log | ✅ **DOCUMENTED** - CHANGELOG.md tracks changes | Yes - Complete |
| **Appendix F** | Demo → Live Swap Runbook | ✅ **DOCUMENTED** - Swap procedures defined | Yes - Phase 0 |

### Key Findings

1. **Current Scope (Phases 1-5):** Sections 5, 7, 8 + supporting sections
   - **Status:** ~65-70% complete
   - **Remaining:** Data population, Phase 5 LLM integration, Phase 6 CI/CD

2. **Future Scope (Beyond Phases 1-5):** Sections 2, 3, 4, 6
   - **EcomAgent Integration** (Section 3): Requires asyncio.to_thread wrapper, editable package install
   - **Canonical Product Model** (Section 2): Pydantic schema for cross-platform products
   - **Google Sheets Staging** (Section 4): Approval interface, Apps Script automation
   - **Advertising Agent** (Section 6): Meta Marketing API, campaign/ad creation

3. **Smart Incremental Strategy:**
   - Phase 1-5: Build data/metrics foundation ← **CURRENT FOCUS**
   - Phase 6+: Add complex integrations (EcomAgent, Advertising, Google Sheets) ← **FUTURE**

### Why This Matters

The spec is **aspirational documentation** describing the complete vision. The project has **intentionally implemented a subset** (Phases 1-5) to establish solid foundations before tackling complex integrations.

**This is NOT a problem** - it's good engineering practice. Build and test the core data pipeline before adding orchestration layers.

**Action Items:**
1. **Document spec scope clearly**: Update PROJECT_PLAN_ACTIVE.md to clarify which spec sections are in-scope for Phases 1-5
2. **Create "Phase 7+" spec**: Move Sections 2, 3, 4, 6 to future phases document
3. **Focus on completing Phases 1-5**: Don't get distracted by aspirational features

---

## Phase-by-Phase Status Verification

### PHASE 0 — Configuration & Cutover Readiness
**Claimed Status:** Active, 25% complete
**Verified Status:** ✅ **Mostly complete**, but inconsistent test evidence

**Completed Items:**
- [X] Documentation baseline corrections (spec v1.4.1, safety locks, env standardization)
- [X] .env.example consolidated as canonical template
- [X] Environment parity enforcement mechanism added to PROJECT_PLAN_ACTIVE.md
- [X] TEST-ENV-01 executed (multiple times with varying results)

**Issues Found:**
- **Inconsistent test evidence**: TEST-ENV-01 shows PASS on 2024-12-30, then FAIL on 2026-01-01 05:58Z (17 missing keys), then PASS again on 2026-01-01 06:44Z
- **Environment drift**: Evidence shows .env had only 13 keys initially, then expanded to 37 keys
- **Extra keys not in template**: APEG_API_BASE_URL, APEG_API_HOST, APEG_API_PORT, DEMO_STORE_DOMAIN_ALLOWLIST, META_APP_ID, TEST_PRODUCT_ID, TEST_TAG_PREFIX

**Remaining Work:**
- [ ] Shopify auth smoke test (graphQL: { shop { name } })
- [ ] Meta token debug (if Phase 4 planned soon)
- [ ] n8n credential ID documentation (DEMO environment)
- [ ] Resolve .env.example vs .env discrepancies (extra keys need documentation)

**Recommendation:** Mark Phase 0 as complete once smoke tests pass and .env discrepancies are documented.

---

### PHASE 1 — Deterministic Shopify Backbone
**Claimed Status:** Complete (verified Dec 29)
**Verified Status:** ✅ **COMPLETE**

**Evidence Verification:**
- [X] Bulk query → COMPLETED via node(id:) polling (Stage 2 verified)
- [X] Bulk mutation → COMPLETED via staged upload path
- [X] Upload hard-gate: non-2xx prevents runMutation
- [X] Tag merge preserves existing tags
- [X] Sequential lock enforcement (Redis)

**Test Coverage:**
- 4 unit test files for bulk client
- Integration test framework in place
- All acceptance tests marked as verified

**Issues:** None found. Phase 1 is production-ready.

---

### PHASE 2 — Shopify Muscle Layer (Safe Writes)
**Claimed Status:** Complete (verified Dec 30)
**Verified Status:** ⚠️ **90% COMPLETE** (error recovery patterns pending)

**Completed Items:**
- [X] Bulk Mutation Client implemented (401 lines)
- [X] Safe tag merge verified (integration test PASS 12/30)
- [X] Critical bug fix: Root GraphQL error handling (prevents KeyError crashes)
- [X] Critical schema fix: groupObjects completely removed from mutations
- [X] Integration test: verify_phase2_safe_writes.py PASS

**Remaining Work:**
- [ ] Error recovery patterns: partialDataUrl handling incomplete
- [ ] Audit logging for all writes (mentioned in spec but implementation unclear)

**Issues Found:**
- **partialDataUrl handling**: Mentioned in spec but not fully implemented
- **Rollback procedure**: Not tested according to ACCEPTANCE_TESTS.md

**Recommendation:** Complete error recovery patterns before marking fully done. Current state is production-usable but lacks complete failure handling.

---

### PHASE 3 — n8n Orchestration Bindings
**Claimed Status:** In progress (Part 2 nearly complete)
**Verified Status:** ✅ **95% COMPLETE** (Part 3 future enhancements remain)

**Part 1: FastAPI Backend — COMPLETE**
- [X] POST /api/v1/jobs/seo-update endpoint (routes.py: 246 lines)
- [X] API key authentication (X-APEG-API-KEY → 401 on invalid)
- [X] Background task dispatch
- [X] aiohttp timeout configuration (30s connect, 300s total)

**Part 2: n8n Integration — COMPLETE (with caveat)**
- [X] TEST-N8N-01: Auth failure (401) - PASS (12/30)
- [X] TEST-N8N-02: Dry run (202) - PASS (12/30)
- [X] TEST-N8N-03: Live execution - PASS (01/01, bulk op gid://shopify/BulkOperation/4412960243814)
- [X] Environment parity enforcement (TEST-ENV-01 PASS)
- [X] N8N_WORKFLOW_CONFIG.md created

**Part 2: Incomplete/Blocked**
- [ ] TEST-N8N-04: Array typing test - BLOCKED (n8n unavailable in sandbox, 01/01 08:42Z)
- [ ] TEST-INTEGRATION-02: Phase 2 tests with consolidated template - SKIPPED (config mismatch)

**Part 3: Future Enhancements (Backlog)**
- [ ] Job status callback endpoint (webhook for completion)
- [ ] Persistent job queue (Celery/RQ)
- [ ] GET /api/v1/jobs/{job_id} status query endpoint

**Issues Found:**
- **Background tasks are fire-and-forget**: No persistence, lost on server restart
- **No job status tracking**: Cannot query job completion status
- **TEST-N8N-04 blocked**: Sandbox limitation prevents full array typing verification

**Recommendation:** Mark Phase 3 core as complete. Part 3 enhancements are architectural improvements, not blockers.

---

### PHASE 4 — Data Collection & Metrics Intelligence
**Claimed Status:** Core complete, validation blocked
**Verified Status:** ⚠️ **75% COMPLETE** (core infrastructure done, validation and automation pending)

**Part 1: Core Infrastructure — COMPLETE**
- [X] SQLite schema (5 tables: metrics_meta_daily, order_attributions, collector_state, etc.)
- [X] Attribution logic (3-tier waterfall algorithm in attribution.py: 249 lines)
- [X] Meta Insights collector (meta_collector.py: 254 lines)
- [X] Shopify Orders collector (shopify_collector.py: 378 lines)
- [X] Orchestrator service (collector.py: 274 lines)
- [X] Strategy tag catalog template (18 tags in strategy_tags.json)
- [X] CLI entry point (run_metrics_collector.py)

**Part 2: Validation & Testing — BLOCKED ON DATA**
- [X] TEST-COLLECTOR-01: SQLite idempotency - VERIFIED (01/01, re-run shows no duplicates)
- [ ] TEST-META-01: Meta API smoke test - SKIPPED (no ad spend data for test date)
- [ ] TEST-SHOPIFY-01: Shopify attribution smoke test - SKIPPED (no orders in test date range)
- [ ] TEST-COLLECTOR-02: End-to-end collection test - PARTIAL (no Meta data)

**Part 3: Production Deployment — NOT STARTED**
- [ ] Scheduler implementation (cron/systemd timer)
- [ ] Meta ad account timezone API retrieval (currently hardcoded fallback)
- [ ] Webhook notifications on collection completion
- [ ] Metrics dashboard (query SQLite for insights)

**Critical Data Issue:**
The database exists and schema is correct, but smoke tests cannot run without:
1. Active Meta ad campaigns with spend data
2. Shopify orders in test date range
3. This is a **test data availability issue**, not an implementation issue

**Recommendation:**
1. Run collector against production date range to populate real data
2. Re-run smoke tests once data exists
3. Implement scheduler for daily automation
4. Mark as complete once smoke tests pass

---

### PHASE 5 — Feedback Loop & Refinement Engine
**Claimed Status:** Core analysis complete, LLM integration pending
**Verified Status:** ⚠️ **60% COMPLETE** (analysis engine done, execution layer blocked)

**Part 1: Core Analysis & Decision Engine — COMPLETE**
- [X] Feedback database schema (seo_versions, feedback_runs, feedback_actions)
- [X] Product-level attribution schema (order_line_attributions table)
- [X] Strategy tag mapping resolver (mapping.py: 157 lines with 3 methods)
- [X] Analyzer module (analyzer.py: 427 lines with diagnosis matrix)
- [X] Version control module (version_control.py: 218 lines)
- [X] LLM prompt builders (prompts.py: 126 lines)
- [X] CLI entry point (run_feedback_loop.py: analysis mode functional)
- [X] Unit tests (diagnosis matrix validated)

**Part 2: LLM Integration & Job Emission — BLOCKED**
- [ ] Claude API integration for Challenger generation (requires ANTHROPIC_API_KEY)
- [ ] Phase 3 job emission implementation (POST to /api/v1/jobs/seo-update)
- [ ] Propose mode implementation (load candidates → generate Challengers → create proposals)
- [ ] Execute mode implementation (approve → emit jobs → track job_id)

**Part 3: Data Dependencies — BLOCKED ON BACKFILL**
- [ ] Populate strategy_tag_mappings table
  - Method A: Track APEG ad creation (future)
  - **Method B: Parse existing campaign/ad names** ← Implementation exists (mapping_enrichment.py: 112 lines) but not automated
  - Method C: Fetch utm_campaign from ad URLs (stub)
- [ ] Backfill order_line_attributions (requires Phase 4 collector rerun with updated GraphQL query)

**Part 4: Evaluation Engine — NOT STARTED**
- [ ] Outcome evaluation (compare pre/post windows)
- [ ] Winner promotion (supersede Champion with Challenger)
- [ ] Auto-rollback on LOSS outcome
- [ ] Budget automation

**Critical Issues:**
1. **Empty tables blocking execution**: strategy_tag_mappings and order_line_attributions are unpopulated
2. **LLM integration stub**: Prompt builders exist but no Claude API client implementation
3. **Job emission stub**: Structure ready but HTTP POST to Phase 3 API not wired up

**Recommendation:**
1. **Priority 1**: Populate strategy_tag_mappings using Method B parser (mapping_enrichment.py exists)
2. **Priority 2**: Backfill order_line_attributions (rerun Phase 4 collector)
3. **Priority 3**: Implement Claude API client
4. **Priority 4**: Wire up job emission to Phase 3 API

---

### PHASE 6 — Hardening + CI/CD
**Claimed Status:** Not started
**Verified Status:** ❌ **0% COMPLETE** (completely undefined)

**No Specification Exists:**
- [ ] CI workflows (GitHub Actions)
- [ ] Coverage gates
- [ ] GPL denylist enforcement (pip-licenses)
- [ ] Deployment automation
- [ ] Monitoring setup
- [ ] Rollback procedures

**Recommendation:** Create Phase 6 specification before starting implementation.

---

## Completed Work Inventory

### ✅ Infrastructure (Production-Ready)
1. **Async architecture**: FastAPI + aiohttp with proper async/await patterns
2. **Shopify Bulk Client**: Full CRUD with Redis distributed locking (928 lines)
3. **API Layer**: Authentication, background tasks, exception safety (246 lines)
4. **Metrics Collection**: 3-tier attribution, idempotent daily ingestion (1,496 lines)
5. **Feedback Analysis**: Diagnosis matrix, version control, strategy mapping (1,029 lines)

### ✅ Testing (52 tests, well-covered)
1. **Unit tests**: 8 files with comprehensive mocking
2. **Integration tests**: 1 file (verify_phase2_safe_writes.py)
3. **Smoke tests**: 2 files (Meta API, Shopify attribution)
4. **Test evidence logging**: 946-line ACCEPTANCE_TESTS.md

### ✅ Documentation (12,926+ lines)
1. **Master specification**: integration-architecture-spec-v1.4.1.md (10,337 lines)
2. **Project plan**: PROJECT_PLAN_ACTIVE.md (309 lines)
3. **Test evidence**: ACCEPTANCE_TESTS.md (946 lines)
4. **Changelog**: CHANGELOG.md (detailed implementation log)
5. **Agent context**: AGENTS.md (275 lines), PLANS.md
6. **API docs**: API_USAGE.md, N8N_WORKFLOW_CONFIG.md, ENVIRONMENT.md

### ✅ Configuration
1. **.env.example**: Comprehensive 30-key template
2. **Strategy tag catalog**: 18 tags defined in strategy_tags.json
3. **Safety gates**: APEG_ENV, APEG_ALLOW_WRITES, store allowlists

---

## Remaining Work Breakdown (Prioritized)

### 🔴 CRITICAL BLOCKERS (Must complete for system operation)

#### 1. Data Population (Phase 5 blocker)
**Estimated Effort:** 4-6 hours

- [ ] **Populate strategy_tag_mappings** (P0)
  - Run mapping_enrichment.py script against existing Meta campaigns
  - Method B (name parsing) implementation exists, needs execution
  - Verify confidence scores and metadata
  - **Files:** [src/apeg_core/feedback/mapping_enrichment.py](src/apeg_core/feedback/mapping_enrichment.py)

- [ ] **Backfill order_line_attributions** (P0)
  - Update Shopify GraphQL query to capture line items
  - Rerun Phase 4 collector for historical date range
  - Verify product-level ROAS computation
  - **Files:** [src/apeg_core/metrics/shopify_collector.py](src/apeg_core/metrics/shopify_collector.py)

#### 2. Phase 5 Execution Layer (Integration work)
**Estimated Effort:** 8-12 hours

- [ ] **Claude API Integration** (P0)
  - Implement async Claude client (use anthropic SDK)
  - Wire up prompt builders to API calls
  - Add output validation and retry logic
  - **Files:** New file: [src/apeg_core/feedback/llm_client.py](src/apeg_core/feedback/llm_client.py)

- [ ] **Phase 3 Job Emission** (P0)
  - POST to /api/v1/jobs/seo-update from feedback loop
  - Track phase3_job_id in seo_versions table
  - Implement rollback job emission
  - **Files:** [src/apeg_core/feedback/analyzer.py](src/apeg_core/feedback/analyzer.py), [scripts/run_feedback_loop.py](scripts/run_feedback_loop.py)

- [ ] **Propose/Execute Modes** (P1)
  - Implement propose mode (Challenger generation workflow)
  - Implement execute mode (approval → job emission)
  - Add approval workflow mechanism
  - **Files:** [scripts/run_feedback_loop.py](scripts/run_feedback_loop.py)

### 🟡 HIGH PRIORITY (Production readiness)

#### 3. Phase 4 Validation & Automation
**Estimated Effort:** 6-8 hours

- [ ] **Run collectors against production data**
  - Execute for last 30 days to populate metrics
  - Verify Meta and Shopify data collection
  - Run smoke tests (TEST-META-01, TEST-SHOPIFY-01)

- [ ] **Implement scheduler**
  - Create systemd timer or cron job
  - Daily collection at configured time (METRICS_COLLECTION_TIME)
  - Error notification mechanism
  - **Files:** New: [infra/systemd/apeg-metrics-collector.service](infra/systemd/apeg-metrics-collector.service), [infra/systemd/apeg-metrics-collector.timer](infra/systemd/apeg-metrics-collector.timer)

- [ ] **Meta timezone API retrieval**
  - Replace hardcoded timezone fallback
  - Fetch from Meta ad account settings
  - **Files:** [src/apeg_core/metrics/meta_collector.py](src/apeg_core/metrics/meta_collector.py)

#### 4. Phase 2/3 Completion
**Estimated Effort:** 4-6 hours

- [ ] **Error recovery patterns** (Phase 2)
  - Implement partialDataUrl handling
  - Test bulk operation partial failures
  - Document recovery procedures
  - **Files:** [src/apeg_core/shopify/bulk_client.py](src/apeg_core/shopify/bulk_client.py), [src/apeg_core/shopify/bulk_mutation_client.py](src/apeg_core/shopify/bulk_mutation_client.py)

- [ ] **Job status tracking** (Phase 3)
  - Implement GET /api/v1/jobs/{job_id} endpoint
  - Add job status persistence (SQLite or Redis)
  - Return job progress/completion status
  - **Files:** [src/apeg_core/api/routes.py](src/apeg_core/api/routes.py), new schema in [src/apeg_core/schemas/](src/apeg_core/schemas/)

- [ ] **Persistent queue** (Phase 3)
  - Evaluate Celery vs RQ vs custom SQLite queue
  - Implement job persistence and recovery
  - Ensure jobs survive server restarts
  - **Files:** New module: [src/apeg_core/queue/](src/apeg_core/queue/)

### 🟢 MEDIUM PRIORITY (Quality of life)

#### 5. Phase 6 Specification & Implementation
**Estimated Effort:** 12-16 hours

- [ ] **Create Phase 6 specification**
  - Define CI/CD requirements
  - Specify coverage gates and metrics
  - Document deployment procedures
  - **Files:** New: [docs/PHASE6_CICD_SPEC.md](docs/PHASE6_CICD_SPEC.md)

- [ ] **Implement CI workflows**
  - GitHub Actions workflow for tests
  - License scanning (pip-licenses)
  - Coverage reporting
  - **Files:** New: [.github/workflows/ci.yml](.github/workflows/ci.yml), [.github/workflows/license-scan.yml](.github/workflows/license-scan.yml)

- [ ] **Deployment automation**
  - Create deployment scripts
  - Document server setup
  - Implement blue-green or rolling deployment
  - **Files:** New: [infra/deploy/](infra/deploy/)

#### 6. Phase 5 Evaluation Engine
**Estimated Effort:** 8-10 hours

- [ ] **Outcome evaluation**
  - Implement pre/post window comparison
  - Calculate Winner/Loser/Inconclusive outcomes
  - Update seo_versions with results
  - **Files:** New: [src/apeg_core/feedback/evaluator.py](src/apeg_core/feedback/evaluator.py)

- [ ] **Auto-rollback on LOSS**
  - Trigger rollback when Challenger underperforms
  - Emit Phase 3 job to restore Champion
  - Record rollback in audit trail
  - **Files:** [src/apeg_core/feedback/version_control.py](src/apeg_core/feedback/version_control.py)

---

## Missed/Undocumented Steps

### Steps Present in Code but Not in PROJECT_PLAN_ACTIVE.md

1. **mapping_enrichment.py implementation** (Phase 5)
   - File exists: [src/apeg_core/feedback/mapping_enrichment.py](src/apeg_core/feedback/mapping_enrichment.py) (112 lines)
   - Parses campaign/ad names to extract strategy tags
   - **Not mentioned in PROJECT_PLAN_ACTIVE.md Part 3**
   - **Action:** Document in plan, execute to populate strategy_tag_mappings

2. **Unit tests for ShopifyBulkClient**
   - File exists: [tests/unit/test_bulk_client_mock.py](tests/unit/test_bulk_client_mock.py)
   - Git commit shows "Add unit tests for ShopifyBulkClient with mocked API interactions"
   - **Not tracked in ACCEPTANCE_TESTS.md**
   - **Action:** Add TEST-BULK-05 through TEST-BULK-10 for new mock tests

3. **seed_dummy_data.py script**
   - File exists: [scripts/seed_dummy_data.py](scripts/seed_dummy_data.py) (3,261 lines!)
   - Not mentioned in any phase plan
   - Appears to generate test data for metrics and attributions
   - **Action:** Document purpose and usage in PHASE4_TESTING.md

### Steps Mentioned in Spec but Not Implemented

1. **Etsy microservice isolation** (GPL licensing workaround)
   - Mentioned in CHANGELOG.md as blocking issue
   - No design specification exists
   - No timeline documented
   - **Action:** Create ETSY_INTEGRATION_PLAN.md or defer indefinitely

2. **Webhook HMAC verification** (mentioned in ACCEPTANCE_TESTS.md)
   - Listed in LIVE SWAP checklist as REQUIRED
   - No implementation found in codebase
   - **Action:** Clarify if this is n8n webhooks or Shopify webhooks

3. **Audit logging for all writes** (Phase 2)
   - Mentioned in PROJECT_PLAN_ACTIVE.md as deliverable
   - Partial logging exists (run_id, bulk_op_id in logs)
   - No structured audit trail table in SQLite
   - **Action:** Create audit_log table or clarify that JSONL + logs are sufficient

4. **Metrics dashboard** (Phase 4 Part 3)
   - Listed as future enhancement
   - No specification or UI framework chosen
   - **Action:** Defer to post-Phase 6 or create spec

### Environmental Discrepancies

1. **.env has extra keys not in .env.example**
   - APEG_API_BASE_URL, APEG_API_HOST, APEG_API_PORT
   - DEMO_STORE_DOMAIN_ALLOWLIST
   - META_APP_ID
   - TEST_PRODUCT_ID, TEST_TAG_PREFIX
   - **Action:** Document these in .env.example or remove from .env

2. **Multiple environment files mentioned**
   - .env.integration referenced in tests but deprecated
   - Evidence shows both .env and .env.integration usage
   - **Action:** Clarify single .env.example → .env workflow

---

## Documentation Issues & Improvements

### Redundancy (Identified Issues)

1. **Multiple merger feasibility documents** (~300KB total)
   - [docs/Research/APEG EcomAgent Merger Feasibility Report.md](docs/Research/APEG%20EcomAgent%20Merger%20Feasibility%20Report.md)
   - [docs/Research/Merging EcomAgent and PEG Systems.txt](docs/Research/Merging%20EcomAgent%20and%20PEG%20Systems.txt)
   - [docs/Research/Master-BuildPlan.md](docs/Research/Master-BuildPlan.md)
   - **Action:** Archive to docs/Research/Archive/, keep only Master-BuildPlan.md

2. **Duplicate project planning research**
   - [docs/Research/NEW Updated Project Plan Research.md](docs/Research/NEW%20Updated%20Project%20Plan%20Research.md)
   - Overlaps with PROJECT_PLAN_ACTIVE.md
   - **Action:** Archive or merge relevant content into PROJECT_PLAN_ACTIVE.md

3. **Long-form research documents**
   - [docs/Research/Online Jewelry Business Research.md](docs/Research/Online%20Jewelry%20Business%20Research.md) (47KB)
   - Valuable domain knowledge but not technical reference
   - **Action:** Move to docs/Business/ directory

### Missing Documentation

1. **No Architectural Decision Records (ADR)**
   - Decisions scattered across CHANGELOG.md and research docs
   - No standardized ADR format
   - **Action:** Create docs/adr/ directory with template

2. **No deployment runbook**
   - Server setup not documented
   - Monitoring configuration missing
   - Rollback procedures undefined
   - **Action:** Create docs/DEPLOYMENT.md

3. **No Phase 6 specification**
   - CI/CD completely undefined
   - No requirements or acceptance criteria
   - **Action:** Create docs/PHASE6_CICD_SPEC.md

4. **No troubleshooting guide**
   - Common errors not documented
   - Redis connection issues, Shopify API errors, etc.
   - **Action:** Create docs/TROUBLESHOOTING.md

### Ambiguities (Need Clarification)

1. **Phase completion percentages inconsistent**
   - README claims ~75% complete
   - Detailed analysis shows 65-70%
   - Different phases have conflicting status
   - **Action:** Update all documentation with verified percentages

2. **Test evidence timestamps in future**
   - ACCEPTANCE_TESTS.md shows dates like 2026-01-01
   - Git log also shows 2026-01-01 commits
   - **Clarification needed:** Is system clock correct? Or typo in dates?

3. **Sandbox vs production environments**
   - Some tests show "sandbox credentials unset"
   - Others show "DEMO credentials"
   - Relationship between DEMO/LIVE and sandbox unclear
   - **Action:** Create docs/ENVIRONMENTS.md to clarify

4. **Background task persistence**
   - Phase 3 notes tasks are fire-and-forget
   - Part 3 says "future: persistent queue"
   - Unclear if this is blocking or enhancement
   - **Action:** Clarify in PROJECT_PLAN_ACTIVE.md

---

## How to Prevent This in the Future

### Documentation Governance (Proposed)

#### 1. Single Source of Truth Hierarchy
```
docs/
├── integration-architecture-spec-v1.x.md  ← Technical law (what)
├── PROJECT_PLAN_ACTIVE.md                  ← Execution status (when)
├── ACCEPTANCE_TESTS.md                     ← Test evidence (proof)
└── CHANGELOG.md                            ← Implementation log (how)
```

**Rule:** If conflict exists, hierarchy wins (spec > plan > tests > changelog)

#### 2. Research Document Lifecycle
```
docs/Research/
├── Active/           ← Current investigation (max 5 docs)
├── Archive/          ← Completed research (readonly)
└── Decisions/        ← ADRs (architectural decision records)
```

**Rule:** Archive research doc when decision made; create ADR to capture outcome

#### 3. Mandatory Phase Gate Checklist
Before marking any phase complete:
- [ ] All acceptance tests executed with PASS evidence
- [ ] CHANGELOG.md updated with implementation summary
- [ ] PROJECT_PLAN_ACTIVE.md updated with completion timestamp
- [ ] All TODO comments in code resolved or moved to backlog
- [ ] Documentation reviewed for ambiguities

#### 4. Weekly Status Reconciliation
**Process:** Every Friday (or weekly interval)
1. Compare PROJECT_PLAN_ACTIVE.md % complete with actual test evidence
2. Update all completion percentages based on ACCEPTANCE_TESTS.md
3. Archive any research documents that led to decisions
4. Update .env.example if new variables added to .env
5. Git commit: "chore: Weekly status reconciliation [DATE]"

#### 5. ExecPlan Protocol (Already exists in PLANS.md)
**Enforcement:** For any feature >4 hours:
1. Create ExecPlan following .agent/PLANS.md template
2. Update ExecPlan progress section after each implementation step
3. Link ExecPlan to PROJECT_PLAN_ACTIVE.md phase item
4. Archive ExecPlan to docs/Archive/ExecPlans/ when complete

#### 6. Test Evidence Requirements
**Rule:** No phase item can be marked "Done" without:
1. Test execution command documented
2. Expected output documented
3. Actual output pasted with timestamp
4. PASS/FAIL status with date
5. Evidence source (file path, line number, or command)

#### 7. Environment Parity Enforcement (Already in place)
**Enhancement:** Add automated check
```bash
# .github/workflows/env-parity-check.yml
- name: Verify .env parity
  run: |
    python scripts/verify_env_parity.py
    # Fails if .env has keys not in .env.example
```

---

## Recommended Documentation Structure

### Proposed Directory Reorganization
```
docs/
├── integration-architecture-spec-v1.4.1.md  # Master spec (keep)
├── PROJECT_PLAN_ACTIVE.md                    # Execution tracker (keep)
├── ACCEPTANCE_TESTS.md                       # Test evidence (keep)
├── CHANGELOG.md                              # Implementation log (keep)
│
├── guides/                                   # NEW: User-facing guides
│   ├── DEPLOYMENT.md
│   ├── TROUBLESHOOTING.md
│   ├── ENVIRONMENTS.md
│   └── API_USAGE.md (move from root)
│
├── specs/                                    # NEW: Feature specifications
│   ├── PHASE4_METRICS_SPEC.md
│   ├── PHASE5_FEEDBACK_SPEC.md
│   ├── PHASE6_CICD_SPEC.md
│   └── ETSY_INTEGRATION_PLAN.md
│
├── adr/                                      # NEW: Architectural decisions
│   ├── 001-async-architecture.md
│   ├── 002-graphql-bulk-operations.md
│   ├── 003-redis-distributed-locks.md
│   └── template.md
│
├── business/                                 # NEW: Business context
│   └── Online Jewelry Business Research.md (move from Research/)
│
└── Research/
    ├── Active/                               # Current investigations
    ├── Archive/                              # Completed research
    │   ├── APEG EcomAgent Merger Feasibility Report.md
    │   ├── Merging EcomAgent and PEG Systems.txt
    │   └── NEW Updated Project Plan Research.md
    └── Master-BuildPlan.md                   # Keep as architectural convergence reference
```

### New Document Templates

#### ADR Template (docs/adr/template.md)
```markdown
# ADR-XXX: [Title]

**Status:** Proposed | Accepted | Deprecated
**Date:** YYYY-MM-DD
**Deciders:** [Names]

## Context
[What is the issue we're facing?]

## Decision
[What decision did we make?]

## Consequences
### Positive
- [Benefit 1]

### Negative
- [Drawback 1]

## Alternatives Considered
1. [Alternative 1] - Rejected because...

## References
- [Link to spec section]
- [Link to research doc]
```

---

## Ambiguities & Corrections Needed

### Critical Ambiguities Requiring User Clarification

1. **Date/Time Accuracy**
   - Git log shows commits on 2026-01-01
   - Test evidence timestamps show 2026-01-01
   - **Question:** Is this correct or is system clock set wrong?

2. **Environment Strategy**
   - DEMO vs LIVE in .env.example
   - "Sandbox credentials" in test output
   - Relationship unclear
   - **Question:** Is "sandbox" = DEMO? Or a third environment?

3. **Phase 3 Persistent Queue**
   - Listed as "Part 3: Future Enhancements"
   - But background tasks lost on restart is a significant limitation
   - **Question:** Is this a Phase 3 blocker or Phase 6+ enhancement?

4. **strategy_tag_mappings Population**
   - mapping_enrichment.py exists and appears functional
   - Not mentioned in PROJECT_PLAN_ACTIVE.md
   - **Question:** Should this be run manually now? Or automated later?

5. **Audit Logging Scope**
   - Phase 2 deliverable: "Audit logging for all writes"
   - Logging exists (run_id, bulk_op_id in application logs)
   - No structured audit table in SQLite
   - **Question:** Are logs sufficient or need database table?

6. **Etsy Integration Timeline**
   - GPL licensing blocker acknowledged
   - No microservice design spec
   - No timeline
   - **Question:** Is Etsy integration indefinitely deferred?

### Corrections to Make

1. **Update Phase Completion Percentages**
   - Phase 0: 25% → **90%** (only smoke tests remain)
   - Phase 3: "In Progress" → **95% Complete**
   - Phase 4: "Core Complete" → **75% Complete**
   - Phase 5: "In Progress" → **60% Complete**
   - **Overall: 65-70% complete** (not 75%)

2. **Reconcile .env.example with .env**
   - Add missing keys to .env.example:
     - APEG_API_BASE_URL (network config)
     - APEG_API_HOST, APEG_API_PORT
     - DEMO_STORE_DOMAIN_ALLOWLIST
     - META_APP_ID
   - Or document why these are local-only

3. **Document seed_dummy_data.py**
   - 3,261 lines of code
   - Not mentioned anywhere
   - **Action:** Add usage section to README or TESTING.md

4. **Clarify TEST-ENV-01 Evidence**
   - Multiple runs with different results
   - Latest shows PASS (2026-01-01 08:39Z)
   - **Action:** Keep only latest evidence, archive old runs

---

## Recommended Immediate Actions

### Week 1: Data Activation (Unblock Phase 5)
**Goal:** Populate empty tables and validate with real data

1. **Run mapping enrichment** (Day 1-2)
   - Execute mapping_enrichment.py against Meta campaigns
   - Verify strategy_tag_mappings populated
   - Record evidence in ACCEPTANCE_TESTS.md

2. **Backfill order line attributions** (Day 2-3)
   - Update Shopify collector GraphQL query
   - Rerun for last 30 days
   - Verify order_line_attributions populated

3. **Run Phase 4 collectors against production** (Day 3-4)
   - Execute for last 30 days to get real data
   - Re-run smoke tests (TEST-META-01, TEST-SHOPIFY-01)
   - Mark Phase 4 as complete if tests pass

4. **Document findings** (Day 5)
   - Update PROJECT_PLAN_ACTIVE.md with actual data insights
   - Record any data quality issues discovered
   - Update completion percentages

### Week 2: Phase 5 Integration (Complete Feedback Loop)
**Goal:** Wire up LLM and job emission to make feedback loop functional

1. **Implement Claude API client** (Day 6-7)
   - Create src/apeg_core/feedback/llm_client.py
   - Async client with retry logic
   - Output validation

2. **Wire up job emission** (Day 8-9)
   - POST to Phase 3 API from analyzer
   - Track job_id in seo_versions
   - Implement rollback emission

3. **Implement propose/execute modes** (Day 10)
   - Complete propose mode (Challenger generation)
   - Complete execute mode (job emission)
   - Test end-to-end feedback loop

4. **Test and document** (Day 11-12)
   - Run full feedback loop with real data
   - Document results
   - Mark Phase 5 core as complete

### Week 3: Production Readiness (Phase 4 + 6)
**Goal:** Automation and deployment preparation

1. **Implement scheduler** (Day 13-14)
   - Systemd timer for daily metrics collection
   - Error notification mechanism
   - Test automated collection

2. **Create Phase 6 specification** (Day 15-16)
   - Define CI/CD requirements
   - Document deployment procedures
   - Create acceptance tests

3. **Implement basic CI** (Day 17-18)
   - GitHub Actions workflow
   - License scanning
   - Test execution on PR

4. **Documentation cleanup** (Day 19-21)
   - Archive redundant research docs
   - Create ADR directory structure
   - Write deployment runbook
   - Update all completion percentages

---

## Success Criteria

### Definition of "Complete" for Each Phase

**Phase 0:** Environment configured
- [ ] Shopify auth smoke test PASS
- [ ] .env.example parity verified
- [ ] No extra keys in .env without documentation

**Phase 1-2:** Already complete ✅

**Phase 3:** API operational
- [ ] All TEST-N8N tests PASS (or documented why TEST-N8N-04 is not blocking)
- [ ] Job status tracking implemented OR explicitly deferred
- [ ] Persistent queue implemented OR documented as Phase 6 work

**Phase 4:** Metrics flowing
- [ ] Daily collection automated (scheduler running)
- [ ] All smoke tests PASS with real data
- [ ] At least 30 days of historical data collected

**Phase 5:** Feedback loop operational
- [ ] strategy_tag_mappings and order_line_attributions populated
- [ ] LLM integration functional (Challenger generation working)
- [ ] Job emission working (at least 1 successful end-to-end test)
- [ ] All TEST-FEEDBACK tests PASS

**Phase 6:** Production hardened
- [ ] CI workflow running on all PRs
- [ ] Deployment runbook tested
- [ ] GPL license scan passing
- [ ] Monitoring operational

### Overall Project "Done" Criteria

1. **All 6 phases marked complete** in PROJECT_PLAN_ACTIVE.md
2. **All acceptance tests PASS** in ACCEPTANCE_TESTS.md
3. **System running in production** with real data for 7+ days
4. **Zero critical bugs** in issue tracker
5. **Documentation complete**:
   - Deployment runbook exists and tested
   - Troubleshooting guide covers common errors
   - All architectural decisions documented
6. **Handoff possible**: Another developer can deploy and operate system using docs alone

---

## Files Requiring Attention

### Critical (Blocking Progress)
- [ ] [src/apeg_core/feedback/llm_client.py](src/apeg_core/feedback/llm_client.py) — **CREATE** (LLM integration)
- [ ] [scripts/run_feedback_loop.py](scripts/run_feedback_loop.py) — **MODIFY** (wire up propose/execute)
- [ ] [src/apeg_core/metrics/shopify_collector.py](src/apeg_core/metrics/shopify_collector.py) — **MODIFY** (add line items to query)
- [ ] [.env.example](.env.example) — **MODIFY** (add missing keys or document discrepancies)

### High Priority (Production Readiness)
- [ ] [infra/systemd/apeg-metrics-collector.service](infra/systemd/apeg-metrics-collector.service) — **CREATE** (scheduler)
- [ ] [infra/systemd/apeg-metrics-collector.timer](infra/systemd/apeg-metrics-collector.timer) — **CREATE** (scheduler)
- [ ] [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — **CREATE** (deployment runbook)
- [ ] [docs/PHASE6_CICD_SPEC.md](docs/PHASE6_CICD_SPEC.md) — **CREATE** (CI/CD specification)
- [ ] [.github/workflows/ci.yml](.github/workflows/ci.yml) — **CREATE** (CI workflow)

### Medium Priority (Quality Improvements)
- [ ] [docs/adr/template.md](docs/adr/template.md) — **CREATE** (ADR structure)
- [ ] [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — **CREATE** (common errors)
- [ ] [docs/ENVIRONMENTS.md](docs/ENVIRONMENTS.md) — **CREATE** (clarify DEMO/LIVE/sandbox)
- [ ] [src/apeg_core/api/routes.py](src/apeg_core/api/routes.py) — **MODIFY** (add job status endpoint)
- [ ] [docs/PROJECT_PLAN_ACTIVE.md](docs/PROJECT_PLAN_ACTIVE.md) — **UPDATE** (correct completion %)

### Low Priority (Nice to Have)
- [ ] [src/apeg_core/shopify/bulk_client.py](src/apeg_core/shopify/bulk_client.py) — **MODIFY** (partialDataUrl handling)
- [ ] [docs/Research/Archive/](docs/Research/Archive/) — **CREATE** (archive redundant docs)
- [ ] [scripts/verify_env_parity.py](scripts/verify_env_parity.py) — **CREATE** (automated env check)

---

## Critical Discovery: Spec vs Implementation Scope

### The Specification is Aspirational
The **integration-architecture-spec-v1.4.1.md** (10,337 lines) describes the **complete vision** of a full e-commerce automation system including:

**ASPIRATIONAL (Not Yet Implemented):**
- **Section 2:** Canonical Product Model - unified data model across platforms (NOT IN CODEBASE)
- **Section 3:** APEG → EcomAgent Integration - SEO agent integration via asyncio.to_thread (NOT INTEGRATED - EcomAgent is separate repo)
- **Section 4:** N8N Staging Layer - Google Sheets approval interface with Apps Script (NOT IMPLEMENTED)
- **Section 6:** Advertising Agent Foundation - Meta Marketing API ad campaign creation (NOT IMPLEMENTED)

**IMPLEMENTED (Current Focus - Phases 1-5):**
- **Section 5:** Shopify GraphQL Bulk Operations → **Phases 1-2 COMPLETE**
- **Section 7:** Metrics Collection & Storage → **Phase 4 (75% complete)**
- **Section 8:** Feedback Loop Architecture → **Phase 5 (60% complete - analysis done, LLM integration pending)**

### Project Strategy: Incremental Build-Out

The project is **intentionally building the data/metrics foundation first** (Phases 1-5) before tackling:
1. EcomAgent/Advertising Agent integration
2. Google Sheets staging layer
3. Full e-commerce automation loop

**This is the RIGHT approach** - establish solid data infrastructure before adding complex integrations.

### Current State: Phase 1-5 Implementation

**What EXISTS (Implemented):**
- ✅ Shopify Bulk Operations with Redis locking (Phases 1-2)
- ✅ FastAPI API layer with n8n integration (Phase 3)
- ✅ Metrics collection from Meta/Shopify (Phase 4)
- ✅ Feedback loop analysis engine with diagnosis matrix (Phase 5)
- ✅ 52 passing tests with comprehensive coverage
- ✅ Excellent async architecture

**What's MISSING (To Complete Phases 1-5):**
- ❌ Data population (empty strategy_tag_mappings and order_line_attributions tables)
- ❌ Phase 5 LLM integration (prompt builders exist, Claude API client not implemented)
- ❌ Phase 5 job emission (structure ready, HTTP POST not wired up)
- ❌ Phase 6 specification and CI/CD implementation

**What's DEFERRED (Future Phases Beyond Current Scope):**
- 🔮 Canonical Product Model (Section 2)
- 🔮 EcomAgent Integration (Section 3)
- 🔮 Google Sheets Staging Layer (Section 4)
- 🔮 Advertising Agent / Campaign Creation (Section 6)

## Summary

### The Good News
APEG is a **well-engineered system with solid foundations following a sensible incremental strategy**. The spec describes the full vision, but the project has wisely focused on building the data/metrics foundation (Phases 1-5) first.

- ✅ Async architecture properly designed
- ✅ Testing comprehensive (52 tests passing)
- ✅ Phases 1-3 production-ready
- ✅ Phase 4-5 core infrastructure complete
- ✅ Clear separation between implemented vs. future features

### The Challenges
1. **Data layer is empty**: Tables exist but need population
2. **Phase 5 integration layer incomplete**: Analysis engine done, LLM client and job emission pending
3. **Documentation has redundancy**: ~300KB of duplicate research docs
4. **Phase 6 undefined**: No CI/CD specification exists yet
5. **Spec scope ambiguity**: 10K-line spec describes full vision, but only ~60% is target for current phases

### The Path Forward
**3-4 weeks of focused work** to complete Phases 1-5:
- **Week 1:** Data activation (populate tables, run collectors against production)
- **Week 2:** Phase 5 integration (LLM client + job emission - ~500 lines of code)
- **Week 3:** Production readiness (scheduler, CI/CD, deployment automation)

**Future work** (beyond current scope): EcomAgent integration, Google Sheets staging, Advertising Agent, Canonical Product Model

### Key Insight
This isn't a "lack of documentation" or "incomplete implementation" problem — it's a **smart incremental strategy with data activation as next step**.

The 10,337-line spec describes the **complete e-commerce automation vision**, but the project has **intentionally focused on the metrics/feedback foundation first** (Phases 1-5). This is the right approach - build solid data infrastructure before complex integrations.

**Immediate needs:**
1. Populate empty tables (strategy_tag_mappings, order_line_attributions)
2. Wire up Phase 5 execution layer (~500 lines: LLM client + job emission)
3. Add automation (scheduler, CI/CD)
4. Clean up documentation redundancy

The project is **~65-70% complete for Phases 1-5**, which is the current scope. The spec describes phases beyond this scope that are intentionally deferred.

---

## Future Phases (7+) - Deferred Implementation

**IMPORTANT FOR AUTONOMOUS AGENTS:** The items below are **OUT OF SCOPE** for current execution. They are documented here for completeness and future planning. **DO NOT ATTEMPT** to implement these unless explicitly instructed.

### Phase 7: Canonical Product Model (Spec Section 2)

**Purpose:** Unified data model for products flowing through SEO, Ads, and Metrics pipelines

**Status:** NOT STARTED - Deferred until Phases 1-5 complete

**Scope:**
- Create `src/apeg_core/schemas/canonical_product.py`
- Implement `CanonicalProduct` Pydantic model with cross-platform support
- Add platform-specific export methods (`.to_shopify()`, `.to_etsy()`)
- Implement tag hydration pattern (fetch → merge → push)
- Add validation for Shopify/Etsy constraints

**Key Requirements (from Spec Section 2):**
```python
class CanonicalProduct(BaseModel):
    # Core Identity
    product_id: str          # Universal identifier
    shopify_id: Optional[str]
    etsy_id: Optional[str]
    sku: Optional[str]
    handle: str              # URL slug

    # SEO Content
    title: str = Field(max_length=140)  # Etsy limit
    description_html: str
    meta_title: Optional[str]
    meta_description: Optional[str]
    tags: List[str]

    # Advertising
    strategy_tag: Optional[str]
    images: List[ImageRef]
    price: Optional[Decimal]

    # Versioning
    version: int = 1
    created_at: datetime
    updated_at: datetime
```

**Dependencies:**
- Requires Shopify and Etsy API integration complete
- Needs tag merge safety pattern implemented
- Validation framework for cross-platform constraints

**Estimated Effort:** 40-60 hours

**Acceptance Criteria:**
- [ ] CanonicalProduct model validates Shopify constraints (title ≤255, tags ≤250)
- [ ] CanonicalProduct model validates Etsy constraints (title ≤140, tags ≤13)
- [ ] `.to_shopify()` method merges existing tags (prevents destructive overwrites)
- [ ] `.to_etsy()` method strips HTML and selects top 13 tags deterministically
- [ ] Unit tests cover validation edge cases
- [ ] Integration test proves round-trip (Shopify → Canonical → Shopify) preserves data

---

### Phase 8: APEG → EcomAgent Integration (Spec Section 3)

**Purpose:** Integrate EcomAgent SEO engine into APEG via asyncio.to_thread wrapper

**Status:** NOT STARTED - Requires EcomAgent repository setup

**Scope:**
- Create editable package install for EcomAgent: `pip install -e ../EcomAgent`
- Add `pyproject.toml` to EcomAgent if missing
- Create `src/apeg_core/orchestrators/seo_orchestrator.py`
- Implement async wrapper using `asyncio.to_thread()` pattern
- Add configuration override mechanism (in-memory, not file-based)
- Test SEO engine call from APEG FastAPI endpoint

**Key Requirements (from Spec Section 3):**
```python
class SEOOrchestrator:
    def __init__(self):
        # Import EcomAgent (synchronous)
        from src.seo_engine.engine import SEOEngine
        self.engine = SEOEngine()
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_SEO)

    async def optimize_product_async(self, product_data, overrides, meta):
        """Async wrapper for sync SEO engine"""
        return await asyncio.to_thread(
            self.engine.optimize_product,
            product_data=product_data,
            overrides=overrides,
            meta=meta
        )
```

**Dependencies:**
- EcomAgent repository accessible at `../EcomAgent`
- EcomAgent has `optimize_product()` method with compatible signature
- Canonical Product Model implemented (Phase 7)

**Estimated Effort:** 30-40 hours

**Blockers:**
- EcomAgent codebase location/access
- EcomAgent API compatibility with APEG

**Acceptance Criteria:**
- [ ] EcomAgent imports successfully in APEG
- [ ] Async wrapper doesn't block event loop (verified with concurrent test)
- [ ] SEO engine processes product and returns optimized content
- [ ] Configuration overrides work (seasonal_tone, force_title_length, etc.)
- [ ] Integration test proves end-to-end: APEG call → EcomAgent → result

---

### Phase 9: Google Sheets Staging Layer (Spec Section 4)

**Purpose:** Mobile-friendly human approval interface for SEO changes before Shopify publication

**Status:** NOT STARTED - Requires Google Apps Script setup

**Scope:**
- Create Google Sheet with staging schema (run_id, product_id, proposed_title, etc.)
- Implement n8n ingestion workflow (POST results to sheet)
- Create Apps Script onChange trigger (detect APPROVED status)
- Implement n8n executor workflow (execute approved changes)
- Add single-run enforcement (prevent concurrent runs)
- Handle degraded mode (Sheets API failures)

**Key Requirements (from Spec Section 4):**
- Sheet columns: run_id, product_id, handle, status, original_title, proposed_title, shopify_admin_link, error_code, processed_at
- Metadata row (Row 1): run_id, run_timestamp, run_status, shop_admin_base_url
- Apps Script triggers webhook on status change to APPROVED
- N8N executor verifies: status==APPROVED, processed_at empty, DB status !=DONE
- Throttling: 20 rows/2 seconds (Google Sheets API rate limits)

**Dependencies:**
- Google Sheets API OAuth setup in n8n
- n8n workflow automation (ingestion + executor)
- Apps Script deployment (webhook callback)
- APEG API endpoint to receive approval callbacks

**Estimated Effort:** 50-70 hours (includes n8n workflow design + Apps Script)

**Blockers:**
- Google Cloud project setup for Sheets API
- n8n instance deployment and configuration
- Apps Script webhook endpoint setup

**Acceptance Criteria:**
- [ ] SEO results stream to Google Sheet (20 rows/2s throttling)
- [ ] Human changes status from PENDING → APPROVED in sheet
- [ ] Apps Script triggers n8n executor webhook
- [ ] N8N executor runs Shopify bulk mutation
- [ ] Sheet updates processed_at timestamp after execution
- [ ] Degraded mode handles Sheets API failures (saves to DB only)

---

### Phase 10: Advertising Agent Foundation (Spec Section 6)

**Purpose:** Automate Meta (Facebook/Instagram) advertising for SEO-optimized products

**Status:** NOT STARTED - Requires Meta Marketing API credentials

**Scope:**
- Create `src/apeg_core/agents/advertising_agent.py`
- Implement Meta Business SDK async wrapper (using `asyncio.to_thread()`)
- Create campaign structure: Campaign → AdSet → Ad
- Implement interest-based targeting (lookup via Targeting Search API)
- Add UTM tracking for metrics correlation
- Create campaigns in PAUSED state (manual approval required)
- Store campaign_id/ad_id in database for metrics linking

**Key Requirements (from Spec Section 6):**
```python
class MetaAdsClient:
    async def create_campaign_async(self, params):
        """Create OUTCOME_TRAFFIC campaign (no pixel required)"""
        return await asyncio.to_thread(self._create_campaign_sync, params)

    def _create_campaign_sync(self, params):
        campaign = Campaign(parent_id=self.ad_account.get_id_assured())
        campaign_params = {
            'name': params['name'],
            'objective': 'OUTCOME_TRAFFIC',  # V1: Traffic objective
            'status': 'PAUSED',              # Manual approval gate
            'special_ad_categories': [],     # Required even when empty
            'daily_budget': params['daily_budget']  # In cents
        }
        campaign.remote_create(params=campaign_params)
        return campaign
```

**Dependencies:**
- Meta Business Manager account setup
- Meta app credentials (APP_ID, APP_SECRET, ACCESS_TOKEN)
- Ad account ID (act_XXXXX)
- Facebook Page ID (for ad creatives)
- Instagram account ID (for placements)
- Strategy tag mapping (knows which products to advertise)

**Estimated Effort:** 80-100 hours (including Meta API learning curve)

**Blockers:**
- Meta Marketing API credentials
- Meta Business Manager access
- Test ad account with budget for validation

**Acceptance Criteria:**
- [ ] Campaign created with OUTCOME_TRAFFIC objective
- [ ] AdSet created with interest-based targeting (birthstone, jewelry, gifts)
- [ ] Carousel ad created with product images from Shopify
- [ ] UTM parameters track: utm_campaign={strategy_tag}, utm_content={ad_id}, utm_term={product_handle}
- [ ] Campaign stored in database with campaign_id for metrics correlation
- [ ] Campaign created in PAUSED state (manual activation required)
- [ ] Integration test proves: create campaign → verify in Meta Ads Manager

---

### Phase 11: Etsy Integration (BLOCKED - GPL Licensing)

**Purpose:** Sync SEO-optimized product descriptions to Etsy

**Status:** BLOCKED - etsyv3 library has GPL-3.0 license incompatible with APEG's MIT license

**Blocker Resolution Options:**
1. **Microservice isolation** (Recommended): Run Etsy sync as separate microservice to isolate GPL code
2. **Replace library**: Use Etsy REST API via custom HTTP calls (no GPL dependency)
3. **Internal-only**: Use GPL code for internal tooling only, never distribute

**Scope (if/when unblocked):**
- Isolate etsyv3 library in separate microservice
- Create HTTP API between APEG and Etsy microservice
- Implement Etsy listing creation (state: draft)
- Add Etsy-specific validation (title ≤140, tags ≤13, taxonomy_id required)
- Handle shipping profiles and Processing Profiles migration

**Estimated Effort:** 60-80 hours (microservice setup + API integration)

**Deferred Until:** GPL licensing conflict resolved

---

### Phase 12: Metrics Dashboard UI

**Purpose:** Web-based dashboard for querying and visualizing metrics data

**Status:** Deferred - SQLite queries sufficient for V1

**Scope:**
- Create React/Next.js dashboard application
- Connect to SQLite database (read-only access)
- Visualize strategy tag performance (CTR, ROAS, conversions by tag)
- Display product-level attribution (top performers, underperformers)
- Show feedback loop actions (Challenger proposals, outcomes)
- Filter by date range, strategy tag, campaign

**Dependencies:**
- Metrics database populated with production data
- UI framework choice (React, Vue, Svelte)
- Chart library (Chart.js, Recharts, D3)

**Estimated Effort:** 100-120 hours (full-stack UI development)

**Deferred Rationale:** SQLite queries via CLI are sufficient for V1. Dashboard is nice-to-have, not MVP blocker.

---

### Phase 13: Auto-Pause Logic & Budget Optimization

**Purpose:** Automatically pause underperforming ad campaigns and reallocate budgets

**Status:** Future V2 Feature

**Scope:**
- Implement auto-pause rules (e.g., CTR <0.3% for 7 days)
- Add budget reallocation algorithm (shift budget from losers to winners)
- Create notification system (email/Slack alerts for paused campaigns)
- Add override mechanism (human can prevent auto-pause)

**Estimated Effort:** 40-60 hours

**Deferred Rationale:** V1 uses manual control only. Auto-pause requires confidence in metrics accuracy first.

---

### Phase 14: Conversion Tracking & Meta Pixel

**Purpose:** Track purchases and ROAS at ad-level granularity

**Status:** Future V2 Feature - Requires Meta Pixel setup

**Scope:**
- Install Meta Pixel on Shopify store
- Implement conversion events (ViewContent, AddToCart, Purchase)
- Switch from OUTCOME_TRAFFIC to OUTCOME_SALES objective
- Add ROAS-based campaign optimization

**Dependencies:**
- Meta Pixel ID
- Shopify theme modification (embed Pixel script)
- Privacy policy updates (GDPR/CCPA compliance)

**Estimated Effort:** 30-40 hours

**Deferred Rationale:** OUTCOME_TRAFFIC is sufficient for V1. Conversion tracking adds complexity and privacy concerns.

---

### Phase 15: Review App Integration

**Purpose:** Enrich feedback loop context with customer reviews

**Status:** Future Enhancement - Requires third-party app connector

**Scope:**
- Integrate with review app API (Judge.me, Loox, Yotpo, etc.)
- Fetch top 5 most helpful reviews per product
- Extract review themes (positive/negative keywords)
- Include review context in LLM refinement prompts

**Dependencies:**
- Review app subscription (Judge.me, Loox, etc.)
- API credentials for chosen review app
- Review sentiment analysis (LLM or keyword-based)

**Estimated Effort:** 20-30 hours

**Deferred Rationale:** V1 spec defines review enrichment but notes Shopify has no native reviews API. Requires third-party app decision first.

---

## Modularization Plan (For Future ExecPlans)

When ready to execute phases, break this comprehensive plan into focused ExecPlans:

**Current Work (Execute Now):**
- `EXECPLAN-P4-data-population.md` - Populate strategy_tag_mappings and order_line_attributions
- `EXECPLAN-P5-llm-integration.md` - Implement Claude API client and job emission
- `EXECPLAN-P6-cicd-hardening.md` - GitHub Actions, license scanning, deployment

**Future Work (Execute Later):**
- `EXECPLAN-P7-canonical-model.md` - Unified product data model
- `EXECPLAN-P8-ecomagent-integration.md` - SEO engine async wrapper
- `EXECPLAN-P9-google-sheets-staging.md` - Approval interface
- `EXECPLAN-P10-advertising-agent.md` - Meta Marketing API integration
- `EXECPLAN-P11-etsy-integration.md` - Etsy sync (after GPL blocker resolved)

**Each ExecPlan should follow `.agent/PLANS.md` protocol:**
- Self-contained (no external references)
- Living document (Progress/Surprises/Decisions sections)
- Verifiable outcomes (acceptance criteria with observable behavior)
- Recovery protocol (idempotent, can resume after interruption)

---
