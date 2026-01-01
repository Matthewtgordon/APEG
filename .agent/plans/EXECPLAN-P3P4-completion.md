# ExecPlan: Complete Phase 3 + Phase 4 Smoke Tests

**Phase:** 3-4 Bridge
**Created:** 2025-01-01
**Author:** Claude (Spec Steward)
**Status:** READY_FOR_EXECUTION

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

- [x] (2025-01-01 04:50Z) Verify baseline: discovered 1 failing test + 5 warnings
- [x] (2025-01-01 04:55Z) Fixed test_poll_status_completed: lock reference was cleared after release
- [x] (2025-01-01 04:58Z) Fixed unawaited coroutine warnings: raise_for_status is sync, not async
- [ ] (pending) Phase 0: Complete environment parity check
- [ ] (pending) Phase 3: Execute TEST-N8N-03 (live execution with background job proof)
- [ ] (pending) Phase 4: Run TEST-META-01 (Meta API smoke test)
- [ ] (pending) Phase 4: Run TEST-SHOPIFY-01 (Shopify attribution smoke test)
- [ ] (pending) Phase 4: Run TEST-COLLECTOR-01 (idempotency test)
- [ ] (pending) Update ACCEPTANCE_TESTS.md with evidence
- [ ] (pending) Update PROJECT_PLAN_ACTIVE.md with completion status

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

---

## Outcomes & Retrospective

(Update at completion)

---

## Context and Orientation

### Current Project State

APEG is an e-commerce automation system in Phase 3-4 transition:

| Phase | Status | Blocking Items |
|-------|--------|----------------|
| 0 | ⚠️ Parity pending | TEST-ENV-01 evidence needed |
| 1-2 | ✅ Complete | None |
| 3 | ⚠️ Near complete | TEST-N8N-03 (live execution) |
| 4 | ⚠️ Code complete | Smoke tests need credentials |
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

**Actual:** [FILL IN AFTER RUNNING]

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

**Critical Check:**
```bash
grep "APEG_API_KEY" .env
```
**Expected:** `APEG_API_KEY=<some-non-placeholder-value>`
**NOT Expected:** `APEG_API_KEY=your-secret-api-key-here`

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

```bash
# Test with valid API key (expect 400 for empty products)
curl -X POST http://localhost:8000/api/v1/jobs/seo-update \
  -H "Content-Type: application/json" \
  -H "X-APEG-API-KEY: $(grep APEG_API_KEY .env | cut -d= -f2)" \
  -d '{"run_id": "test", "shop_domain": "test.myshopify.com", "products": []}'
```

**Expected:** `{"detail":"products must be non-empty"}`

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

```bash
# Run Shopify attribution smoke test
PYTHONPATH=. pytest tests/smoke/test_shopify_attribution.py -v
```

**Expected:** Test passes or shows specific field availability

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

### Step 7: Update Documentation

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
- [ ] TEST-ENV-01 shows PASS in ACCEPTANCE_TESTS.md
- [ ] All .env.example keys exist in active .env

**Phase 3 Complete when:**
- [ ] TEST-N8N-01, TEST-N8N-02, TEST-N8N-03 all PASS
- [ ] Evidence recorded in ACCEPTANCE_TESTS.md
- [ ] PROJECT_PLAN_ACTIVE shows Phase 3 items checked

**Phase 4 Smoke Tests Complete when:**
- [ ] TEST-META-01 executed (PASS or BLOCKED with documented reason)
- [ ] TEST-SHOPIFY-01 executed (PASS or BLOCKED with documented reason)
- [ ] Evidence recorded in ACCEPTANCE_TESTS.md

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