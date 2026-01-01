# PLANS.md — ExecPlan Protocol for APEG
# Version: 1.0.0 | Source: OpenAI Codex Cookbook + APEG adaptations

This document defines the **ExecPlan** format—a living design document that enables multi-hour autonomous execution. When implementing complex features or significant refactors, create an ExecPlan and update it continuously as work proceeds.

---

## When to Use an ExecPlan

Create an ExecPlan when:
- Implementing a new phase (Phase 0-6)
- Task requires >30 minutes of work
- Multiple files must be coordinated
- External API integration is involved
- User says "create an execution plan" or "implement Phase X"

Do NOT create an ExecPlan for:
- Single-file bug fixes
- Documentation-only updates
- Simple test additions

---

## Non-Negotiable Requirements

1. **Self-Contained**: The ExecPlan must contain ALL knowledge needed for a novice to succeed. Assume the reader has only the working tree and this file.

2. **Living Document**: Update Progress, Surprises, Decision Log, and Outcomes sections at EVERY stopping point.

3. **Verifiable Outcomes**: Every milestone must produce observable behavior, not just code changes.

4. **No External References**: Do not say "as described in the spec" or "see previous plan." Embed the needed information here.

5. **Timestamps**: Use ISO format timestamps (e.g., `2025-01-15 14:30Z`) in Progress section.

---

## ExecPlan Skeleton

Copy this template to `.agent/plans/EXECPLAN-{PHASE}-{DESCRIPTION}.md`:

```markdown
# ExecPlan: [Short, Action-Oriented Title]

**Phase:** [N]
**Created:** [YYYY-MM-DD]
**Author:** [Agent/Human]
**Status:** IN_PROGRESS | BLOCKED | COMPLETE

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries, 
Decision Log, and Outcomes & Retrospective MUST be updated as work proceeds.

Reference: This document follows `.agent/PLANS.md` protocol.

---

## Purpose / Big Picture

[2-3 sentences explaining what someone can do AFTER this work that they could not 
do BEFORE. State the user-visible behavior you will enable.]

Example for Phase 3:
> After this phase, n8n workflows can trigger APEG's SEO update API, which executes
> bulk Shopify mutations with safe tag merge. The API accepts product arrays and
> returns job IDs for tracking.

---

## Progress

Use checkboxes with timestamps. Update at EVERY stopping point.

- [x] (2025-01-15 10:00Z) Read existing codebase structure
- [x] (2025-01-15 10:30Z) Verified baseline tests pass (12/12)
- [ ] Create new endpoint in src/apeg_core/api/routes.py
- [ ] (started: schema defined; remaining: handler logic)

Split partially completed items: `(completed: X; remaining: Y)`

---

## Surprises & Discoveries

Document unexpected findings with evidence. This prevents re-debugging after context loss.

- **Observation:** [What you found]
  **Evidence:** [Log output, error message, or test result]
  **Resolution:** [How you addressed it, if applicable]

Example:
- **Observation:** Shopify rate limit hit at 2 req/sec, not documented 4 req/sec
  **Evidence:** HTTP 429 in logs at 2025-01-15 11:23:45
  **Resolution:** Added exponential backoff starting at 2s delay

---

## Decision Log

Record every decision with rationale. Future agents (or humans) need to know WHY.

- **Decision:** [What you decided]
  **Rationale:** [Why this choice over alternatives]
  **Alternatives Considered:** [What else you evaluated]
  **Date:** [YYYY-MM-DD]

Example:
- **Decision:** Use Redis SETNX instead of Redlock algorithm
  **Rationale:** Single Redis instance in current deployment; Redlock adds complexity without benefit
  **Alternatives Considered:** PostgreSQL advisory locks (rejected: Redis already in stack)
  **Date:** 2025-01-15

---

## Outcomes & Retrospective

Update at milestone completion. Compare result against original Purpose.

- What worked well?
- What would you do differently?
- What should the next phase know?

---

## Context and Orientation

Describe the current state as if reader knows NOTHING. Name key files by full path.

Example:
> This is Phase 3 of the APEG project. Phases 1-2 established the Shopify bulk 
> operation infrastructure in `src/apeg_core/shopify/`. This phase adds the FastAPI
> endpoint that n8n will call to trigger SEO updates.
>
> Key files:
> - `src/apeg_core/api/routes.py` — Existing endpoint skeleton (to be extended)
> - `src/apeg_core/schemas/bulk_ops.py` — ProductUpdateSpec model (exists)
> - `docs/PROJECT_PLAN_ACTIVE.md` — Phase 3 checklist items

Define any jargon:
> - **Safe tag merge:** Pattern where we fetch existing tags, union with new tags, 
>   subtract removed tags, then write back. Prevents overwriting.
> - **Staged upload:** Shopify's 4-step bulk mutation protocol: create upload URL → 
>   upload JSONL → trigger mutation → poll for completion.

---

## Plan of Work

Prose description of the sequence of edits. For each edit, name:
- File path
- Function/class to modify or create
- What to insert or change

Example:
> 1. Extend `src/apeg_core/api/routes.py` to add `POST /api/v1/jobs/seo-update`
>    - Add request model `SEOUpdateJobRequest` with `products: list[SEOUpdateProduct]`
>    - Add background task that calls `ShopifyBulkMutationClient`
>
> 2. Add unit tests in `tests/unit/test_api_routes.py`
>    - Test 401 on missing API key
>    - Test 202 on valid request
>    - Test 400 on empty products array

---

## Concrete Steps

Exact commands to run with expected output. Update as you execute.

### Step 1: Verify Baseline

```bash
cd /path/to/APEG
PYTHONPATH=. pytest tests/unit/ -v
```

Expected: `12 passed in 2.34s`

Actual: [FILL IN AFTER RUNNING]

### Step 2: Create New Endpoint

[File edits with context...]

### Step 3: Run New Tests

```bash
PYTHONPATH=. pytest tests/unit/test_api_routes.py -v
```

Expected: `15 passed` (3 new tests added)

Actual: [FILL IN AFTER RUNNING]

---

## Validation and Acceptance

How to prove this works. Phrase as observable behavior.

**Acceptance Criteria:**

1. Run `PYTHONPATH=. pytest tests/unit/test_api_routes.py::test_seo_update_returns_202 -v`
   - Expected: PASSED
   - Observe: Response status 202, job_id in body

2. Run `curl -X POST http://localhost:8000/api/v1/jobs/seo-update -H "X-APEG-API-KEY: test" -d '...'`
   - Expected: `{"job_id": "...", "status": "queued"}`

3. Check logs for: "Queued SEO update job: job_id=..."

---

## Idempotence and Recovery

All steps are safe to repeat. If interrupted:

1. Read this ExecPlan's Progress section
2. Run `PYTHONPATH=. pytest -v` to verify current state
3. Resume from first unchecked item in Progress

Rollback procedure:
```bash
git stash                    # Save uncommitted changes
git log --oneline -5         # Find last good commit
git reset --hard <commit>    # Restore to known state
```

---

## Interfaces and Dependencies

Be prescriptive. Name specific types and signatures.

**New Pydantic Models (src/apeg_core/schemas/):**

```python
class SEOUpdateProduct(BaseModel):
    product_id: str  # GID format: gid://shopify/Product/123
    tags_add: list[str] = []
    tags_remove: list[str] = []
    seo: Optional[ProductSEO] = None
```

**External Dependencies:**
- Redis (existing): Lock coordination
- aiohttp (existing): HTTP client for Shopify
- No new dependencies required

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2025-01-15 | Codex | Initial creation |
| 2025-01-15 | Codex | Updated after Step 2 completion |
```

---

## File Naming Convention

Store ExecPlans in `.agent/plans/`:

```
.agent/
├── AGENTS.md                              # Static context (this file's sibling)
├── PLANS.md                               # Protocol definition (this file)
└── plans/
    ├── EXECPLAN-P3-n8n-seo-endpoint.md   # Phase 3 work
    ├── EXECPLAN-P4-metrics-collector.md  # Phase 4 work
    └── EXECPLAN-P5-feedback-loop.md      # Phase 5 work
```

Naming format: `EXECPLAN-P{phase}-{kebab-description}.md`

---

## Progress Update Rules

1. **Timestamp every checkbox change**
   - Bad: `- [x] Created endpoint`
   - Good: `- [x] (2025-01-15 14:30Z) Created endpoint in routes.py`

2. **Split partial progress immediately**
   - Bad: `- [ ] Implement authentication` (no indication of partial work)
   - Good: `- [ ] Implement authentication (completed: decorator; remaining: token validation)`

3. **Never delete items** — Mark as skipped with reason if not needed
   - `- [~] (SKIPPED: Not needed per Decision Log entry 2025-01-15)`

4. **Add items as discovered** — Plans evolve; insert new items where logical

---

## Quality Gates

Before marking ExecPlan COMPLETE:

- [ ] All Progress items checked or explicitly skipped
- [ ] Surprises & Discoveries section has at least one entry (even if "None unexpected")
- [ ] Decision Log captures any non-trivial choices
- [ ] Outcomes section summarizes what was achieved
- [ ] All Validation/Acceptance criteria verified with actual output
- [ ] Tests pass: `PYTHONPATH=. pytest -v`
- [ ] No uncommitted changes: `git status` shows clean

---

## Anti-Patterns to Avoid

❌ **Vague progress entries**
```
- [x] Did the thing
```

✅ **Specific, verifiable entries**
```
- [x] (2025-01-15 14:30Z) Added POST /api/v1/jobs/seo-update endpoint in routes.py
```

---

❌ **External references without embedding**
```
See the architecture spec for details on bulk operations.
```

✅ **Embedded context**
```
Bulk operations use a 4-step "staged upload dance":
1. stagedUploadsCreate → get signed URL
2. Multipart POST JSONL to signed URL
3. bulkOperationRunMutation with stagedUploadPath
4. Poll via node(id:) until status=COMPLETED
```

---

❌ **Missing acceptance criteria**
```
The endpoint should work correctly.
```

✅ **Observable acceptance**
```
Run: curl -X POST ... -d '{"products": [...]}'
Expected: HTTP 202 with body {"job_id": "uuid", "status": "queued"}
Verify in logs: "Queued SEO update job: job_id=uuid"
```

---

## Integration with AGENTS.md

The ExecPlan inherits constraints from `.agent/AGENTS.md`:

- **Invariants** from AGENTS.md are automatically in scope
- **Commands** from AGENTS.md are the canonical test/lint/run commands
- **Boundaries** (DO/ASK/NEVER) apply to all ExecPlan work

If an ExecPlan requires violating an AGENTS.md constraint, you MUST:
1. Document in Decision Log with explicit rationale
2. Get human approval before proceeding
3. Update AGENTS.md if constraint is permanently changed

---

## Recovery Protocol

If context is lost (new session, timeout, compaction):

1. **Read** `.agent/AGENTS.md` for project context
2. **Find** active ExecPlan in `.agent/plans/`
3. **Check** Progress section for current state
4. **Run** `git status` to see uncommitted work
5. **Run** `PYTHONPATH=. pytest -v` to verify test state
6. **Resume** from first unchecked Progress item

The ExecPlan is designed to be the ONLY document needed for recovery.
