# Project Context - {{PROJECT_NAME}}
# Generated: {{CONTEXT_GENERATED}}

## Immediate Next Action
- Action: {{IMMEDIATE_ACTION}}
- File: `{{IMMEDIATE_FILE}}`
- Why: {{IMMEDIATE_WHY}}

## Active Work
- ExecPlan: `{{EXECPLAN_PATH}}`
- Last Checkpoint: {{LAST_CHECKPOINT}}

## Current State
- Phase: {{PHASE_NUMBER}} - {{PHASE_NAME}}
- Status: {{PHASE_STATUS}}
- Blockers:
{{BLOCKERS_BLOCK}}

## Constraints (Fresh in RAM)
{{CONSTRAINTS_BLOCK}}

## Preflight Status
- cwd: `{{PREFLIGHT_CWD}}`
- interpreter: `{{PREFLIGHT_INTERPRETER}}`
- python_version: `{{PREFLIGHT_PYTHON_VERSION}}`
- venv_active: `{{PREFLIGHT_VENV_ACTIVE}}`
- env_exists: `{{PREFLIGHT_ENV_EXISTS}}`
- git_status: `{{PREFLIGHT_GIT_STATUS}}`
- branch: `{{PREFLIGHT_BRANCH}}`
- test_cmd_found: `{{PREFLIGHT_TEST_CMD_FOUND}}`
- secrets_mode: `{{PREFLIGHT_SECRETS_MODE}}`
- SAFE_MOCK_OK: `{{PREFLIGHT_SAFE_MOCK_OK}}`
- last_preflight: `{{PREFLIGHT_LAST}}`

## Scope (Current Task)
- Goal: {{SCOPE_GOAL}}
- Non-goals: {{SCOPE_NON_GOALS}}
- Risk level: {{SCOPE_RISK}}
- Test plan: {{SCOPE_TEST_PLAN}}

## Pending Inputs (Non-Blocking)
{{PENDING_INPUTS_BLOCK}}
