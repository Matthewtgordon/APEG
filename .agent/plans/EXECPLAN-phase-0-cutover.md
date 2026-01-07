# ExecPlan: Phase 0 Config and Cutover Readiness
**Phase:** 0 | **Created:** 2026-01-06 | **Status:** IN_PROGRESS
This document is live. Update Progress, Surprises, and Decision Log at every stop.

## Progress (Update First)
- [x] (2026-01-06 05:33Z) Created ExecPlan and scoped Phase 0 deliverables
- [x] (2026-01-06 05:42Z) Audit `.env.example` against spec Section 1.8 (prepare change list)
- [x] (2026-01-06 06:26Z) Update `.env.example` with missing placeholders and LLM provider keys
- [x] (2026-01-06 06:36Z) Update `docs/ENVIRONMENT.md` to reflect canonical variables and parity rules
- [x] (2026-01-06 06:37Z) Add `ANTHROPIC_MODEL` placeholder to env template and docs
- [~] (SKIPPED: Deferred until config loader requirements are clarified; document env usage first)
- [x] (2026-01-06 07:28Z) Record Phase 0 acceptance evidence in `docs/ACCEPTANCE_TESTS.md`
- [ ] Update Phase 0 checklist items in `docs/PROJECT_PLAN_ACTIVE.md`

## Surprises & Discoveries (If none, write "None unexpected")
- **Observation:** No LLM router configuration found; feedback loop uses Anthropic-only env keys.
  **Evidence:** `scripts/run_feedback_loop.py` reads `FEEDBACK_LLM_API_KEY` or `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`.
  **Resolution:** Documented provider keys in `.env.example` and `docs/ENVIRONMENT.md`; router config can be added later if needed.

## Decision Log (Record "why," not just "what")
- **Decision:** Start with Phase 0 environment parity tasks from `docs/PROJECT_PLAN_ACTIVE.md`
  **Rationale:** Phase 0 is the current gate and blocks phase completion until parity passes
  **Alternatives:** Jump to Phase 3-5 implementation work (rejected; violates current gating)
  **Date:** 2026-01-06
- **Decision:** Defer central config loader until env usage is documented and requirements are clarified
  **Rationale:** Avoids introducing a new abstraction without a spec-backed contract
  **Alternatives:** Implement loader immediately (rejected for now)
  **Date:** 2026-01-06

## Purpose (2-3 sentences)
Phase 0 ensures environment parity and cutover readiness so the system can safely move from demo to live without config drift. After completion, required environment variables are canonicalized, validation is enforced, and evidence is logged in acceptance tests.

## Context (Minimal)
- Current phase is Phase 0 per `docs/PROJECT_PLAN_ACTIVE.md`
- Spec anchors: Section 1.8 (Environment & Configuration Boundary) and Appendix F (Demo -> Live)
- Key files: `.env.example`, `docs/ENVIRONMENT.md`, `docs/ACCEPTANCE_TESTS.md`, `docs/PROJECT_PLAN_ACTIVE.md`

## Plan of Work (Short)
- `.env.example` -> compare against spec Section 1.8; list missing or deprecated vars
- `docs/ENVIRONMENT.md` -> update to reflect canonical vars and parity rules from spec
- `src/apeg_core/config.py` or equivalent -> confirm validation behavior and update if needed
- `docs/ACCEPTANCE_TESTS.md` -> add evidence placeholders or results for Phase 0 tests
- `docs/PROJECT_PLAN_ACTIVE.md` -> check off completed Phase 0 items with dates

## Validation & Acceptance (Observable)
- Run: Shopify auth smoke test (`{ shop { name } }`) and record output in `docs/ACCEPTANCE_TESTS.md`
- Run: Meta token debug and record scopes/validity in `docs/ACCEPTANCE_TESTS.md` (or mark DEFERRED)
- Verify: n8n credential IDs documented for DEMO in `docs/ACCEPTANCE_TESTS.md`

## Outcomes & Retrospective (At completion)
- What worked
- What didn't
- What's next
