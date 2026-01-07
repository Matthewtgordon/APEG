# ExecPlan Protocol
# Version: {{PLANS_VERSION}}

## When to Create an ExecPlan
Create when:
- Work is >30 minutes
- Multiple files must be coordinated
- External API integration is involved
- User requests a plan or phase implementation

Do NOT create for:
- Single-file fixes
- Documentation-only updates
- Simple test additions

## Non-Negotiable Requirements
1. Self-contained for a new reader.
2. Living document: update Progress, Surprises, Decision Log, Outcomes.
3. Verifiable outcomes (observable behavior).
4. No external links; internal refs allowed and required.
5. Preflight before work; record results.
6. Execution loop compliance (see GOVERNANCE).

## ExecPlan Template (copy for new plan)

```markdown
# ExecPlan: {Short, Action-Oriented Title}

**Status:** IN_PROGRESS | BLOCKED | COMPLETE
**Created:** {YYYY-MM-DD}
**Owner:** {Name or Agent}

## Progress
- [ ] (YYYY-MM-DD HH:MMZ) {step}
- [ ] {step} (completed: X; remaining: Y)

## Surprises & Discoveries
- **Observation:** {what you found}
  **Evidence:** {log output or error}
  **Resolution:** {how handled}

## Decision Log
- **Decision:** {what}
  **Rationale:** {why}
  **Alternatives:** {what else}
  **Date:** {YYYY-MM-DD}

## Outcomes & Retrospective
- {what worked}
- {what to change next time}
- {what the next phase should know}

## Purpose / Big Picture
{2-3 sentences: what changes in user-visible behavior}

## Context and Orientation
- Current state
- Key files by full path
- Define any jargon

## Plan of Work
{Prose sequence: file, function/class, change}

## Concrete Steps
1) {command}
   Expected: {short output}

## Validation and Acceptance
- Run: {command}
- Expected: {observable outcome}

## Idempotence and Recovery
- Safe to repeat.
- Resume from first unchecked Progress item.

## Interfaces and Dependencies
- {APIs, types, services, versions}
```

## Execution Behavior
- Run preflight first and log results.
- After each step, run the declared test tier.
- If tests fail, classify with ENV-DRIFT and fix (max 2 attempts).
- If the same error repeats twice, invoke STALEMATE.
