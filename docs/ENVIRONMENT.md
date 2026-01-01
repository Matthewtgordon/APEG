# ENVIRONMENT.md
# EcomAgent Environment Configuration

> **📍 Quick Links:** [Main README](../README.md) | [API Usage](API_USAGE.md) | [Docs Index](README.md)

**Source of Truth:** integration-architecture-spec-v1.4.md Section 1.8  
**Last Updated:** 2025-12-29

## 📋 Table of Contents

- [Profiles](#profiles)
- [Required Variables](#required-variables)
  - [Shopify Variables](#shopify-variables)
  - [Meta Ads Variables](#meta-ads-variables)
  - [n8n Variables](#n8n-variables)
  - [Infrastructure Variables](#infrastructure-variables)
- [File Structure](#file-structure)
- [Security Rules](#security-rules)
- [Demo → Live Swap](#demo--live-swap)

---

## Profiles

| Profile | Purpose | Secret Store |
|---------|---------|--------------|
| `DEMO` | Development/testing against dev store | Local .env.demo (gitignored) |
| `LIVE` | Production against live store | Secret manager / env vars |

Switch via: `ENVIRONMENT=DEMO` or `ENVIRONMENT=LIVE`

---

## Shopify Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SHOPIFY_STORE_DOMAIN` | ✓ | e.g., `mystore.myshopify.com` |
| `SHOPIFY_ADMIN_ACCESS_TOKEN` | ✓ | Admin API token (secret) |
| `SHOPIFY_API_VERSION` | ✓ | Pinned: `2025-10` |
| `SHOPIFY_WEBHOOK_SHARED_SECRET` | ✓ | HMAC verification |
| `SHOPIFY_APP_CLIENT_ID` | OAuth only | |
| `SHOPIFY_APP_CLIENT_SECRET` | OAuth only | |
| `SHOPIFY_LOCATION_ID` | If inventory ops | |
| `SHOPIFY_BULK_LOCK_NAMESPACE` | Optional | Lock key prefix |

---

## Meta Ads Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `META_GRAPH_API_VERSION` | ✓ | Pinned: `v22.0` |
| `META_ACCESS_TOKEN` | ✓ | System user token (secret) |
| `META_AD_ACCOUNT_ID` | ✓ | `act_XXXXX` format |
| `META_BUSINESS_ID` | Optional | Business Manager ID |
| `META_PIXEL_ID` | If conversions | |
| `META_PAGE_ID` | If creatives | Facebook Page ID |
| `META_IG_ACCOUNT_ID` | If IG placements | |
| `META_APP_ID` | Token debug | |
| `META_APP_SECRET` | Token debug | |

---

## n8n Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `N8N_BASE_URL` | ✓ | n8n instance URL |
| `N8N_API_KEY` | If API usage | |
| `N8N_WEBHOOK_URLS` | Per workflow | |
| `N8N_CREDENTIAL_ID_SHOPIFY` | ✓ | Credential ID (demo vs live) |
| `N8N_CREDENTIAL_ID_META` | ✓ | Credential ID (demo vs live) |

---

## Infrastructure Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✓ | PostgreSQL connection |
| `REDIS_URL` | If locks | Redis for distributed locks |
| `LOG_LEVEL` | ✓ | DEBUG, INFO, WARNING, ERROR |
| `ENVIRONMENT` | ✓ | `DEMO` or `LIVE` |

---

## File Structure

```
project/
├── .env.example      # Template (committed)
├── .env.demo         # Demo values (gitignored)
├── .env.live         # Live values (gitignored, or use secret manager)
└── .gitignore        # Must include .env.demo, .env.live
```

---

## Security Rules

1. **Never commit secrets** - All tokens in .env files or secret store
2. **No hardcoded values** - All env-specific values via env vars
3. **Validate on startup** - Fail fast if required vars missing
4. **Log safely** - Never log tokens, mask in error messages

### 🔒 Security Best Practices

**API Keys & Tokens**
- Generate strong API keys: `openssl rand -hex 32`
- Rotate credentials regularly
- Use different keys for DEMO and LIVE environments
- Never share credentials in chat, logs, or documentation

**File Security**
- Keep `.env.*` files in `.gitignore`
- Set restrictive file permissions: `chmod 600 .env`
- Use a secret manager (AWS Secrets Manager, HashiCorp Vault) for production
- Back up `.env` files securely before modifications:
  ```bash
  cp .env .env.bak.$(date +%Y%m%d-%H%M%S)
  ```

**Environment Isolation**
- Strict separation between DEMO and LIVE
- Different Shopify stores for each environment
- Different Meta ad accounts or sandboxes
- Separate Redis instances recommended

---

## Demo → Live Swap

See Appendix F in spec. Summary:
1. Switch `ENVIRONMENT=LIVE`
2. Update all `*_TOKEN`, `*_SECRET`, `*_ID` vars
3. Update n8n credential IDs
4. Run smoke tests
5. Verify execution logs show LIVE credentials
