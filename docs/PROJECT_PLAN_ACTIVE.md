# PROJECT_PLAN_ACTIVE.md
# EcomAgent + APEG Execution Plan

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2025-12-29  
**Current Phase:** PHASE 0

---
## RETAIN FORMAT DO NOT RESTRUCTURE
## PHASE 0 — CONFIG + CUTOVER READINESS ⬅️ ACTIVE

**Spec Anchors:** Section 1.8, Appendix F, Security section

### PHASE 0: Documentation Baseline

- [X] Done 12.30: Documentation baseline corrections (spec v1.4.1 + safety locks + env standardization)

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| `.env.example` (no secrets) | [ ] ToDo: | 1.8 |
| `ENVIRONMENT.md` | [ ] ToDo: | 1.8, Appendix F |
| Config loader + validation | [ ] ToDo: | 1.8 |
| Secrets via env/secret store only | [ ] ToDo: | 1.8 |

**Acceptance Tests:**
- [ ] ToDo: Shopify auth smoke: `{ shop { name } }` returns store name
- [ ] ToDo: Meta token debug: valid + required scopes
- [ ] ToDo: n8n credential mapping verified (demo credential ID documented)

## PHASE 0 — EXECUTABLE START PLAN

- [ ] ToDo: Confirm Shopify app creation path (Dev Dashboard required for new apps after 2026-01-01; existing legacy custom apps unaffected).
- [ ] ToDo: Update `.env.example` with any new required keys (no secrets).
- [ ] ToDo: Create `.env` only if missing.
- [ ] ToDo: If `.env` exists and must be changed, run backup first:
```bash
      cp .env .env.bak.$(date +%Y%m%d-%H%M%S)
```
- [ ] ToDo: Run Shopify auth smoke test (GraphQL: { shop { name } }) and paste evidence into ACCEPTANCE_TESTS.
- [ ] ToDo: Record n8n credential IDs (DEMO) and paste evidence into ACCEPTANCE_TESTS.
- [ ] ToDo: Decide Meta timing:
    - If Phase 4 planned in next sprint: run token debug now and paste evidence into ACCEPTANCE_TESTS.
    - Else: mark Meta token debug as DEFERRED in PROJECT_PLAN_ACTIVE and ACCEPTANCE_TESTS.

---

## PHASE 1 — DETERMINISTIC SHOPIFY BACKBONE

**Spec Anchors:** Section 5.6, Section 5.10, Section 2.4.2

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| BulkJob model (id, type, status, shop_domain) | [ ] ToDo: | 5.6 |
| Distributed lock (1 query + 1 mutation per shop) | [ ] ToDo: | 5.10 |
| Poller: `node(id:) ... on BulkOperation` | [ ] ToDo: | 5.6 |
| Staged upload wrapper (hard gate on failure) | [ ] ToDo: | 5.5 |

**Acceptance Tests (VERIFIED in Stage 2):**
- [X] Done 12.29: Bulk query → COMPLETED via node(id:) polling
- [X] Done 12.29: Bulk mutation → COMPLETED via staged upload path
- [X] Done 12.29: Upload hard-gate: non-2xx prevents runMutation
- [X] Done 12.29: Tag merge preserves existing tags

---

### PHASE 1: Core Async Engine

- [X] Done 12.30: Shopify Bulk Client (schemas + async client + Redis locks + tests)
- [ ] ToDo: JSONL Parser (async streaming from Shopify bulk result URLs)
- [ ] ToDo: Integration Tests (real Shopify API + Redis, gated by .env credentials)

## PHASE 2 — SHOPIFY MUSCLE LAYER (SAFE WRITES)

### PHASE 2: Bulk Mutations & Safe Write (VERIFIED - Integration PASS 12.30)

- [X] Done 12.30: Bulk Mutation Client (staged upload + safe tag merge + unit tests)
- [X] Done 12.30: verify_phase2_safe_writes.py PASS (safe write + staged upload + cleanup)
- [ ] ToDo: Error recovery patterns (partialDataUrl handling)

**Spec Anchors:** Section 2.4.2, product update rules

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| Tag hydration tool (fetch → union → update) | [ ] ToDo: | 2.4.2 |
| SEO update tool (ProductInput.seo) | [ ] ToDo: | 2.3 |
| Audit logging for all writes | [ ] ToDo: | 9.x |

**Acceptance Tests:**
- [ ] ToDo: Write ops in DEMO with rollback plan
- [ ] ToDo: Audit log captures before/after state

---

## PHASE 3 — N8N ORCHESTRATION BINDINGS

**Spec Anchors:** Section 8.13, workflow triggers

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| Webhook contract (trigger endpoints) | [ ] ToDo: | 8.13 |
| Credential-ID swap checklist | [ ] ToDo: | 8.13 |
| Execution log verification | [ ] ToDo: | 8.13 |

**Acceptance Tests:**
- [ ] ToDo: Workflow run in DEMO produces correct outputs
- [ ] ToDo: Post-swap: LIVE credential in execution log

---

## PHASE 4 — META ADS MINIMUM DEPLOYMENT

**Spec Anchors:** Section 6.12, Meta config

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| Meta connector (token debug, account read) | [ ] ToDo: | 6.12 |
| PAUSED campaign create path | [ ] ToDo: | 6.12 |
| Rate limit + error code handling | [ ] ToDo: | 6.11 |

**Acceptance Tests:**
- [ ] ToDo: Token debug PASS
- [ ] ToDo: Ad account read PASS
- [ ] ToDo: Create PAUSED campaign (optional)

---

## PHASE 5 — HARDENING + CI/CD

**Spec Anchors:** Appendix D (CI), license scan

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| CI workflows (tests + license scan) | [ ] ToDo: | Appendix D |
| Coverage gate | [ ] ToDo: | Appendix D |
| GPL denylist enforcement | [ ] ToDo: | Section 1.7 |

**Acceptance Tests:**
- [ ] ToDo: CI green on PR
- [ ] ToDo: License scan green (no GPL in prod deps)

---

## LIVE SWAP CHECKLIST

See Appendix F in spec. Execute only when:
- [ ] ToDo: All Phase 0-3 acceptance tests PASS in DEMO
- [ ] ToDo: Smoke tests documented in ACCEPTANCE_TESTS.md
- [ ] ToDo: Credential swap procedure rehearsed

---

## AGENT ALIGNMENT RULE

Every PR must reference:
1. Spec section(s)
2. Phase item
3. Acceptance test(s)

If test contradicts spec → patch spec first via CHANGELOG, then code.
