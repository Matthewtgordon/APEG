# Project Context - APEG
# Generated: 2026-01-06 07:28Z

## Immediate Next Action
- Action: Update docs/PROJECT_PLAN_ACTIVE.md with Phase 0 evidence statuses
- File: `docs/PROJECT_PLAN_ACTIVE.md`
- Why: Phase 0 evidence file exists; plan needs status update

## Active Work
- ExecPlan: `.agent/plans/EXECPLAN-phase-0-cutover.md`
- Last Checkpoint: 2026-01-06 07:28Z

## Current State
- Phase: 0 - Config + Cutover Readiness
- Status: IN_PROGRESS
- Blockers:
- Etsy integration blocked by GPL-3.0 etsyv3 license

## Constraints (Fresh in RAM)
- No GPL-3.0 dependencies in APEG
- Do not bypass human approval for Shopify writes
- Use product.seo { title, description } for Shopify SEO updates
- Writes require APEG_ALLOW_WRITES=YES and APEG_ENV set

## Preflight Status
- cwd: `/home/matt/repos/APEG`
- interpreter: `unknown`
- python_version: `unknown`
- venv_active: `unknown`
- env_exists: `true`
- git_status: `unknown`
- branch: `unknown`
- test_cmd_found: `true`
- secrets_mode: `LIVE`
- SAFE_MOCK_OK: `false`
- last_preflight: `2026-01-06 07:28Z`

## Scope (Current Task)
- Goal: Record Phase 0 evidence status and missing inputs
- Non-goals: No code changes
- Risk level: LOW
- Test plan: test.smoke

## Pending Inputs (Non-Blocking)
- Provide META_APP_SECRET - needed for: Meta token validation
- Provide N8N_BASE_URL - needed for: n8n credential check
