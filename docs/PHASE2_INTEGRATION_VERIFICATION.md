# Phase 2 Integration Test Verification (Post Schema Fix)

## Prereqs
- Schema fix applied (groupObjects removed)
- DEMO store credentials in `.env`
- Redis running on localhost:6379
- Dependencies installed: `python -m pip install -r requirements.txt`

## Run
```bash
# Verify clean codebase
rg -n "groupObjects|\$groupObjects" src/apeg_core/ || echo "✓ Code clean"

# Load environment
set -a; source .env; set +a

# Verify environment
echo "Store: $SHOPIFY_STORE_DOMAIN"
echo "Env: $APEG_ENV (must be DEMO)"
echo "Writes: $APEG_ALLOW_WRITES (must be YES)"

# Start Redis if needed
docker ps | grep redis || docker run -d -p 6379:6379 redis:7-alpine

# Run integration test
PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py
```

## Expected PASS Signals

- "PASS: Safe write preserved all original tags"
- "PASS: New tag '<tag>' successfully added"
- "PASS: Staged upload dance completed (no 403/400 errors)"
- "PASS: ALL INTEGRATION TESTS PASSED"

### Success Pattern
```
[INFO] ✓ Safety gates passed: DEMO-only mode confirmed
[INFO] Starting SEO update job...
[INFO] Fetching current state for 1 products
[INFO] Submitting bulk mutation for 1 products
[INFO] Bulk operation submitted: gid://shopify/BulkOperation/...
[INFO] ✓ Bulk operation completed: objects=1
[INFO] ================================================
[INFO] SCENARIO 1: Safe Tag Merge (Preserve Original Tags)
[INFO] ================================================
[INFO] Initial tags: ['original-tag-1', 'original-tag-2']
[INFO] Adding new tag: apeg_safe_write_test_20241230123456
[INFO] ✓ Bulk operation completed: 1 objects
[INFO] Final tags: ['apeg_safe_write_test_20241230123456', 'original-tag-1', 'original-tag-2']
[INFO] ✓ PASS: Safe write preserved all original tags
[INFO] ✓ PASS: New tag 'apeg_safe_write_test_20241230123456' successfully added
[INFO] ================================================
[INFO] SCENARIO 2: Staged Upload Dance
[INFO] ================================================
[INFO] ✓ PASS: Staged upload dance completed (no 403/400 errors)
[INFO] ================================================
[INFO] ✓ ALL INTEGRATION TESTS PASSED
[INFO] ================================================
Exit code: 0
```

### Failure Patterns to Watch For

**Schema Error (Not Fixed):**
```
ShopifyBulkGraphQLError: GraphQL root errors: Field 'groupObjects' doesn't exist...
```
→ Code still contains groupObjects; rerun verification sweep

**Authentication Error:**
```
ShopifyBulkGraphQLError: GraphQL root errors: Access denied...
```
→ Check SHOPIFY_ADMIN_ACCESS_TOKEN in .env

**Lock Error:**
```
ShopifyBulkMutationLockedError: Bulk mutation lock already held...
```
→ Another job running or stale lock; check Redis: `redis-cli KEYS "apeg:*"`

## Post-Success Actions

1. Update `docs/PROJECT_PLAN_ACTIVE.md`:
```markdown
- [X] Done 12.30: Schema fix verified (groupObjects removed, integration test green)
```

2. Update `docs/ACCEPTANCE_TESTS.md`:
```markdown
**Status:** VERIFIED (integration test passed 12.30)
```

3. Commit verification:
```bash
git add docs/
git commit -m "docs: phase 2 schema fix verified (integration test green)"
```

4. Unblock Phase 3 development
