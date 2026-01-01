# AGENTS.md — APEG Project Context Anchor
# Version: 1.0.0 | Last Updated: 2025-01-01
# Purpose: Static context for AI coding agents (Codex, Claude Code)

## Project Overview

**APEG** (Async Product Enhancement Gateway) is an e-commerce automation system that orchestrates SEO optimization and advertising campaigns across Shopify and Etsy platforms.

| Attribute | Value |
|-----------|-------|
| Runtime | Python 3.11+ on ARM64 (Raspberry Pi 5) + x86 (Cloud VM) |
| Architecture | FastAPI async master + sync worker pattern |
| Primary Store | Shopify (GraphQL Bulk Operations) |
| Orchestration | n8n workflows via HTTP triggers |
| Concurrency | Redis distributed locks (1 bulk op per shop) |
| Current Phase | Phase 3-5 (SEO API + Metrics + Feedback Loop) |

---

## Critical Invariants (NEVER Violate)

### 🚫 Licensing
```
NEVER import GPL/LGPL/AGPL dependencies into src/apeg_core/
BLOCKED: etsyv3 library (GPL-3.0) — must isolate in separate microservice
PERMITTED: MIT, Apache-2.0, BSD, ISC
VERIFY: pip-licenses --fail-on="GPL;LGPL;AGPL"
```

### 🚫 Shopify Bulk Operations Concurrency
```
NEVER run bulk operations in parallel
CONSTRAINT: 1 query + 1 mutation per shop at any time
ENFORCE: Redis lock with key "shopify:bulk:{shop_domain}"
POLL: Use node(id:) query — NOT deprecated bulkOperations query
EVIDENCE: "already in progress" error confirms sequential enforcement
```

### 🚫 Async Architecture Preservation
```
NEVER call blocking I/O from async context without wrapper
NEVER rewrite EcomAgent (sync) — wrap it instead
PATTERN: await asyncio.to_thread(sync_function, *args)
WRAPPER LOCATION: Integration points in src/apeg_core/api/routes.py
```

### 🚫 Safe Write Pattern
```
NEVER overwrite Shopify product tags directly
ALWAYS: Fetch current → Merge in memory → Push update
FORMULA: new_tags = (current_tags ∪ tags_add) - tags_remove
VERIFIED: Stage 2 tests confirm tag preservation
```

---

## Commands

### Virtual Environment (REQUIRED FIRST)
```bash
# ALWAYS activate venv before running any Python commands
# Ubuntu 24.04+ uses PEP 668 externally-managed Python
cd /path/to/APEG
source .venv/bin/activate      # Or: . .venv/bin/activate

# Verify you're in venv (prompt should show (.venv))
which python                    # Should show: /path/to/APEG/.venv/bin/python
```

### Test Execution
```bash
# ALWAYS run from project root with PYTHONPATH (venv must be active)
PYTHONPATH=. pytest -v                          # All tests
PYTHONPATH=. pytest tests/unit/ -v              # Unit tests only
PYTHONPATH=. pytest tests/integration/ -v       # Integration (requires Redis + .env)
PYTHONPATH=. pytest tests/smoke/ -v             # Smoke tests (requires API credentials)
PYTHONPATH=. pytest -m "not integration" -v     # Skip integration tests
```

### Linting & Type Checking
```bash
ruff check src/                                  # Lint source
ruff check tests/                                # Lint tests
mypy src/ --ignore-missing-imports              # Type check (optional)
```

### Development Server
```bash
PYTHONPATH=. uvicorn src.apeg_core.main:app --reload --host 0.0.0.0 --port 8000
```

### Phase-Specific Scripts
```bash
PYTHONPATH=. python scripts/run_metrics_collector.py --date 2025-01-01 -v
PYTHONPATH=. python scripts/run_feedback_loop.py --mode analyze -v
PYTHONPATH=. python scripts/seed_dummy_data.py
```

---

## Project Structure

```
APEG/
├── .agent/                      # Agent context files (this directory)
│   ├── AGENTS.md               # ← You are here (static context)
│   └── PLANS.md                # ExecPlan protocol definition
├── .env.example                # Canonical environment template (NEVER commit secrets)
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Test configuration
│
├── src/apeg_core/              # Main application package
│   ├── main.py                 # FastAPI app entry point
│   ├── api/                    # HTTP endpoints
│   │   ├── auth.py             # X-APEG-API-KEY validation
│   │   └── routes.py           # POST /api/v1/jobs/seo-update
│   ├── shopify/                # Shopify integration layer
│   │   ├── bulk_client.py      # Async bulk query client + Redis locks
│   │   ├── bulk_mutation_client.py  # Staged upload + safe tag merge
│   │   ├── exceptions.py       # Custom exception hierarchy
│   │   └── graphql_strings.py  # Canonical GraphQL queries/mutations
│   ├── schemas/                # Pydantic models
│   │   └── bulk_ops.py         # BulkOperation, ProductUpdateSpec, etc.
│   ├── metrics/                # Phase 4: Data collection
│   │   ├── schema.py           # SQLite schema (metrics_meta_daily, etc.)
│   │   ├── collector.py        # Daily orchestrator
│   │   ├── meta_collector.py   # Meta Marketing API client
│   │   ├── shopify_collector.py # Shopify orders + attribution
│   │   └── attribution.py      # 3-tier waterfall algorithm
│   └── feedback/               # Phase 5: Refinement engine
│       ├── schema.py           # seo_versions, feedback_runs tables
│       ├── analyzer.py         # Diagnosis matrix + candidate selection
│       ├── version_control.py  # Champion/Challenger snapshots
│       ├── mapping.py          # strategy_tag resolution
│       └── prompts.py          # LLM prompt builders
│
├── tests/
│   ├── unit/                   # Mocked tests (no external deps)
│   ├── integration/            # Requires Redis + .env credentials
│   │   └── verify_phase2_safe_writes.py  # Shopify API integration
│   └── smoke/                  # API field validation tests
│
├── scripts/                    # CLI entry points
│   ├── run_metrics_collector.py
│   ├── run_feedback_loop.py
│   └── seed_dummy_data.py
│
├── data/
│   └── metrics/
│       └── strategy_tags.json  # Strategy tag catalog
│
├── docs/                       # Documentation
│   ├── PROJECT_PLAN_ACTIVE.md  # Phase tracking (source of truth)
│   ├── ACCEPTANCE_TESTS.md     # Test evidence log
│   ├── CHANGELOG.md            # Spec fixes + evidence
│   ├── integration-architecture-spec-v1.4.1.md  # Master spec
│   └── N8N_WORKFLOW_CONFIG.md  # n8n setup guide
│
└── infra/                      # Infrastructure (future)
    └── n8n/
        └── workflows/          # Exported workflow JSON files
```

---

## Boundaries

### ✅ ALWAYS (Do without asking)
- Run full test suite before marking any task complete
- Update Progress section in active ExecPlan after each step
- Use `PYTHONPATH=.` prefix for all Python commands
- Verify tests pass BEFORE and AFTER changes
- Check root `["errors"]` before accessing `["data"]` in GraphQL responses

### ⚠️ ASK FIRST (Pause and document reasoning)
- Adding new dependencies to requirements.txt
- Modifying database schema (SQLite tables)
- Changing bulk operation sequencing logic
- Modifying `.env.example` structure
- Creating new API endpoints

### 🚫 NEVER (Hard constraints)
- Delete existing tests
- Commit secrets or credentials
- Bypass Redis lock for "performance optimization"
- Import GPL-licensed packages into apeg_core
- Run bulk operations without waiting for COMPLETED status
- Call blocking I/O without asyncio.to_thread wrapper

---

## Testing Requirements

| Test Type | Location | Command | External Deps |
|-----------|----------|---------|---------------|
| Unit | `tests/unit/` | `pytest tests/unit/ -v` | None (mocked) |
| Integration | `tests/integration/` | `pytest tests/integration/ -v` | Redis, .env |
| Smoke | `tests/smoke/` | `pytest tests/smoke/ -v` | API credentials |

### Test Evidence Pattern
Every implementation must include:
1. Unit test with mocked dependencies
2. Evidence in ACCEPTANCE_TESTS.md with test output
3. For API changes: curl/httpie command + response

---

## Environment Variables (Key Subset)

```bash
# Required for all operations
APEG_API_KEY=<generated-secret>        # API authentication
APEG_ENV=DEMO                          # Safety gate (DEMO|LIVE)
APEG_ALLOW_WRITES=NO                   # Write protection

# Shopify
SHOPIFY_STORE_DOMAIN=store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_xxx
SHOPIFY_API_VERSION=2024-10

# Redis
REDIS_URL=redis://localhost:6379

# Metrics (Phase 4)
METRICS_DB_PATH=data/metrics.db
META_ACCESS_TOKEN=xxx
META_AD_ACCOUNT_ID=act_xxx
```

---

## Git Workflow

```bash
# Branch naming
feature/phase-{N}-{description}
fix/issue-{description}

# Commit format
[Phase N] <imperative verb> <what changed>
# Example: [Phase 3] Add n8n HTTP Request credential setup

# PR requirements
1. Reference spec section(s)
2. Reference phase item from PROJECT_PLAN_ACTIVE.md
3. Link acceptance test(s) in ACCEPTANCE_TESTS.md
4. All tests passing (CI green)
```

---

## Quick Reference: Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 0 | Config + Cutover | ⚠️ Parity check pending |
| 1 | Shopify Backbone | ✅ Complete |
| 2 | Bulk Mutations | ✅ Complete |
| 3 | n8n Orchestration | ⚠️ TEST-N8N-03 pending |
| 4 | Metrics Collection | ⚠️ Smoke tests blocked (credentials) |
| 5 | Feedback Loop | ⚠️ LLM integration pending |
| 6 | CI/CD Hardening | 🔲 Not started |

---

## ExecPlan Protocol

When implementing complex features, create an ExecPlan following `.agent/PLANS.md`.

Trigger phrases:
- "Implement Phase X"
- "Complete the remaining items in PROJECT_PLAN_ACTIVE"
- "Create an execution plan for..."

The ExecPlan becomes the living document that tracks progress, decisions, and verification.