# ExecPlan: Phase 5 Feedback Loop (Revised)

**Phase:** 5
**Created:** 2026-01-01
**Author:** Codex
**Status:** BLOCKED

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries,
Decision Log, and Outcomes & Retrospective MUST be updated as work proceeds.

Reference: This document follows `.agent/PLANS.md` protocol.

---

## Purpose / Big Picture

After this phase, the feedback loop can analyze collected metrics, generate SEO
challenger proposals, and execute safe Shopify SEO updates through the existing
Phase 3 API with traceable job IDs and outcomes stored in SQLite.
This unlocks a closed-loop refinement cycle that is constrained by Redis locks
and Shopify bulk mutation semantics already verified in Phase 3.

---

## Progress

- [x] (2026-01-01 07:53Z) Scanned feedback loop code: analyzer, schema, version_control, prompts, CLI
- [x] (2026-01-01 07:53Z) Scanned metrics collectors/schema for strategy_tag mappings and product_id GIDs
- [x] (2026-01-01 07:53Z) Cross-referenced Phase 3 API + n8n run logs (job_id, Redis lock, bulk op id)
- [x] (2026-01-01 07:54Z) Verify baseline tests (Step 1: 44 passed)
- [x] (2026-01-01 07:54Z) Add strategy_tag mapping enrichment for Meta metrics (module + run_analysis hook)
- [x] (2026-01-01 07:57Z) Re-ran unit tests after mapping enrichment (44 passed)
- [x] (2026-01-01 09:19Z) Implement propose mode (LLM challenger generation + seo_versions proposals; runtime requires FEEDBACK_LLM_API_KEY)
- [x] (2026-01-01 09:19Z) Implement execute mode (Phase 3 API job emission with batching; runtime requires APEG_API_KEY + APEG_API_BASE_URL)
- [x] (2026-01-01 09:19Z) Implement evaluate mode (outcome recording based on metrics windows)
- [x] (2026-01-01 09:19Z) Add unit tests for propose/execute/evaluate helpers (48 passed)
- [x] (2026-01-01 09:19Z) Update ACCEPTANCE_TESTS.md and PROJECT_PLAN_ACTIVE.md with evidence
- [x] (2026-01-01 09:56Z) Fix propose/evaluate runtime issues (missing ProductMetrics import, timezone-safe timestamps)
- [x] (2026-01-01 09:56Z) Run propose/execute/evaluate modes with credentials (no candidates/proposals available)
- [x] (2026-01-01 09:56Z) Re-run unit tests after fixes (48 passed)
- [x] (2026-01-01 10:02Z) Seed sample metrics/orders data (seed_dummy_data.py; placeholder product IDs)
- [x] (2026-01-01 10:02Z) Propose mode runs with seeded data (1 proposal created using stub LLM + dummy snapshot)
- [x] (2026-01-01 10:02Z) Execute mode attempted with dummy Phase 3 endpoint (blocked: localhost API unavailable)
- [x] (2026-01-01 10:02Z) Evaluate mode re-run (no applied versions yet)
- [x] (2026-01-01 10:08Z) Run full pytest suite (56 passed, 2 skipped)
- [x] (2026-01-01 10:08Z) Attempt integration suite (no tests collected)
- [x] (2026-01-01 10:14Z) Add integration test for propose mode (collected; skipped without credentials)
- [x] (2026-01-01 10:14Z) Re-run full pytest suite after integration test (56 passed, 3 skipped)

---

## Surprises & Discoveries

- **Observation:** Meta insights collection never populates `strategy_tag_mappings`, yet the analyzer joins Meta metrics against that table.
  **Evidence:** `src/apeg_core/metrics/meta_collector.py` writes `metrics_meta_daily` only; analyzer joins `metrics_meta_daily` -> `strategy_tag_mappings`.
  **Resolution:** Add a mapping enrichment step (naming-convention parse from Meta names) or analysis will remain data-starved.

- **Observation:** Phase 5 CLI only implements `analyze`; `propose`, `execute`, `evaluate` exit with errors.
  **Evidence:** `scripts/run_feedback_loop.py` has `logger.error(... not yet implemented)` for those modes.
  **Resolution:** Implement each mode with explicit I/O boundaries and tests.

- **Observation:** LLM prompt output includes fields not supported by Phase 3 updates (e.g., `alt_text_rules`).
  **Evidence:** `src/apeg_core/feedback/prompts.py` output schema vs `ProductUpdateSpec` (tags_add/remove, seo only).
  **Resolution:** Map LLM output to supported fields only and ignore unsupported fields; document in decision log.

- **Observation:** Phase 3 API returns only `job_id` and lacks a status endpoint.
  **Evidence:** `/api/v1/jobs/seo-update` response model contains job_id/status/run_id; no GET endpoint exists.
  **Resolution:** Treat job_id as write-trace only; evaluate outcome by metrics window, not API status.

- **Observation:** Product-level attribution lacks CTR/CPC fields needed for spec's evaluation math.
  **Evidence:** `order_line_attributions` only stores revenue, units, and strategy_tag; no click or CTR metrics.
  **Resolution:** Use ROAS-based outcome evaluation for now; document threshold choices in Decision Log.

- **Observation:** Propose/execute/evaluate runs completed but returned no eligible targets/proposals in sandbox data.
  **Evidence:** `run_feedback_loop.py --mode propose` logged "No eligible targets for propose mode"; execute/evaluate logged "No proposals ready" / "No versions ready".
  **Resolution:** Requires real metrics data and approved proposals to exercise full flow.

- **Observation:** Execute mode cannot reach Phase 3 API in sandbox (localhost blocked).
  **Evidence:** `Phase 3 API request failed: Cannot connect to host localhost:8000`
  **Resolution:** Use remote APEG_API_BASE_URL in real environment or run uvicorn with accessible host.

- **Observation:** Integration propose test collected but skipped without credentials.
  **Evidence:** `tests/integration/test_feedback_loop_propose_integration.py` skipped due to missing env vars.
  **Resolution:** Provide Shopify + Anthropic credentials to run integration test end-to-end.

---

## Decision Log

- **Decision:** Use Phase 3 API for all Shopify updates (no direct Shopify writes in Phase 5).
  **Rationale:** Phase 3 already enforces Redis lock and safe-write tag merge; reusing it avoids concurrency bugs.
  **Alternatives Considered:** Direct Shopify GraphQL updates (rejected: would bypass Redis lock invariants).
  **Date:** 2026-01-01

- **Decision:** Batch approved updates into a single job per run (or chunk sequentially).
  **Rationale:** Redis lock allows only one bulk operation per shop; batching avoids lock contention.
  **Alternatives Considered:** Fire one job per product (rejected: would fail on lock contention).
  **Date:** 2026-01-01

- **Decision:** Enrich `strategy_tag_mappings` from Meta names using naming conventions.
  **Rationale:** Without mappings, Meta spend/impressions/ctr are absent and the diagnosis matrix yields insufficient data.
  **Alternatives Considered:** Ignore Meta metrics (rejected: roas/ctr would be misleading or zero).
  **Date:** 2026-01-01

- **Decision:** Store Phase 3 job IDs in `seo_versions.phase3_job_id` and `feedback_actions.notes` without schema changes.
  **Rationale:** Avoid schema changes (requires approval) while keeping traceability.
  **Alternatives Considered:** Add a new job tracking table (rejected: schema change needs approval).
  **Date:** 2026-01-01

- **Decision:** Evaluate challenger outcomes using product-level ROAS changes and order volume thresholds.
  **Rationale:** Product-level CTR/CPC are not available in current schema; ROAS and orders are the most reliable metrics available without schema changes.
  **Alternatives Considered:** Derive CTR from strategy-level metrics (rejected: would not isolate product impact).
  **Date:** 2026-01-01

- **Decision:** Allow optional stub LLM and dummy product snapshots for seeded sample data runs.
  **Rationale:** Enables propose-mode validation in environments without Shopify or Anthropic credentials.
  **Alternatives Considered:** Require full credentials before running (rejected: blocks local validation).
  **Date:** 2026-01-01

---

## Outcomes & Retrospective

- What worked well? Propose/execute/evaluate logic is now wired with helper functions and unit coverage; Phase 3 job batching aligns with Redis lock constraints.
- What would you do differently? Add CTR/CPC to product-level attribution so evaluation can match spec formulas.
- What should the next phase know? Runtime validation of propose/execute/evaluate is blocked until Shopify/Anthropic credentials and Phase 3 API connectivity are available.

---

## Context and Orientation

Phase 5 builds on:
- Phase 3 API (`POST /api/v1/jobs/seo-update`) for Shopify bulk mutations with Redis locks.
- Phase 4 metrics in SQLite (`metrics_meta_daily`, `order_attributions`, `order_line_attributions`).
- Feedback schema (`seo_versions`, `feedback_runs`, `feedback_actions`) already present.

Key files:
- `scripts/run_feedback_loop.py` — CLI entry point (analyze/propose/execute/evaluate)
- `src/apeg_core/feedback/analyzer.py` — diagnosis matrix + candidate selection
- `src/apeg_core/feedback/version_control.py` — seo_versions lifecycle
- `src/apeg_core/feedback/prompts.py` — LLM prompt schema + validation
- `src/apeg_core/feedback/mapping.py` — naming-convention strategy tag mapper
- `src/apeg_core/metrics/schema.py` — metrics + mappings tables
- `src/apeg_core/metrics/meta_collector.py` — Meta insights persistence
- `src/apeg_core/metrics/shopify_collector.py` — Shopify orders + line items (product GID)
- `src/apeg_core/api/routes.py` — Phase 3 job submission + background execution

Terminology:
- **strategy_tag_mappings:** Maps Meta entity IDs to strategy tags for aggregations.
- **seo_versions:** Tracks champion/challenger snapshots and job IDs.
- **Phase 3 job:** Background bulk mutation triggered via API; uses Redis lock per shop.

---

## Plan of Work

1. **Mapping enrichment (Meta -> strategy_tag):**
   - Add a helper that reads `metrics_meta_daily.raw_json` for `campaign_name`/`ad_name`,
     uses `StrategyTagMapper` to infer strategy tags, and upserts `strategy_tag_mappings`.
   - Run this before analysis so Meta metrics can be joined in `FeedbackAnalyzer`.

2. **Propose mode implementation:**
   - Extend CLI to load candidates, pick product-level targets, fetch current SEO snapshots,
     generate challenger SEO via LLM, validate outputs, and write `seo_versions` proposals.
   - Use `SEOVersionControl.create_proposal()` and write decision logs.

3. **Execute mode implementation:**
   - Select approved `seo_versions` (or auto-approve when approval disabled).
   - Build `ProductUpdateSpec` list with supported fields only (seo title/description, tags_add/remove).
   - Send a single Phase 3 API job per run; chunk sequentially if actions exceed batch limit.
   - Persist `phase3_job_id` and update status to APPLIED with evaluation window.

4. **Evaluate mode implementation:**
   - Compare baseline vs evaluation windows using existing metrics.
   - Record WIN/LOSS/INCONCLUSIVE in `seo_versions`.

5. **Tests and docs:**
   - Unit tests for mapping enrichment, propose parsing, execute batching, and evaluate outcomes.
   - Update ACCEPTANCE_TESTS.md with evidence; update PROJECT_PLAN_ACTIVE.md status.

---

## Concrete Steps

### Step 1: Verify Baseline

```bash
PYTHONPATH=. ./venv/bin/python -m pytest tests/unit/ -v
```

**Expected:** Unit tests pass (record count)

**Actual:** PASSED (2026-01-01 07:54Z) — 44 passed

---

### Step 2: Mapping Enrichment (Meta -> strategy_tag_mappings)

- Add `src/apeg_core/feedback/mapping_enrichment.py` to parse Meta raw_json and upsert mappings.
- Wire into `scripts/run_feedback_loop.py` before analysis.

**Expected:** `strategy_tag_mappings` populated for any Meta entities with recognizable names.

**Actual:** Implemented `src/apeg_core/feedback/mapping_enrichment.py` and wired into `run_feedback_loop.py` analyze mode (2026-01-01 07:54Z)

---

### Step 3: Propose Mode (LLM + seo_versions)

- Add LLM client (aiohttp) using `ANTHROPIC_API_KEY` (no new dependencies).
- Fetch current SEO snapshot for product IDs via Shopify GraphQL.
- Validate LLM JSON using `SEOChallengerPrompt.validate_output()`.
- Create proposals in `seo_versions`.

---

### Step 4: Execute Mode (Phase 3 Job Emission)

- Build `ProductUpdateSpec` list from proposals.
- POST to Phase 3 API using `APEG_API_KEY` and `SHOPIFY_STORE_DOMAIN`.
- Persist job ID in `seo_versions.phase3_job_id` and mark APPLIED.

---

### Step 5: Evaluate Mode

- Compare baseline window vs evaluation window metrics.
- Update `seo_versions.outcome`.

---

### Step 6: Tests + Evidence

```bash
PYTHONPATH=. ./venv/bin/python -m pytest tests/unit/ -v
```

Record evidence in `docs/ACCEPTANCE_TESTS.md`.

---

## Validation and Acceptance

1. `run_feedback_loop.py --mode analyze` populates `feedback_runs` and `feedback_actions`.
2. `--mode propose` creates `seo_versions` rows with status PROPOSED and valid diff snapshots.
3. `--mode execute` submits a Phase 3 job and records `phase3_job_id` without lock contention.
4. `--mode evaluate` updates outcomes based on metrics windows.
5. Unit tests cover mapping enrichment and execute batching.

---

## Idempotence and Recovery

All steps are safe to repeat:
- Mapping enrichment uses upsert on `strategy_tag_mappings`.
- Propose mode writes new proposals; use run_id to trace duplicates.
- Execute mode batches approved proposals only.

Recovery:
1. Read this ExecPlan Progress section.
2. Re-run unit tests.
3. Resume from first unchecked Progress item.

---

## Interfaces and Dependencies

**Environment Variables:**
- `FEEDBACK_ENABLED`, `FEEDBACK_WINDOW_DAYS`, `FEEDBACK_MIN_*`, `FEEDBACK_REQUIRE_APPROVAL`
- `APEG_API_KEY`, `SHOPIFY_STORE_DOMAIN`, `APEG_API_BASE_URL`
- `ANTHROPIC_API_KEY` (for LLM calls)

**External Services:**
- Phase 3 API (FastAPI)
- Shopify Admin API
- Redis (used by Phase 3 API)
- Meta API (metrics source)

**Database Tables (no schema changes planned):**
- `seo_versions`, `feedback_runs`, `feedback_actions`
- `metrics_meta_daily`, `order_attributions`, `order_line_attributions`
- `strategy_tag_mappings`

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-01-01 | Codex | Initial Phase 5 revised ExecPlan |
