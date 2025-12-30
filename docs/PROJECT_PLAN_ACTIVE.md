# PROJECT_PLAN_ACTIVE.md
# EcomAgent + APEG Execution Plan

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2025-12-29  
**Current Phase:** PHASE 0

---
## RETAIN FORMAT DO NOT RESTRUCTURE
## PHASE 0 — CONFIG + CUTOVER READINESS ⬅️ ACTIVE

**Spec Anchors:** Section 1.8, Appendix F, Security section

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| `.env.example` (no secrets) | [ ] | 1.8 |
| `ENVIRONMENT.md` | [ ] | 1.8, Appendix F |
| Config loader + validation | [ ] | 1.8 |
| Secrets via env/secret store only | [ ] | 1.8 |

**Acceptance Tests:**
- [ ] Shopify auth smoke: `{ shop { name } }` returns store name
- [ ] Meta token debug: valid + required scopes
- [ ] n8n credential mapping verified (demo credential ID documented)

---

## PHASE 1 — DETERMINISTIC SHOPIFY BACKBONE

**Spec Anchors:** Section 5.6, Section 5.10, Section 2.4.2

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| BulkJob model (id, type, status, shop_domain) | [ ] | 5.6 |
| Distributed lock (1 query + 1 mutation per shop) | [ ] | 5.10 |
| Poller: `node(id:) ... on BulkOperation` | [ ] | 5.6 |
| Staged upload wrapper (hard gate on failure) | [ ] | 5.5 |

**Acceptance Tests (VERIFIED in Stage 2):**
- [x] Bulk query → COMPLETED via node(id:) polling
- [x] Bulk mutation → COMPLETED via staged upload path
- [x] Upload hard-gate: non-2xx prevents runMutation
- [x] Tag merge preserves existing tags

---

## PHASE 2 — SHOPIFY MUSCLE LAYER (SAFE WRITES)

**Spec Anchors:** Section 2.4.2, product update rules

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| Tag hydration tool (fetch → union → update) | [ ] | 2.4.2 |
| SEO update tool (ProductInput.seo) | [ ] | 2.3 |
| Audit logging for all writes | [ ] | 9.x |

**Acceptance Tests:**
- [ ] Write ops in DEMO with rollback plan
- [ ] Audit log captures before/after state

---

## PHASE 3 — N8N ORCHESTRATION BINDINGS

**Spec Anchors:** Section 8.13, workflow triggers

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| Webhook contract (trigger endpoints) | [ ] | 8.13 |
| Credential-ID swap checklist | [ ] | 8.13 |
| Execution log verification | [ ] | 8.13 |

**Acceptance Tests:**
- [ ] Workflow run in DEMO produces correct outputs
- [ ] Post-swap: LIVE credential in execution log

---

## PHASE 4 — META ADS MINIMUM DEPLOYMENT

**Spec Anchors:** Section 6.12, Meta config

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| Meta connector (token debug, account read) | [ ] | 6.12 |
| PAUSED campaign create path | [ ] | 6.12 |
| Rate limit + error code handling | [ ] | 6.11 |

**Acceptance Tests:**
- [ ] Token debug PASS
- [ ] Ad account read PASS
- [ ] Create PAUSED campaign (optional)

---

## PHASE 5 — HARDENING + CI/CD

**Spec Anchors:** Appendix D (CI), license scan

| Deliverable | Status | Spec Section |
|-------------|--------|--------------|
| CI workflows (tests + license scan) | [ ] | Appendix D |
| Coverage gate | [ ] | Appendix D |
| GPL denylist enforcement | [ ] | Section 1.7 |

**Acceptance Tests:**
- [ ] CI green on PR
- [ ] License scan green (no GPL in prod deps)

---

## LIVE SWAP CHECKLIST

See Appendix F in spec. Execute only when:
- [ ] All Phase 0-3 acceptance tests PASS in DEMO
- [ ] Smoke tests documented in ACCEPTANCE_TESTS.md
- [ ] Credential swap procedure rehearsed

---

## AGENT ALIGNMENT RULE

Every PR must reference:
1. Spec section(s)
2. Phase item
3. Acceptance test(s)

If test contradicts spec → patch spec first via CHANGELOG, then code.
