# AGENTS.md - APEG
# Version: 1.0.0 | Updated: 2025-12-29

## Read First (Order & Authority)
1. `.agent/GOVERNANCE.md` - immutable rules; highest authority
2. `.agent/CONTEXT.md` - current status and immediate next action
3. `docs/RUNBOOK.md` - commands reference
4. `.agent/PLANS.md` - ExecPlan protocol

If instructions conflict, stop and ask.

## Overview
APEG orchestrates SEO updates, ad campaigns, and metrics feedback across Shopify using EcomAgent, N8N, and Meta Ads.

**Stack:** Python 3.11+ | FastAPI | SQLite
**Architecture:** Async master orchestrator with sync agent wrappers (asyncio.to_thread)

## Boundaries
If any ASK FIRST condition applies, stop and request approval. If any NEVER condition would be violated, do not proceed.

### ALWAYS
- Wrap sync EcomAgent calls with asyncio.to_thread to preserve async architecture.
- Use Shopify GraphQL SEO input object product.seo { title, description }.
- Require APEG_ENV and APEG_ALLOW_WRITES=YES for any write path.
- Keep human approval workflow (Google Sheets staging) in place for Shopify writes.

### ASK FIRST
- Add or change environment variables in .env.example.
- Add new dependencies or change package strategy (EcomAgent packaging or pip installs).
- Modify bulk operation sequencing or locking behavior.
- Change Etsy integration approach (GPL isolation vs custom API).

### NEVER
- Import GPL-3.0 etsyv3 into the APEG codebase.
- Bypass approval workflow for Shopify writes.
- Use product.metafields.seo.title (invalid SEO field mapping).
- Commit secrets or credentials.

## Key Files
| Purpose | Path |
|---------|------|
| Entry point | `src/apeg_core/main.py` |
| SEO orchestrator | `src/apeg_core/agents/seo_orchestrator.py` |
| Advertising agent | `src/apeg_core/agents/advertising_agent.py` |
| Metrics collector | `src/apeg_core/metrics/collector.py` |
| DB schema | `src/apeg_core/db/schema.sql` |

## Planning
For complex tasks (>30 min, multi-file, or external integrations), create an ExecPlan following `.agent/PLANS.md`.
