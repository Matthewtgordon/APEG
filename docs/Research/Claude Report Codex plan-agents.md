# Bootstrap Files for Autonomous AI Coding Agents

OpenAI Codex and similar AI coding agents can execute multi-hour tasks autonomously when given properly structured documentation. The key lies in **two complementary files**: AGENTS.md for static project context and PLANS.md as a living execution protocol that agents update as they work. For your APEG e-commerce system, these files must encode project-specific invariants (no GPL, sequential bulk ops, asyncio.to_thread patterns) while enabling context recovery after any interruption.

## The AGENTS.md specification creates a "README for machines"

AGENTS.md has emerged as an open, vendor-neutral standard now adopted by over **60,000 open-source projects** and stewarded by the Linux Foundation's Agentic AI Foundation. Unlike human-focused READMEs, AGENTS.md provides structured instructions that coding agents parse for relevant context. The standard is deliberately simple—plain Markdown with semantic headings, no required fields, maximum flexibility.

The file discovery follows a hierarchical pattern: agents check the current working directory first, then traverse parent directories to the repo root, with closer files taking precedence. This enables monorepos to have package-specific overrides while maintaining global conventions.

Research analyzing **2,500+ repositories** identified six core sections that effective AGENTS.md files include:

| Section | Purpose for Agents |
|---------|-------------------|
| **Commands** | Executable build/test/lint commands with exact flags |
| **Testing** | How to run tests, what framework, where test files live |
| **Project Structure** | Folder layout, key file locations by full path |
| **Code Style** | Concrete examples over explanations |
| **Git Workflow** | Branch naming, commit format, PR requirements |
| **Boundaries** | Three-tier DO/ASK/NEVER constraints |

The critical insight: **keep files under 150 lines**. Research shows frontier LLMs reliably follow only ~150-200 instructions before uniform degradation occurs across all instruction-following. Longer files bury the signal that matters most.

## ExecPlans enable multi-hour autonomous execution

The breakthrough pattern for sustained autonomous work comes from OpenAI's Aaron Friel, who developed **ExecPlans**—design documents enabling Codex sessions exceeding 7 hours from a single prompt. The methodology rests on one non-negotiable principle: *treat the reader as a complete beginner who has only the current working tree and the ExecPlan file*.

Every ExecPlan contains four **mandatory living sections** that agents must update continuously:

```markdown
## Progress
- [x] (2025-01-15 10:30Z) Created Redis lock wrapper
- [ ] Implement bulk operation retry logic (started: error handling; remaining: backoff)

## Surprises & Discoveries
- Observation: Shopify rate limits hit at 2 requests/second, not 4
  Evidence: 429 responses in logs at timestamp X

## Decision Log
- Decision: Use exponential backoff with jitter
  Rationale: Prevents thundering herd on rate limit recovery
  Date: 2025-01-15

## Outcomes & Retrospective
Bulk ops now retry correctly. Learned: always test rate limits with production credentials.
```

The Progress section uses **timestamped checkboxes** that agents update at every stopping point. Partial progress is explicitly marked: `(completed: X; remaining: Y)`. This creates recovery points—if an agent loses context mid-session, it can resume by reading the ExecPlan alone.

Each milestone must be **independently verifiable**: clear acceptance criteria, exact commands to run, and expected output transcripts for comparison. The pattern "Run `pytest tests/integration/` and expect 12 passed; the new test `test_bulk_operation_lock` fails before and passes after" gives agents unambiguous success criteria.

## Context anchors prevent the "amnesia problem"

When agents lose context—whether from session timeout, compaction, or new conversation—they need structured anchors to resume work. Anthropic's engineering team recommends a **two-file approach**: a progress tracker (like `claude-progress.txt`) plus a feature checklist in **JSON format** rather than Markdown.

The JSON recommendation addresses a subtle failure mode: models are less likely to inappropriately modify structured JSON than Markdown prose. Feature tracking becomes more reliable:

```json
{
  "phase": 2,
  "feature": "shopify_bulk_inventory_sync",
  "status": "in_progress",
  "last_verified": "2025-01-15T10:30:00Z",
  "blocking_issues": null,
  "verification_steps": [
    "Run pytest tests/integration/test_bulk_ops.py",
    "Verify Redis lock acquired in logs",
    "Confirm sequential execution via timestamps"
  ]
}
```

Every agent session should start with a standardized **orientation protocol**: check working directory, read progress files, review git logs, run the init script, and verify existing functionality works before implementing new features. This prevents the common failure where agents assume a broken state is correct and build on top of it.

The Git Context Controller (GCC) research introduces version-control semantics for agent memory: agents can "commit" progress checkpoints, "branch" for experimental approaches, and "merge" successful explorations back to the main execution path. Each commit stores three layers: branch purpose, cumulative progress summary, and detailed current contribution.

## Invariants require prominent placement and explicit verification

The most dangerous anti-pattern is buried constraints that fade from context during long sessions. For APEG's specific requirements, invariants must appear in **prominent, early sections** with explicit "NEVER" framing:

```markdown
## Critical Invariants (NEVER Violate)

### Licensing
🚫 **NEVER** add GPL/LGPL/AGPL-licensed dependencies
✅ MIT, Apache 2.0, BSD permitted

### Shopify Bulk Operations
🚫 **NEVER** run bulk operations in parallel
✅ Sequential execution only—one bulk op must complete before next starts
✅ Use Redis distributed locks to enforce sequencing

### Async Architecture  
🚫 **NEVER** call sync code directly from async context
✅ Wrap ALL blocking operations: `await asyncio.to_thread(sync_function)`
✅ Use `async with` for database sessions

### Execution Environment
✅ ALWAYS run with PYTHONPATH=. from project root
✅ ALWAYS use `pytest -v` for tests, never plain `python`
```

The three-tier boundary system (DO/ASK/NEVER) provides graduated guidance. "Ask first" items—like database schema changes or adding dependencies—create natural checkpoints where agents should pause and document their reasoning rather than proceeding autonomously.

Invariant checking works best when paired with **machine verification before human review**. Generated code should pass linters, type checkers, and schema validators before being considered for merge. For APEG: run `ruff check`, validate Pydantic models, and execute the test suite with coverage thresholds.

## Verification must prove code works, not just compiles

The critical insight from Anthropic's research: Claude tends to mark features as complete without proper testing. Explicit prompting for **end-to-end verification** dramatically improved outcomes. For your pytest-based test suite:

```markdown
## Verification Protocol

### Before ANY implementation
1. Run existing test suite: `PYTHONPATH=. pytest -v`
2. Confirm baseline: all tests pass before changes
3. Note test count for regression checking

### After implementation
1. Unit tests: `pytest tests/unit/ -v --cov=src --cov-fail-under=80`
2. Integration tests: `pytest tests/integration/ -v`
3. Smoke tests: `pytest tests/smoke/ -v`
4. Verify test count increased (new functionality = new tests)

### Acceptance criteria format
- "Run `pytest tests/integration/test_bulk_ops.py::test_sequential_lock` 
   and observe: PASSED in output, Redis LOCK_ACQUIRED log line, 
   no concurrent bulk operation warnings"
```

For Shopify-specific verification, tests should mock the GraphQL Bulk Operations API and verify that operations execute sequentially even under concurrent requests. Integration tests should use a Redis test instance to confirm lock acquisition and release patterns.

## Living documents require structured update patterns

The ExecPlan methodology mandates that agents update documentation at every stopping point. But this creates a risk: verbose, unfocused updates that consume context without adding value. Structure the updates:

**Progress updates** use atomic, timestamped entries with clear completion status. Avoid narrative prose; prefer factual state changes:

```markdown
## Progress
- [x] (2025-01-15 14:00Z) Phase 2: Bulk ops infrastructure complete
- [x] (2025-01-15 14:30Z) Redis lock wrapper implemented in src/locks/distributed.py
- [ ] Bulk operation queue (blocked: need Shopify webhook verification first)
```

**Decision Log entries** capture the "why" that would otherwise be lost:

```markdown
## Decision Log
- Decision: Use Redis SETNX instead of Redlock algorithm
  Rationale: Single Redis instance; Redlock complexity not justified
  Alternatives considered: Redlock (rejected: multi-node not needed), 
                          PostgreSQL advisory locks (rejected: Redis already in stack)
  Date: 2025-01-15
```

**Surprises & Discoveries** prevent repeated debugging of the same issues across context resets:

```markdown
## Surprises & Discoveries
- Shopify Bulk Operation polling requires minimum 2-second intervals
  Evidence: 429 responses when polling faster
  Resolution: Added exponential backoff starting at 2s
```

## Anti-patterns that cause agent failure are predictable

Research across production deployments reveals consistent failure modes:

**Context window drift** occurs in sessions exceeding ~30 minutes. Early constraints fade as recent tokens dominate attention. The solution: force context resets for long tasks, periodically re-send critical constraints, and structure work into independently completable milestones.

**Silent tool failures cause hallucination cascades**. When file reads or API calls fail silently, agents fill gaps with plausible but fabricated content. For APEG, this manifests as invented function names or assumed API response structures. Always verify tool outputs before proceeding.

**Over-stuffed instruction files** cause uniform degradation. The ~150-200 instruction limit means every unnecessary instruction crowds out important ones. Keep AGENTS.md focused on universal project conventions; use progressive disclosure for task-specific context.

**Cascade failure pattern**: agents persist through errors, compounding damage. A malformed tool call deletes a file; seeing the empty file, the agent rewrites it with "beautiful nonsense"; creates tests for the wrong function; destroys existing tests; updates documentation incorrectly; announces completion. Prevention requires checkpoints and rollback capability.

**Implicit defaults** cause subtle bugs. Models assume "the most typical flag seen during training" for unspecified parameters—wrong AWS regions, deprecated API versions, incorrect pagination behavior. For APEG: explicitly specify Shopify API version, Redis connection patterns, and FastAPI settings.

## APEG-specific AGENTS.md template

Based on the research, here's a complete template for your e-commerce automation system:

```markdown
# APEG E-Commerce Automation

## Project Overview
FastAPI async backend integrating Shopify GraphQL Bulk Operations with Redis 
concurrency controls. Multi-phase implementation (Phase 0-6).

## Commands
- **Run all tests:** `PYTHONPATH=. pytest -v`
- **Unit tests only:** `PYTHONPATH=. pytest tests/unit/ -v`
- **Integration tests:** `PYTHONPATH=. pytest tests/integration/ -v`
- **Smoke tests:** `PYTHONPATH=. pytest tests/smoke/ -v`
- **Type checking:** `mypy src/`
- **Linting:** `ruff check src/`
- **Start dev server:** `PYTHONPATH=. uvicorn src.main:app --reload`

## Project Structure
```
src/
├── api/           # FastAPI route handlers (async)
├── services/      # Business logic layer
├── bulk_ops/      # Shopify Bulk Operation orchestration
├── locks/         # Redis distributed lock implementations
└── models/        # Pydantic models and schemas

tests/
├── unit/          # Isolated unit tests (mocked dependencies)
├── integration/   # Tests requiring Redis/external services
└── smoke/         # End-to-end verification tests
```

## Critical Invariants (NEVER Violate)

### Licensing
🚫 **NEVER** add GPL/LGPL/AGPL dependencies
✅ Permitted: MIT, Apache 2.0, BSD, ISC

### Bulk Operations
🚫 **NEVER** execute Shopify bulk operations in parallel
✅ Sequential only—wait for COMPLETED status before starting next
✅ Enforce via Redis distributed locks

### Async Architecture
🚫 **NEVER** call blocking code from async context without wrapper
✅ Use `await asyncio.to_thread(sync_func)` for ALL sync operations
✅ Use `async with` for resource management

### Execution
✅ ALWAYS run from project root with `PYTHONPATH=.`
✅ ALWAYS verify tests pass before AND after changes

## Code Style
- Type hints required on all function signatures
- Pydantic models for all API request/response schemas
- Async functions prefixed: `async def get_`, `async def create_`
- Sync wrappers in `utils/sync_bridge.py`

## Testing Requirements
- New functionality requires new tests
- Integration tests must verify Redis lock behavior
- Bulk operation tests must confirm sequential execution
- Mock Shopify API using `pytest-httpx` fixtures

## Boundaries
✅ **Always:** Run full test suite before marking complete
✅ **Always:** Update Progress section in active ExecPlan
⚠️ **Ask first:** Adding new dependencies
⚠️ **Ask first:** Database schema changes
⚠️ **Ask first:** Changes to bulk operation sequencing logic
🚫 **Never:** Delete existing tests
🚫 **Never:** Commit secrets or credentials
🚫 **Never:** Bypass the Redis lock for "performance"
```

## APEG-specific PLANS.md template

The ExecPlan for a specific phase:

```markdown
# Phase 2: Shopify Bulk Operations Infrastructure

This ExecPlan is a living document. Progress, Surprises, Decision Log, 
and Outcomes sections MUST be updated as work proceeds.

## Purpose / Big Picture
Enable reliable, sequential Shopify Bulk Operations for inventory sync. 
After this phase: system can queue bulk operations, execute them one at a time 
using Redis locks, poll for completion, and process results without data races.

## Progress
- [ ] Create Redis lock wrapper in src/locks/distributed.py
- [ ] Implement bulk operation queue in src/bulk_ops/queue.py
- [ ] Add polling mechanism with exponential backoff
- [ ] Write integration tests verifying sequential execution
- [ ] Update smoke tests to include bulk operation flow

## Surprises & Discoveries
(Document unexpected findings here as they occur)

## Decision Log
(Record every architectural or implementation decision with rationale)

## Outcomes & Retrospective
(Summarize at milestone completion)

## Context and Orientation
This is Phase 2 of 7. Phase 0-1 established FastAPI skeleton and Shopify 
auth. The bulk operation infrastructure will be used by Phase 3 (inventory 
sync) and Phase 4 (order fulfillment).

Key files:
- `src/shopify/client.py`: GraphQL client (exists)
- `src/locks/` directory: Create distributed.py here
- `src/bulk_ops/` directory: Create queue.py, processor.py

## Concrete Steps

### Step 1: Redis Lock Wrapper
```bash
# Verify Redis connection
redis-cli ping

# Create lock module
touch src/locks/__init__.py
touch src/locks/distributed.py
```

Expected structure in distributed.py:
```python
class DistributedLock:
    async def acquire(self, key: str, ttl: int = 300) -> bool: ...
    async def release(self, key: str) -> bool: ...
    async def __aenter__(self): ...
    async def __aexit__(self): ...
```

### Step 2: Bulk Operation Queue
(Continue with similar detail...)

## Validation and Acceptance

Run `PYTHONPATH=. pytest tests/integration/test_locks.py -v` 
Expect: 5 tests passed, including test_sequential_lock_enforcement

Run `PYTHONPATH=. pytest tests/integration/test_bulk_ops.py -v`
Expect: test_bulk_operations_execute_sequentially PASSED

Verify in test output: "Lock acquired for bulk_op_*" appears before 
"Lock released for bulk_op_*" for each operation.

## Idempotence and Recovery

All steps are idempotent. If interrupted:
1. Read this ExecPlan's Progress section
2. Run test suite to verify current state
3. Resume from first unchecked item

Rollback: `git reset --hard HEAD~1` if tests fail after changes.

## Interfaces and Dependencies
- redis-py: Async Redis client (already installed)
- src/shopify/client.py: GraphQL execution
- Pydantic models in src/models/bulk_ops.py (to be created)
```

## Synthesis: the autonomous execution protocol

Combining these patterns creates a protocol for multi-hour autonomous execution:

1. **Agent starts session** → reads AGENTS.md for project context
2. **Agent loads ExecPlan** → reads current phase PLANS.md for specific task
3. **Orientation check** → runs test suite to verify baseline state
4. **Execute with updates** → works through Concrete Steps, updating Progress after each
5. **Document decisions** → logs any choices made in Decision Log
6. **Record surprises** → notes unexpected behavior with evidence
7. **Verify completion** → runs acceptance criteria exactly as written
8. **Update retrospective** → summarizes outcomes for future context recovery

The critical enabler is **GPT-5.1-Codex-Max's compaction capability**: as context windows fill, the model prunes while preserving critical information. But compaction works best when living documents provide explicit, structured state—the Progress section survives compaction because it's marked as critical, while conversational context gets pruned.

For APEG's multi-phase project, create one ExecPlan per phase. Each phase's completion updates a master `phase_status.json` that tracks which phases are complete, which is active, and any cross-phase dependencies. This hierarchical structure enables both deep work within phases and recovery if an agent needs to understand the broader project state.