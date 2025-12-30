# Phase 2 Integration Test Plan: Bulk Mutations & Safe Write

## Prerequisites
- Real Shopify store (DEMO environment)
- `.env` configured with valid credentials
- Redis instance running
- Test products with known IDs and tags

## Test Scenarios

### INT-TEST-01: Staged Upload Dance (End-to-End)
**Objective:** Verify 4-step staged upload workflow completes successfully.

**Steps:**
1. Create 10 ProductUpdateInput with test tags
2. Call `run_product_update_bulk()`
3. Verify bulk operation ID returned
4. Call `poll_and_get_result()` until COMPLETED
5. Download result JSONL from `operation.url`
6. Parse JSONL and verify product IDs match input

**Success Criteria:**
- All 10 products updated successfully
- No userErrors in result JSONL
- Mutation lock released after completion

### INT-TEST-02: Safe Tag Hydration (Read-Merge-Write)
**Objective:** Verify tags are not overwritten; union merge works.

**Steps:**
1. Manually set tags on test product: `["original-tag-1", "original-tag-2"]`
2. Call `fetch_current_product_state()` for that product
3. Verify returned tags match `["original-tag-1", "original-tag-2"]`
4. Create ProductUpdateInput with `tags=["new-tag"]`
5. Call `merge_product_updates(current_state_map, [update])`
6. Verify merged tags = `["new-tag", "original-tag-1", "original-tag-2"]`
7. Submit bulk mutation with merged tags
8. Poll until complete
9. Fetch product again via Shopify Admin API
10. Verify final tags contain all 3 tags

**Success Criteria:**
- Original tags preserved
- New tag added
- No tags lost

### INT-TEST-03: Multipart Upload Ordering Validation
**Objective:** Verify file field is LAST in multipart form (prevents 403 errors).

**Steps:**
1. Enable aiohttp request logging
2. Run `run_product_update_bulk()` with 1 product
3. Inspect HTTP traffic logs
4. Verify multipart boundary order: parameters first, file field last

**Success Criteria:**
- HTTP 204 from staged upload POST
- No 403/400 errors
- Logs show file field appended after all parameters

### INT-TEST-04: Lock Contention Handling
**Objective:** Verify second mutation fails fast when lock held.

**Steps:**
1. Start bulk mutation (do not await completion)
2. Immediately attempt second `run_product_update_bulk()`
3. Verify ShopifyBulkMutationLockedError raised
4. Verify error message contains shop_domain and lock_key

**Success Criteria:**
- Second mutation raises ShopifyBulkMutationLockedError
- First mutation continues unaffected
- Lock released after first mutation completes

## Deferred Tests (Require Live PROD Data)
- Large-scale mutation (1000+ products)
- Partial data recovery (FAILED status with partialDataUrl)
- Network timeout during staged upload
