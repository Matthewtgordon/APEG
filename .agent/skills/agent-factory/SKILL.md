---
name: agent-factory
description: Generate project agent configuration files (AGENTS.md, .agent/GOVERNANCE.md, .agent/PLANS.md, .agent/CONTEXT.md, docs/RUNBOOK.md, docs/PROJECT_STATUS.md, and optional .agent/skills/*/SKILL.md) from a structured spec. Use when the user asks to create or update agent config files, wants an "Agent Factory" setup, or needs repeatable template-based generation.
---

# Agent Factory

Generate a full, consistent agent configuration set from a single JSON spec.

## Quick Start (copy-paste)
Command:
    python3 scripts/render_agent_factory.py --spec references/spec.example.json --output-root /path/to/repo

Expected:
    Wrote 4 required files (+ optional files if provided in spec)

## Inputs (no guessing)
- Required file: JSON spec (see `references/spec.md`)
- Preconditions: Python 3.8+, write access to target repo
- Optional sections: `runbook`, `status`, `skills` (omit to skip those files)

## Scripts (exact signatures)
### scripts/render_agent_factory.py
- Purpose: Render templates into project files from a JSON spec
- Required args: `--spec <path>`
- Optional args: `--output-root <dir>`, `--templates <dir>`, `--validate-only`
- Command:
    python3 scripts/render_agent_factory.py --spec <path/to/spec.json> --output-root <repo>
- Expected:
    Wrote AGENTS.md, .agent/GOVERNANCE.md, .agent/PLANS.md, .agent/CONTEXT.md

## Workflow (short)
1. Gather project details and fill the JSON spec (use `references/spec.md`).
2. Run `scripts/render_agent_factory.py` to generate files.
3. Review outputs and re-run if updates are needed.

## References (load only when needed)
- `references/spec.md` - Required fields and optional sections
- `references/spec.example.json` - Example spec to copy and edit

## Assets
- `assets/templates/` - Source templates used by the renderer
