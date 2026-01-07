# Project Status - APEG
# Updated: 2026-01-06

## Phase Overview
| Phase | Name | Status | Goal | Evidence |
|---|---|---|---|---|
| 0 | Config + Cutover Readiness | IN_PROGRESS | Environment parity and cutover readiness | `docs/ACCEPTANCE_TESTS.md` |
| 1 | EcomAgent Standalone | COMPLETE | EcomAgent runs standalone and produces JSONL outputs | `docs/ACCEPTANCE_TESTS.md` |
| 2 | n8n Integration | IN_PROGRESS | n8n stages SEO changes and executes Shopify bulk ops | `docs/ACCEPTANCE_TESTS.md` |

## Current Phase
**Phase:** 0 - Config + Cutover Readiness
**Goal:** Enforce environment parity and complete demo-to-live readiness checks

**Objectives**
- Update environment docs
- Record Phase 0 evidence

**Evidence**
- docs/ACCEPTANCE_TESTS.md
- docs/evidence/phase0-evidence-20260106-0728Z.txt

## Risks / Architectural Debt
- Environment parity drift
- Cutover misconfiguration

## Blockers
- META_APP_SECRET missing
- N8N_BASE_URL missing

