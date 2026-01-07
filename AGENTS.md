# AGENTS.md - APEG
# Version: 1.0.0 | Updated: 2026-01-06

## Read First
1. `.agent/CONTEXT.md` - immediate state and next action
2. `.agent/GOVERNANCE.md` - execution loop and protocols
3. `docs/RUNBOOK.md` - command registry and test tiers
4. `.agent/PLANS.md` - ExecPlan protocol

## Autonomy Mode
Current: FULL
- FULL: execute the loop autonomously; ask only for ASK FIRST items
- PARTIAL: pause after each checkpoint for review
- MANUAL: propose changes; user executes

## Boundaries

### ALWAYS
- Use commands only from docs/RUNBOOK.md
- Run test.smoke after every code change
- Wrap sync EcomAgent calls with asyncio.to_thread

### ASK FIRST
- Add or change environment variables in .env.example
- Add new dependencies or change package strategy
- Modify bulk operation sequencing or locking behavior

### NEVER
- Import GPL-3.0 etsyv3 into APEG
- Bypass approval workflow for Shopify writes
- Commit secrets or credentials

## Context Pointers
- `.agent/CONTEXT.md` - session boot and immediate next action
- `.agent/GOVERNANCE.md` - non-negotiable protocols
- `.agent/PLANS.md` - ExecPlan structure
- `docs/RUNBOOK.md` - commands and test tiers
- `docs/PROJECT_STATUS.md` - long-term roadmap (if present)

## Key Files
| Purpose | Path |
|---------|------|
| Entry point | `src/apeg_core/main.py` |
| SEO orchestrator | `src/apeg_core/agents/seo_orchestrator.py` |
| Metrics collector | `src/apeg_core/metrics/collector.py` |
| Feedback loop | `src/apeg_core/feedback/analyzer.py` |
| Tests | `tests/` |
