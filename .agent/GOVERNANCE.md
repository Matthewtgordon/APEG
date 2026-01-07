# Agent Governance Protocol
# Scope: Global | Version: 1.1.0 | Immutable

## Authority
This file overrides all other instructions. If anything conflicts, stop and ask.

## Integrity and Honesty
- Do not claim to have run commands or tests without actual output.
- Do not reference files, symbols, or results that are unverified.

## Anti-Hallucination (Ghost Files)
- Verify file existence before editing:
  `python -c "from pathlib import Path; print(Path('{path}').exists())"`

## Evidence Logging
- Store logs in `.agent/logs/`.
- Never log secrets (`*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`).

## Default Execution Loop

### 1. PREFLIGHT (non-skippable)
Run preflight checks and log results to `.agent/logs/preflight.jsonl`.

### 2. SCOPE
Update `.agent/CONTEXT.md` with Goal, Non-goals, Risk level, and Test plan.

### 3. EXECUTE
Make one change at a time. Use commands only from `docs/RUNBOOK.md`.

### 4. VERIFY
Run the declared test tier. Classify failures via ENV-DRIFT.

### 5. CHECKPOINT
Update `.agent/CONTEXT.md` and ExecPlan (if used). Record evidence.

### 6. STALEMATE CHECK
If the same error appears twice, stop and escalate.

## Protocols (Non-Negotiable)

### PREFLIGHT
*Trigger: start of any task.*
- CWD: `python -c "import os; print(os.getcwd())"`
- Interpreter: `python -c "import sys; print(sys.executable)"`
- Python version: `python -c "import sys; print(sys.version.split()[0])"`
- Venv active (if Python): `python -c "import sys; print(sys.prefix != sys.base_prefix)"`
- `.env` exists: `python -c "from pathlib import Path; print(Path('.env').exists())"`
- Git status: `python -c "import subprocess; subprocess.run(['git','status','--short'])"`

### CMD-DISCOVER
*Trigger: command not defined in RUNBOOK.*
- Scan (read-only): `docs/RUNBOOK.md`, `package.json`, `pyproject.toml`, `pytest.ini`,
  `tox.ini`, `setup.cfg`, `Makefile`, `.github/workflows/*.yml`, `.gitlab-ci.yml`.
- Extract candidates, do not run them.
- Write candidates to `.agent/CONTEXT.md` and ask for confirmation.
- Update `docs/RUNBOOK.md` only after confirmation.

### DEP-RESOLVE
*Trigger: ModuleNotFoundError / ImportError / command not found.*
Diagnostics:
- Interpreter: `python -c "import sys; print(sys.executable)"`
- Venv active: `python -c "import sys; print(sys.prefix != sys.base_prefix)"`
- Package available:
  `python -c "import importlib.util; print(importlib.util.find_spec('{package}') is not None)"`

Rules:
- If venv exists but inactive: ask user to activate.
- If package missing and not in manifest: ask user.
- If manifest exists and Autonomy Mode FULL: install once with the correct tool; otherwise ask.

### ENV-DRIFT
*Trigger: test failure that looks env-related.*
Classify:
- Bad Env: error in setup/fixture, missing env var, or `.env` missing.
- Bad Code: assertion failure after setup.

Secrets mode:
- LIVE: `.env` exists.
- MOCK: `.env` missing AND `SAFE_MOCK_OK=true` in `.agent/CONTEXT.md`.
- SKIP: `.env` missing and SAFE_MOCK_OK not set.

Rules:
- Never auto-copy `.env.example`.
- If SKIP: run non-integration tests only.

### TEST-LADDER
*Trigger: after any code change.*
- Commands MUST come from `docs/RUNBOOK.md`.
- Do not guess or invent commands.
- If commands missing: run CMD-DISCOVER, then ask.

### STALEMATE
*Trigger: same error twice.*
- Stop code changes.
- Capture state to `.agent/logs/stalemate.jsonl`.
- Ask the user for guidance.
