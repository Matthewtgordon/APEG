# AGENTS.md - {{PROJECT_NAME}}
# Version: 1.0.0 | Updated: {{UPDATED}}

## Read First
1. `.agent/CONTEXT.md` - immediate state and next action
2. `.agent/GOVERNANCE.md` - execution loop and protocols
3. `docs/RUNBOOK.md` - command registry and test tiers
4. `.agent/PLANS.md` - ExecPlan protocol

## Autonomy Mode
Current: {{AUTONOMY_MODE}}
- FULL: execute the loop autonomously; ask only for ASK FIRST items
- PARTIAL: pause after each checkpoint for review
- MANUAL: propose changes; user executes

## Boundaries

### ALWAYS
{{ALWAYS_BLOCK}}

### ASK FIRST
{{ASK_BLOCK}}

### NEVER
{{NEVER_BLOCK}}

## Context Pointers
- `.agent/CONTEXT.md` - session boot and immediate next action
- `.agent/GOVERNANCE.md` - non-negotiable protocols
- `.agent/PLANS.md` - ExecPlan structure
- `docs/RUNBOOK.md` - commands and test tiers
- `docs/PROJECT_STATUS.md` - long-term roadmap (if present)

## Key Files
| Purpose | Path |
|---------|------|
{{KEY_FILES_ROWS}}
