# ACCEPTANCE_TESTS.md
# Spec → Test Mapping

**Source of Truth:** integration-architecture-spec-v1.4.md  
**Last Updated:** 2025-12-29

---

## PHASE 0 — Configuration & Preconditions

| Test ID | Test Name | Spec Section | Method | Expected | Actual | Status | Evidence |
|---------|-----------|--------------|--------|----------|--------|--------|----------|
|  | Shopify auth: `{ shop { name } }` | 1.8, Appendix F |  |  |  | REQUIRED |  |
|  | Meta token debug valid | 1.8, 6.12 |  |  |  | REQUIRED |  |
|  | n8n credential ID documented | 8.13 |  |  |  | REQUIRED |  |
| AT-P0-LEGACY-APP-01 | Legacy custom app creation constraints | Section 1.7 | Research validation | New apps after 2026-01-01 require Shopify Dev Dashboard; existing legacy apps unaffected | Matches expected | VERIFIED | Stage 2 Research Log |
| AT-P0-CJ-ATTRIBUTION-01 | CustomerJourney attribution window semantics | Section 7 | Research validation | CustomerJourney uses a 30-day attribution window (not data retention); non-build-gating | Matches expected | VERIFIED | Stage 2 Research Log |

---

## PHASE 1 — Shopify Backbone (Stage 2 VERIFIED)

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| `bulkOperations(...)` absent from QueryRoot | 5.6 | ✓ VERIFIED | "Field 'bulkOperations' doesn't exist" |
| `node(id:)` polling works | 5.6 | ✓ VERIFIED | Returns BulkOperation with status |
| Sequential bulk query lock | 5.10 | ✓ VERIFIED | "already in progress" error on concurrent |
| Bulk query → COMPLETED | 5.6 | ✓ VERIFIED | Dev-store test |
| Bulk mutation → COMPLETED | 5.5 | ✓ VERIFIED | Staged upload + runMutation |
| Upload hard-gate (non-2xx blocks) | 5.5 | ✓ VERIFIED | "JSONL file could not be found" |
| stagedUploadPath rejects local paths | 5.5 | ✓ VERIFIED | /tmp path rejected |
| Tag merge preserves existing | 2.4.2 | ✓ VERIFIED | Pre-existing tags preserved |

---

## PHASE 2 — Safe Writes

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| Tag hydration (fetch→union→update) | 2.4.2 | REQUIRED | |
| SEO update via ProductInput.seo | 2.3 | REQUIRED | |
| Audit log before/after | 9.x | REQUIRED | |
| Rollback procedure tested | Appendix F | REQUIRED | |

---

## PHASE 3 — n8n Orchestration

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| Webhook trigger works | 8.13 | REQUIRED | |
| DEMO workflow execution | 8.13 | REQUIRED | |
| Credential swap verified | 8.13 | REQUIRED | Execution log shows LIVE |

---

## PHASE 4 — Meta Ads

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| Token debug valid + scopes | 6.12 | REQUIRED | |
| Ad account read | 6.12 | REQUIRED | |
| PAUSED campaign create | 6.12 | OPTIONAL | |
| Interest ID lookup | 6.4 | REQUIRED | |

---

## PHASE 5 — CI/CD

| Test | Spec Section | Status | Evidence |
|------|--------------|--------|----------|
| CI green on PR | Appendix D | REQUIRED | |
| License scan green | Appendix D | REQUIRED | No GPL in prod |
| Coverage gate | Appendix D | REQUIRED | |

---

## LIVE SWAP (Appendix F)

| Test | Status | Blocker |
|------|--------|---------|
| Shopify auth | REQUIRED | YES |
| Bulk query end-to-end | REQUIRED | YES |
| Bulk mutation end-to-end | REQUIRED | YES |
| Tag merge | REQUIRED | YES |
| Webhook HMAC | REQUIRED | YES |
| Meta token (if immediate) | REQUIRED | If Meta |
| n8n credential swap | REQUIRED | YES |

---

## Evidence Log

### Stage 2 (2025-12-29)

**bulkOperations absent:**
```
Error: "Field 'bulkOperations' doesn't exist on type 'QueryRoot'"
API Version: 2025-10
```

**Concurrent query blocked:**
```
Error: "A bulk query operation for this app and shop is already in progress: gid://shopify/BulkOperation/XXXXX"
```

**Staged upload path rejection:**
```
Error: bulkOperationRunMutation rejected /tmp path, expects Shopify bucket bulk/ path
```

**Tag merge verified:**
```
Before: ["existing-tag-1", "existing-tag-2"]
After productUpdate: ["new-tag-1", "existing-tag-1", "existing-tag-2"]
Result: All pre-existing tags preserved
```
