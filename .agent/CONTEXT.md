# CONTEXT - APEG
# Generated: 2026-01-06 07:28Z | Update every session start

## IMMEDIATE NEXT ACTION (Mandatory)
- Action: Update Phase 0 checklist items to reflect evidence status (PASS/SKIPPED) and missing inputs.
- File to edit now: `docs/PROJECT_PLAN_ACTIVE.md`
- Why: Phase 0 tracking should reflect current evidence run results.

## ACTIVE PLAN
- ExecPlan: `.agent/plans/EXECPLAN-phase-0-cutover.md`
- Last checkpoint: 2026-01-06 07:28Z

## RED LINES (Must obey)
- No GPL-3.0 dependencies in APEG; isolate Etsy or use REST.
- Do not bypass Google Sheets staging and human approval for Shopify writes.
- Use product.seo { title, description } for Shopify GraphQL SEO updates.
- Writes require APEG_ALLOW_WRITES=YES and APEG_ENV set.

## BLOCKERS (If any)
- Etsy integration blocked by GPL-3.0 etsyv3 license.
