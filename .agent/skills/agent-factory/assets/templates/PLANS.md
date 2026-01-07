# ExecPlan Protocol
# Version: {{PLANS_VERSION}} | Methodology definition

## When to Create an ExecPlan
Create when:
- >30 minutes of work
- Multiple files coordinated
- External integrations
- User requests an execution plan

Do NOT create for:
- Single-file fixes
- Docs-only updates
- Simple test additions

## RECOVERY PROTOCOL (Read First, Use Always)
If context is lost or you are resuming:
1. Open the active ExecPlan in `.agent/plans/` and read **Progress** first.
2. Check **Surprises** and **Decision Log** to avoid repeating work.
3. Run `git status` to see uncommitted changes.
4. Run the primary test command to confirm baseline.
5. Resume from the first unchecked Progress item.

If any step fails, document it in **Surprises** and continue.

---

# ExecPlan Template (copy for new plan)

# ExecPlan: {Short, Action-Oriented Title}
**Phase:** {N} | **Created:** {YYYY-MM-DD} | **Status:** IN_PROGRESS | BLOCKED | COMPLETE
This document is live. Update Progress, Surprises, and Decision Log at every stop.

## Progress (Update First)
- [ ] (YYYY-MM-DD HH:MMZ) {specific step}
- [ ] {partial: completed X; remaining Y}
- [~] (SKIPPED: reason + Decision Log ref)

## Surprises & Discoveries (If none, write "None unexpected")
- **Observation:** {what happened}
  **Evidence:** {error/log/test}
  **Resolution:** {what you did}

## Decision Log (Record "why," not just "what")
- **Decision:** {choice made}
  **Rationale:** {why}
  **Alternatives:** {what else considered}
  **Date:** {YYYY-MM-DD}

## Purpose (2-3 sentences)
State what becomes possible after this work and how it's observed.

## Context (Minimal)
- Current state relevant to this task
- Key files (full paths)
- Define any jargon used

## Plan of Work (Short)
- File path -> change summary
- Order of operations

## Validation & Acceptance (Observable)
- Run: {command}
- Expected: {output/behavior}
- Verify: {log/UI evidence}

## Outcomes & Retrospective (At completion)
- What worked
- What didn't
- What's next
