# Phase 2 Integration Tests

> **📍 Quick Links:** [Main README](../../README.md) | [Docs Index](../../docs/README.md) | [Environment Setup](../../docs/ENVIRONMENT.md) | [API Usage](../../docs/API_USAGE.md)

## 📋 Table of Contents

- [Purpose](#purpose)
- [Safety Gates](#safety-gates-all-required)
- [Environment Setup](#environment-setup)
- [Running Tests](#running-tests)
- [Test Scenarios](#test-scenarios)
- [Exit Codes](#exit-codes)
- [Cleanup Guarantee](#cleanup-guarantee)
- [Environment Variables](#environment-variables)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

---

## Purpose
Validates Phase 2 bulk mutations against a real Shopify DEMO store with enforced safety gates.

## Safety Gates (ALL REQUIRED)
The test script enforces three hard safety gates:

1. APEG_ENV=DEMO - Must be set to "DEMO" (refuses LIVE/PROD)
2. Store Allowlist - SHOPIFY_STORE_DOMAIN must be in DEMO_STORE_DOMAIN_ALLOWLIST
3. Explicit Write Confirmation - APEG_ALLOW_WRITES=YES must be set

The script exits with code 2 if any safety gate fails.

## Environment Setup

Template Source: `.env.example` is the canonical template for ALL environments.

IMPORTANT: Do NOT use `.env.integration.example` if it exists - it has been deprecated to prevent environment variable drift.

### Steps:

1. Copy the canonical template:
```bash
cp .env.example .env.integration
```

2. Configure APEG API credentials:
```bash
# Generate a random API key (user-defined secret)
APEG_API_KEY=$(openssl rand -hex 32)
echo "APEG_API_KEY=${APEG_API_KEY}" >> .env.integration
```

3. Configure DEMO Shopify credentials:
```bash
# Edit .env.integration and fill in:
SHOPIFY_STORE_DOMAIN=your-demo-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_your_demo_token
SHOPIFY_API_VERSION=2024-10
```

4. Enable write operations:
```bash
# Edit .env.integration and set:
APEG_ENV=DEMO
APEG_ALLOW_WRITES=YES
```

5. Uncomment and configure Integration Testing section:
```bash
# Edit .env.integration and uncomment:
DEMO_STORE_DOMAIN_ALLOWLIST=your-demo-store.myshopify.com
# TEST_PRODUCT_ID=gid://shopify/Product/1234567890  # Optional
# TEST_TAG_PREFIX=apeg_test_  # Optional
```

6. Source the environment:
```bash
set -a; source .env.integration; set +a
```

7. Run integration tests:
```bash
PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py
```

### Template Parity Rule

When adding new required variables:
1. Update `.env.example` FIRST
2. Regenerate your `.env.integration` from the updated template
3. This prevents \"works in one env, fails in another\" drift

### Troubleshooting

Error: \"APEG_API_KEY environment variable not configured\"
- Verify you sourced the .env.integration file
- Verify APEG_API_KEY exists in .env.integration and has a non-empty value
- Check for typos in variable name (case-sensitive)

## Running Tests

### Option 1: Direct Execution
```bash
# Load environment
set -a; source .env.integration; set +a

# Run integration tests
PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py
```

### Option 2: Using pytest
```bash
# Load environment
set -a; source .env.integration; set +a

# Run with pytest
PYTHONPATH=. pytest tests/integration/verify_phase2_safe_writes.py -v -s
```

## Test Scenarios

### Scenario 1: Safe Tag Merge (Read-Merge-Write)
- Fetches current product tags
- Generates unique test tag
- Submits bulk mutation with merged tags (current + new)
- Polls until COMPLETED
- Verifies:
  - New tag present
  - All original tags preserved

### Scenario 2: Staged Upload Dance (Implicit)
- Validated by Scenario 1 completing without 403/400 errors
- Confirms:
  - stagedUploadsCreate succeeded
  - Multipart upload succeeded
  - bulkOperationRunMutation succeeded
  - Bulk operation reached COMPLETED status

## Exit Codes
- 0: All tests passed
- 1: Test assertion failure or runtime error
- 2: Safety gate failure (env misconfiguration)

## Cleanup Guarantee
- If the script creates a test product, it MUST delete it (even on failure)
- Uses try/finally to guarantee cleanup
- If TEST_PRODUCT_ID env var is provided, no cleanup is performed

## Environment Variables

### Required
- APEG_ENV - Must be "DEMO"
- APEG_ALLOW_WRITES - Must be "YES"
- SHOPIFY_STORE_DOMAIN - Demo store URL
- SHOPIFY_ADMIN_ACCESS_TOKEN - Admin API token
- SHOPIFY_API_VERSION - API version (e.g., "2024-10")
- DEMO_STORE_DOMAIN_ALLOWLIST - Comma-separated allowed stores
- REDIS_URL - Redis connection string

### Optional
- TEST_PRODUCT_ID - Use existing product (skips create/delete)
- TEST_TAG_PREFIX - Custom prefix for test tags (default: "apeg_safe_write_test")

## CI/CD Integration
```yaml
# Example GitHub Actions workflow snippet
- name: Run Phase 2 Integration Tests
  env:
    APEG_ENV: DEMO
    APEG_ALLOW_WRITES: YES
    SHOPIFY_STORE_DOMAIN: ${{ secrets.DEMO_STORE_DOMAIN }}
    SHOPIFY_ADMIN_ACCESS_TOKEN: ${{ secrets.DEMO_ACCESS_TOKEN }}
    SHOPIFY_API_VERSION: 2024-10
    DEMO_STORE_DOMAIN_ALLOWLIST: ${{ secrets.DEMO_STORE_DOMAIN }}
    REDIS_URL: redis://localhost:6379
  run: |
    python tests/integration/verify_phase2_safe_writes.py
```

## Troubleshooting

### "Missing required environment variable"
- Ensure .env.integration is loaded: set -a; source .env.integration; set +a
- Verify all required variables are set

### "Store not in allowlist"
- Check SHOPIFY_STORE_DOMAIN matches an entry in DEMO_STORE_DOMAIN_ALLOWLIST
- No extra whitespace in domain names

### "Bulk operation did not complete successfully"
- Check Shopify Admin API logs for errors
- Verify store has sufficient API rate limit quota
- Check Redis is running and accessible

### "Cleanup failed"
- Product ID logged in error message
- Manually delete via Shopify Admin if script cleanup failed
