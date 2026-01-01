# ExecPlan: Complete Phase 3 + Phase 4 Smoke Tests

**Phase:** 3-4 Bridge
**Created:** 2025-01-01
**Author:** Claude (Spec Steward)
**Status:** COMPLETE

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries, 
Decision Log, and Outcomes & Retrospective MUST be updated as work proceeds.

Reference: This document follows `.agent/PLANS.md` protocol.

---

## Purpose / Big Picture

After this work:
1. **Phase 3 is COMPLETE**: n8n can trigger APEG's SEO update API with full verification (TEST-N8N-03 passes)
2. **Phase 4 smoke tests pass**: Meta API and Shopify attribution tests execute successfully (or document credential requirements)
3. **Phase 0 parity verified**: Environment variables are aligned between .env.example and active .env

The user will be able to trigger n8n workflows that execute Shopify bulk mutations and collect metrics data.

---

## Progress

- [x] (2026-01-01 05:58Z) Verify baseline: `PYTHONPATH=. ./venv/bin/python -m pytest tests/unit/ -v` (44 passed)
- [x] (2025-01-01 04:55Z) Fixed test_poll_status_completed: lock reference was cleared after release
- [x] (2025-01-01 04:58Z) Fixed unawaited coroutine warnings: raise_for_status is sync, not async
- [x] (2026-01-01 05:58Z) Phase 0: Complete environment parity check (FAIL: 21 missing keys, 4 extra keys in .env)
- [x] (2026-01-01 06:44Z) Phase 0: Environment parity recheck PASS (missing 0 keys; extra keys documented)
- [x] (2026-01-01 06:44Z) Started APEG server for Phase 3 testing (uvicorn PID 46628, logs in /tmp/uvicorn.log)
- [x] (2026-01-01 06:44Z) Ran API auth pre-checks (missing key -> "Invalid API key"; valid key + correct domain -> "products must be non-empty")
- [x] (2026-01-01 07:18Z) Phase 3: Execute TEST-N8N-03 (PASS: job completed, bulk op `gid://shopify/BulkOperation/4412960243814`)
- [x] (2026-01-01 07:16Z) Installed Redis and verified `redis-cli ping` returns PONG
- [x] (2026-01-01 06:44Z) Phase 4: Run TEST-META-01 (SKIPPED: no data returned for test date)
- [x] (2026-01-01 06:44Z) Phase 4: Run TEST-SHOPIFY-01 (SKIPPED: no orders found in test date range)
- [x] (2026-01-01 06:51Z) Phase 4: Run TEST-COLLECTOR-01 (PASS: counts unchanged on re-run)
- [x] (2026-01-01 07:05Z) Update ACCEPTANCE_TESTS.md with evidence (completed: TEST-ENV-01, TEST-META-01, TEST-SHOPIFY-01, TEST-COLLECTOR-01, TEST-N8N-03)
- [x] (2026-01-01 07:23Z) Update PROJECT_PLAN_ACTIVE.md with completion status (Phase 3 + Phase 4 status notes)
- [x] (2026-01-01 07:23Z) Run full test suite: `PYTHONPATH=. ./venv/bin/python -m pytest -v` (52 passed, 2 skipped)
- [x] (2026-01-01 08:38Z) Step 1 re-run: `PYTHONPATH=. pytest tests/unit/ -v` (44 passed) after async client fix
- [x] (2026-01-01 08:39Z) Step 2 parity check: .env.example=30 keys, .env=37 keys; missing 0; extra 7; APEG_API_KEY valid
- [x] (2026-01-01 08:41Z) Step 3: Started uvicorn (PID 63436; logs `/tmp/uvicorn.log`), but localhost connections blocked in sandbox; stopped server
- [x] (2026-01-01 08:41Z) Step 4: API auth pre-checks via `httpx.AsyncClient` + `ASGITransport` (401 missing key, 400 domain mismatch, 400 empty products)
- [~] (2026-01-01 08:42Z) Step 5: TEST-N8N-03 skipped (n8n not available in sandbox; localhost networking blocked)
- [x] (2026-01-01 08:42Z) Step 6: Smoke tests executed; both SKIPPED (credentials unset in sandbox)
- [x] (2026-01-01 08:43Z) Step 7: Collector idempotency re-run (credentials unset); counts unchanged for 2025-12-30
- [x] (2026-01-01 08:45Z) Step 8: Documentation updated (ACCEPTANCE_TESTS.md, PROJECT_PLAN_ACTIVE.md) with sandbox evidence

---

## Surprises & Discoveries

- **Observation:** test_poll_status_completed failed with AttributeError: 'NoneType' object has no attribute 'release'
  **Evidence:** The test asserted `bulk_client._current_lock.release.called` but `_release_lock_best_effort()` sets `_current_lock = None` after releasing (correct behavior)
  **Resolution:** Capture mock lock reference before calling poll_status, assert on captured reference

- **Observation:** 5 RuntimeWarnings about unawaited coroutines for `raise_for_status()`
  **Evidence:** `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited` on line 309 of bulk_client.py
  **Resolution:** Added `mock_response.raise_for_status = MagicMock()` to all affected tests (aiohttp's raise_for_status is sync, not async)

- **Observation:** Ubuntu 24.04 uses PEP 668 externally-managed Python
  **Evidence:** `pip install` fails with "externally-managed-environment" even inside .venv when using system pip
  **Resolution:** Use `python -m pip install` or ensure venv pip is in PATH first

- **Observation:** .env previously missed 21 keys from .env.example and had 4 extra keys
  **Evidence:** `comm` comparison showed missing FEEDBACK_*, METRICS_*, STRATEGY_TAG_CATALOG; extras included APEG_API_BASE_URL, APEG_API_HOST, DEMO_STORE_DOMAIN_ALLOWLIST, META_APP_ID
  **Resolution:** .env updated; parity now PASS (0 missing keys, 7 extra keys documented)

- **Observation:** Missing API key returns "Invalid API key" instead of "header missing"
  **Evidence:** `curl` to `/api/v1/jobs/seo-update` without `X-APEG-API-KEY` returned `{"detail":"Invalid API key"}`
  **Resolution:** Noted behavior; update expectations in ExecPlan Step 4 actuals

- **Observation:** Phase 4 smoke tests skipped due to no data/orders for test date range
  **Evidence:** pytest skip reasons: "No data returned for test date (no ad spend)" and "No orders found in test date range"
  **Resolution:** Recorded as SKIPPED in ACCEPTANCE_TESTS.md; proceed with idempotency check

- **Observation:** Background job failed during TEST-N8N-03 due to Redis connection refused
  **Evidence:** `Error 111 connecting to localhost:6379. Connection refused.` in `/tmp/uvicorn.log` for run_id `n8n-manual-test-01`
  **Resolution:** Rerun TEST-N8N-03 after Redis is available

- **Observation:** Redis service and CLI are not installed on this host
  **Evidence:** `Failed to start redis-server.service: Unit redis-server.service not found`, `/bin/bash: redis-server: command not found`, `/bin/bash: redis-cli: command not found`
  **Resolution:** Installed `redis-server` + `redis-tools`; `redis-cli ping` returns PONG (2026-01-01 07:16Z)

- **Observation:** Full pytest run initially failed due to duplicate module name `test_bulk_client_mock`
  **Evidence:** pytest import mismatch between `tests/test_bulk_client_mock.py` and `tests/unit/test_bulk_client_mock.py`
  **Resolution:** Added `tests/__init__.py` and `tests/unit/__init__.py` to give unique module names

- **Observation:** FastAPI TestClient requests hung under Python 3.13/anyio (blocking portal never returned)
  **Evidence:** `pytest tests/unit/ -v` timed out on API route tests; minimal anyio `start_blocking_portal()` call hung
  **Resolution:** Switched API route tests to `httpx.AsyncClient` + `ASGITransport` with `pytest_asyncio.fixture`

- **Observation:** Localhost networking is blocked in this sandbox (curl to 127.0.0.1:8000 failed)
  **Evidence:** `curl: (7) Failed to connect to 127.0.0.1 port 8000` while uvicorn was running
  **Resolution:** Performed API auth pre-checks using in-process `httpx.AsyncClient` + `ASGITransport`

---

## Decision Log

- **Decision:** Fix test assertions to use captured mock references instead of instance attributes
  **Rationale:** When implementation correctly clears state after use (e.g., `_current_lock = None`), tests must capture references before the operation
  **Alternatives Considered:** Modifying implementation to not clear lock (rejected: clearing is correct behavior)
  **Date:** 2025-01-01

- **Decision:** Add `raise_for_status = MagicMock()` to all AsyncMock responses
  **Rationale:** aiohttp's `raise_for_status()` is synchronous, but AsyncMock makes all methods return coroutines by default
  **Alternatives Considered:** Using spec= parameter (rejected: more complex for minimal benefit)
  **Date:** 2025-01-01

- **Decision:** Add `__init__.py` markers to `tests/` and `tests/unit/` for pytest import disambiguation
  **Rationale:** Duplicate filenames across test directories caused import mismatch during full test runs
  **Alternatives Considered:** Renaming or deleting a test file (rejected: avoid altering/deleting tests)
  **Date:** 2026-01-01

- **Decision:** Replace FastAPI TestClient with `httpx.AsyncClient` in API route tests
  **Rationale:** AnyIO blocking portal hangs under Python 3.13, preventing TestClient requests from returning
  **Alternatives Considered:** Pin/downgrade anyio/httpx, switch to Python 3.11 (rejected: environment fixed)
  **Date:** 2026-01-01

- **Decision:** Use `ASGITransport` for API pre-checks instead of curl
  **Rationale:** Sandbox blocks localhost networking, so in-process requests are the only reliable option
  **Alternatives Considered:** Keep uvicorn running and retry curl (rejected: repeated connection failures)
  **Date:** 2026-01-01

---

## Outcomes & Retrospective

- What worked well? Execution checklist kept parity, smoke tests, and idempotency evidence aligned with ACCEPTANCE_TESTS.md.
- What would you do differently? Align TEST-N8N numbering between ExecPlan and ACCEPTANCE_TESTS earlier to reduce ambiguity.
- What should the next phase know? Phase 4 smoke tests were executed but SKIPPED due to no data/orders; rerun when real data exists.

---

## Context and Orientation

### Current Project State

APEG is an e-commerce automation system in Phase 3-4 transition:

| Phase | Status | Blocking Items |
|-------|--------|----------------|
| 0 | ✅ Parity PASS | None |
| 1-2 | ✅ Complete | None |
| 3 | ✅ Complete | None |
| 4 | ⚠️ Smoke tests SKIPPED | No ad spend/orders in test date range |
| 5 | 🔲 Blocked | Requires Phase 4 data |

### Key Files

```
src/apeg_core/api/routes.py          # POST /api/v1/jobs/seo-update endpoint
src/apeg_core/api/auth.py            # X-APEG-API-KEY validation
src/apeg_core/metrics/collector.py   # Daily metrics orchestrator
tests/smoke/test_meta_api.py         # Meta API field validation
tests/smoke/test_shopify_attribution.py  # Shopify attribution validation
docs/ACCEPTANCE_TESTS.md             # Evidence log (update this)
docs/PROJECT_PLAN_ACTIVE.md          # Phase checklist (update this)
.env.example                         # Canonical template
```

### Terminology

- **TEST-N8N-03**: Acceptance test proving n8n can trigger APEG API and a background job executes
- **Environment Parity Check**: Verify .env has all keys from .env.example with valid values
- **Smoke Test**: Lightweight API validation proving credentials work and expected fields exist
- **Safe Tag Merge**: Fetch existing tags → union → subtract → write (never overwrites)

---

## Plan of Work

### Milestone 1: Environment Parity (Phase 0 completion)

1. Compare `.env.example` against active `.env` file
2. Verify APEG_API_KEY is set (not placeholder)
3. Record TEST-ENV-01 PASS/FAIL in ACCEPTANCE_TESTS.md

### Milestone 2: Phase 3 TEST-N8N-03

1. Start APEG server: `uvicorn src.apeg_core.main:app --reload`
2. Configure n8n HTTP Request node with correct credentials
3. Trigger workflow with test payload
4. Verify:
   - HTTP 202 response received
   - Background job appears in logs
   - (If dry_run=false) Shopify bulk operation completes
5. Record evidence in ACCEPTANCE_TESTS.md

### Milestone 3: Phase 4 Smoke Tests

1. Run `tests/smoke/test_meta_api.py` with valid META_ACCESS_TOKEN
2. Run `tests/smoke/test_shopify_attribution.py` with valid Shopify credentials
3. Document which fields are available/unavailable
4. If credentials missing, document as BLOCKED with requirements

### Milestone 4: Documentation Update

1. Update ACCEPTANCE_TESTS.md with all test evidence
2. Update PROJECT_PLAN_ACTIVE.md checkboxes
3. Update CHANGELOG.md if any spec changes discovered

---

## Concrete Steps

### Step 1: Verify Baseline

```bash
cd /path/to/APEG
PYTHONPATH=. pytest tests/unit/ -v
```

**Expected:** All tests pass (check current count in pytest output)

**Actual:** PASSED (2026-01-01 05:58Z) — `PYTHONPATH=. ./venv/bin/python -m pytest tests/unit/ -v` (44 passed)

---

### Step 2: Environment Parity Check (TEST-ENV-01)

```bash
# List all keys in .env.example
grep -E "^[A-Z_]+=" .env.example | cut -d= -f1 | sort > /tmp/example_keys.txt

# List all keys in .env (if exists)
grep -E "^[A-Z_]+=" .env 2>/dev/null | cut -d= -f1 | sort > /tmp/env_keys.txt

# Compare
diff /tmp/example_keys.txt /tmp/env_keys.txt
```

**Expected:** No diff (or only additional keys in .env)

**Actual:** PASS (2026-01-01 06:44Z) — missing 0 keys; extra 7 keys in .env
Extra: APEG_API_BASE_URL, APEG_API_HOST, APEG_API_PORT, DEMO_STORE_DOMAIN_ALLOWLIST, META_APP_ID, TEST_PRODUCT_ID, TEST_TAG_PREFIX

**Critical Check:**
```bash
grep "APEG_API_KEY" .env
```
**Expected:** `APEG_API_KEY=<some-non-placeholder-value>`
**NOT Expected:** `APEG_API_KEY=your-secret-api-key-here`
**Actual:** `APEG_API_KEY` is set to a non-placeholder value (VALID)

**Record in ACCEPTANCE_TESTS.md:**
```markdown
### TEST-ENV-01: Environment Parity Check
**Date:** [YYYY-MM-DD HH:MM]
**Status:** PASS / FAIL
**Evidence:**
- .env.example keys: [count]
- .env keys: [count]
- Missing keys: [list or "none"]
- APEG_API_KEY: [VALID / PLACEHOLDER]
```

---

### Step 3: Start APEG Server

```bash
PYTHONPATH=. uvicorn src.apeg_core.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected:** 
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
```

**Actual:** (2026-01-01 06:44Z) Started via `PYTHONPATH=. ./venv/bin/python -m uvicorn ...` (PID 46628)
```
INFO:     Started server process [46628]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Keep this terminal open for subsequent tests.**

---

### Step 4: Test API Authentication (Pre-check)

```bash
# Test with no API key (expect 401)
curl -X POST http://localhost:8000/api/v1/jobs/seo-update \
  -H "Content-Type: application/json" \
  -d '{"run_id": "test", "shop_domain": "test.myshopify.com", "products": []}'
```

**Expected:** `{"detail":"X-APEG-API-KEY header missing"}`

**Actual:** (2026-01-01 06:44Z) `{"detail":"Invalid API key"}`

```bash
# Test with valid API key (expect 400 for empty products)
curl -X POST http://localhost:8000/api/v1/jobs/seo-update \
  -H "Content-Type: application/json" \
  -H "X-APEG-API-KEY: $(grep APEG_API_KEY .env | cut -d= -f2)" \
  -d '{"run_id": "test", "shop_domain": "test.myshopify.com", "products": []}'
```

**Expected:** `{"detail":"products must be non-empty"}`

**Actual:** (2026-01-01 06:44Z)
- With `shop_domain="test.myshopify.com"`: `{"detail":"shop_domain mismatch: expected 'kfmah5-gr.myshopify.com', got 'test.myshopify.com'"}`
- With `shop_domain=$SHOPIFY_STORE_DOMAIN`: `{"detail":"products must be non-empty"}`

---

### Step 5: TEST-N8N-03 (Live Execution)

**Prerequisites:**
- n8n running and accessible
- HTTP Request credential configured per `docs/N8N_WORKFLOW_CONFIG.md`
- APEG server running (Step 3)

**Test Payload:**
```json
{
  "run_id": "n8n-test-001",
  "shop_domain": "<YOUR_SHOPIFY_STORE_DOMAIN>",
  "products": [
    {
      "product_id": "gid://shopify/Product/<REAL_PRODUCT_ID>",
      "tags_add": ["apeg_phase3_test"],
      "tags_remove": [],
      "seo": null
    }
  ],
  "dry_run": true
}
```

**Execution:**
1. In n8n, create/open the SEO update workflow
2. Configure HTTP Request node:
   - Method: POST
   - URL: `http://<APEG_HOST>:8000/api/v1/jobs/seo-update`
   - Authentication: Header Auth (X-APEG-API-KEY)
   - Body: JSON (above payload)
3. Execute workflow

**Expected Response:**
```json
{
  "job_id": "<uuid>",
  "status": "queued",
  "run_id": "n8n-test-001",
  "received_count": 1
}
```

**Status:** PASS (2026-01-01 07:18Z) — job completed; bulk op `gid://shopify/BulkOperation/4412960243814`

**Actual Response (n8n):**
```json
[
  {
    "job_id": "c7dd52cd-54e5-402e-8b81-d9d0275405f2",
    "status": "queued",
    "run_id": "n8n-manual-test-01",
    "received_count": 1
  }
]
```

**APEG Logs:**
```
2026-01-01 07:17:43,259 [INFO] src.apeg_core.api.routes: Queued SEO update job: job_id=c7dd52cd-54e5-402e-8b81-d9d0275405f2, run_id=n8n-manual-test-01, products_count=1
2026-01-01 07:17:43,260 [INFO] src.apeg_core.api.routes: Starting SEO update job: job_id=c7dd52cd-54e5-402e-8b81-d9d0275405f2, run_id=n8n-manual-test-01, products=1, dry_run=False
2026-01-01 07:17:43,272 [INFO] src.apeg_core.shopify.bulk_mutation_client: Acquired mutation lock: run_id=n8n-manual-test-01
2026-01-01 07:17:46,836 [INFO] src.apeg_core.shopify.bulk_mutation_client: Submitted bulk mutation: op_id=gid://shopify/BulkOperation/4412960243814, run_id=n8n-manual-test-01, updates=1
2026-01-01 07:17:52,096 [INFO] src.apeg_core.api.routes: Job c7dd52cd-54e5-402e-8b81-d9d0275405f2 completed successfully: bulk_op=gid://shopify/BulkOperation/4412960243814, objects=1
```

**Evidence Location:** `docs/ACCEPTANCE_TESTS.md` → `TEST-N8N-05`

**Verify in APEG logs:**
```
INFO: Queued SEO update job: job_id=<uuid>, run_id=n8n-test-001, products_count=1
INFO: Starting SEO update job: job_id=<uuid>, run_id=n8n-test-001, products=1, dry_run=True
INFO: DRY RUN MODE: Would update 1 products
INFO: Job <uuid> completed (dry run)
```

**Record in ACCEPTANCE_TESTS.md:**
```markdown
### TEST-N8N-03: Live Execution
**Date:** [YYYY-MM-DD HH:MM]
**Status:** PASS / FAIL
**Evidence:**
- n8n response: [paste response JSON]
- APEG log entries: [paste relevant log lines]
- Background job completed: YES / NO
```

---

### Step 6: Phase 4 Smoke Tests

```bash
# Set credentials in environment (or ensure .env is loaded)
export META_ACCESS_TOKEN="<your-token>"
export META_AD_ACCOUNT_ID="act_<your-id>"

# Run Meta API smoke test
PYTHONPATH=. pytest tests/smoke/test_meta_api.py -v
```

**Expected (if credentials valid):** Test passes, shows available fields

**Expected (if credentials invalid/missing):**
```
SKIPPED: META_ACCESS_TOKEN not configured
```

**Actual:** (2026-01-01 06:44Z) SKIPPED — `No data returned for test date (no ad spend)`

```bash
# Run Shopify attribution smoke test
PYTHONPATH=. pytest tests/smoke/test_shopify_attribution.py -v
```

**Expected:** Test passes or shows specific field availability

**Actual:** (2026-01-01 06:44Z) SKIPPED — `No orders found in test date range`

**Record in ACCEPTANCE_TESTS.md:**
```markdown
### TEST-META-01: Meta API Fields
**Date:** [YYYY-MM-DD HH:MM]
**Status:** PASS / FAIL / BLOCKED
**Evidence:**
[paste pytest output]

### TEST-SHOPIFY-01: Shopify Attribution
**Date:** [YYYY-MM-DD HH:MM]
**Status:** PASS / FAIL / BLOCKED
**Evidence:**
[paste pytest output]
```

---

### Step 7: TEST-COLLECTOR-01 (Idempotency)

```bash
PYTHONPATH=. python scripts/run_metrics_collector.py --date 2025-12-30 -v
sqlite3 data/metrics.db "SELECT COUNT(*) FROM metrics_meta_daily WHERE metric_date='2025-12-30';"
sqlite3 data/metrics.db "SELECT COUNT(*) FROM order_attributions WHERE created_at LIKE '2025-12-30%';"
sqlite3 data/metrics.db "SELECT metric_date, source_name, status FROM collector_state WHERE metric_date='2025-12-30' ORDER BY source_name;"

# Re-run for idempotency
PYTHONPATH=. python scripts/run_metrics_collector.py --date 2025-12-30 -v
sqlite3 data/metrics.db "SELECT COUNT(*) FROM metrics_meta_daily WHERE metric_date='2025-12-30';"
sqlite3 data/metrics.db "SELECT COUNT(*) FROM order_attributions WHERE created_at LIKE '2025-12-30%';"
sqlite3 data/metrics.db "SELECT metric_date, source_name, status FROM collector_state WHERE metric_date='2025-12-30' ORDER BY source_name;"
```

**Expected:** Counts unchanged; one success row per source in collector_state.

**Actual:** (2026-01-01 06:51Z)
- metrics_meta_daily count: 3 → 3
- order_attributions count: 4 → 4
- collector_state: `2025-12-30|meta|success`, `2025-12-30|shopify|success`

---

### Step 8: Update Documentation

Edit `docs/ACCEPTANCE_TESTS.md`:
- Fill in evidence for each test executed
- Mark status as PASS/FAIL/BLOCKED

Edit `docs/PROJECT_PLAN_ACTIVE.md`:
- Check completed items with `[X] Done <date>`
- Update phase status

Edit `docs/CHANGELOG.md` (if needed):
- Add entry for any discoveries or fixes

---

## Validation and Acceptance

**Phase 0 Complete when:**
- [x] TEST-ENV-01 shows PASS in ACCEPTANCE_TESTS.md
- [x] All .env.example keys exist in active .env

**Phase 3 Complete when:**
- [x] TEST-N8N-01, TEST-N8N-02, TEST-N8N-03 all PASS
- [x] Evidence recorded in ACCEPTANCE_TESTS.md
- [x] PROJECT_PLAN_ACTIVE shows Phase 3 items checked

**Phase 4 Smoke Tests Complete when:**
- [x] TEST-META-01 executed (PASS or BLOCKED with documented reason)
- [x] TEST-SHOPIFY-01 executed (PASS or BLOCKED with documented reason)
- [x] Evidence recorded in ACCEPTANCE_TESTS.md

---

## Idempotence and Recovery

All steps are safe to repeat:
- API calls are read-only or use dry_run=true
- Smoke tests only validate, don't mutate
- Documentation updates are additive

If interrupted:
1. Check Progress section for last completed step
2. Run `PYTHONPATH=. pytest tests/unit/ -v` to verify baseline
3. Resume from next unchecked item

---

## Interfaces and Dependencies

**No new code required** — this ExecPlan executes existing code.

**Required Credentials (for full execution):**
- `APEG_API_KEY` — for API authentication
- `SHOPIFY_STORE_DOMAIN` — target store
- `SHOPIFY_ADMIN_ACCESS_TOKEN` — Shopify API access
- `META_ACCESS_TOKEN` — for Phase 4 smoke tests (optional)
- `META_AD_ACCOUNT_ID` — for Phase 4 smoke tests (optional)

**External Services:**
- Redis (for bulk operation locks)
- n8n (for TEST-N8N-03)
- Shopify Admin API
- Meta Marketing API (optional for smoke tests)

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2025-01-01 | Claude | Initial creation |
| 2026-01-01 | Codex | Executed Phase 0/3/4 steps, captured evidence, updated project plan |
