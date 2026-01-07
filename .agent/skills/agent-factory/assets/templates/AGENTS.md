# AGENTS.md - {{PROJECT_NAME}}
# Version: 1.0.0 | Updated: {{UPDATED}}

## Read First (Order & Authority)
1. `.agent/GOVERNANCE.md` - immutable rules; highest authority
2. `.agent/CONTEXT.md` - current status and immediate next action
3. `docs/RUNBOOK.md` - commands reference
4. `.agent/PLANS.md` - ExecPlan protocol

If instructions conflict, stop and ask.

## Overview
{{ONE_SENTENCE_DESCRIPTION}}

**Stack:** {{LANGUAGE}} {{VERSION}} | {{FRAMEWORK}} | {{DATABASE}}
**Architecture:** {{ARCHITECTURE}}

## Boundaries
If any ASK FIRST condition applies, stop and request approval. If any NEVER condition would be violated, do not proceed.

### ALWAYS
{{ALWAYS_BLOCK}}

### ASK FIRST
{{ASK_BLOCK}}

### NEVER
{{NEVER_BLOCK}}

## Key Files
| Purpose | Path |
|---------|------|
{{KEY_FILES_ROWS}}

## Planning
For complex tasks (>30 min, multi-file, or external integrations), create an ExecPlan following `.agent/PLANS.md`.
