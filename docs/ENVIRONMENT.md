# ENVIRONMENT.md - APEG Environment Configuration

**Source of Truth:** `docs/integration-architecture-spec-v1.4.1.md` Section 1.8
**Canonical Template:** `.env.example` (single source of truth)
**Last Updated:** 2026-01-06

---

## Non-Negotiable Rules

1. `.env.example` is the only canonical template.
2. No secrets in repo. Use `.env` or a secret store.
3. If a required variable is added, update `.env.example` in the same change.
4. Phase transitions are blocked until environment parity is recorded as PASS.

---

## Profiles

Set the environment with:
- `APEG_ENV=DEMO` or `APEG_ENV=LIVE`
- `APEG_ALLOW_WRITES=YES` required for any write path

Legacy alias (optional): `ENVIRONMENT` mirrors `APEG_ENV` if needed.

---

## APEG API Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `APEG_API_KEY` | Yes | X-APEG-API-KEY header auth secret |

## APEG Runtime Safety Gates

| Variable | Required | Description |
|----------|----------|-------------|
| `APEG_ENV` | Yes | DEMO or LIVE |
| `APEG_ALLOW_WRITES` | Yes | Must be YES for mutations |

## Shopify

| Variable | Required | Description |
|----------|----------|-------------|
| `SHOPIFY_STORE_DOMAIN` | Yes | mystore.myshopify.com |
| `SHOPIFY_ADMIN_ACCESS_TOKEN` | Yes | Admin API token |
| `SHOPIFY_API_VERSION` | Yes | Pinned API version |
| `SHOPIFY_WEBHOOK_SHARED_SECRET` | If webhooks | HMAC verification secret |
| `SHOPIFY_APP_CLIENT_ID` | If OAuth | Shopify app client ID |
| `SHOPIFY_APP_CLIENT_SECRET` | If OAuth | Shopify app client secret |
| `SHOPIFY_LOCATION_ID` | If inventory ops | Location ID |
| `SHOPIFY_BULK_LOCK_NAMESPACE` | Optional | Redis lock key prefix |

## Redis

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | If locks | Redis connection string |

## Integration Testing (DEMO only)

| Variable | Required | Description |
|----------|----------|-------------|
| `DEMO_STORE_DOMAIN_ALLOWLIST` | If tests | Comma-separated allowlist |
| `TEST_PRODUCT_ID` | Optional | Use existing product for tests |
| `TEST_TAG_PREFIX` | Optional | Tag prefix for isolation |

## Network Configuration (optional)

| Variable | Required | Description |
|----------|----------|-------------|
| `APEG_API_HOST` | Optional | Bind address |
| `APEG_API_PORT` | Optional | Port |
| `APEG_API_BASE_URL` | Optional | Base URL for callers |

## Meta Ads

| Variable | Required | Description |
|----------|----------|-------------|
| `META_GRAPH_API_VERSION` | If Meta | Graph API version (e.g., v19.0) |
| `META_ACCESS_TOKEN` | If Meta | Access token |
| `META_AD_ACCOUNT_ID` | If Meta | act_XXXXX |
| `META_APP_ID` | If token debug | App ID |
| `META_APP_SECRET` | If token debug | App secret |
| `META_BUSINESS_ID` | If Meta | Business Manager ID |
| `META_PIXEL_ID` | If conversions | Pixel ID |
| `META_PAGE_ID` | If creatives | Facebook Page ID |
| `META_IG_ACCOUNT_ID` | If IG placements | Instagram account ID |

## Metrics Collection

| Variable | Required | Description |
|----------|----------|-------------|
| `METRICS_DB_PATH` | Yes | SQLite DB path |
| `METRICS_RAW_DIR` | Yes | JSONL audit dir |
| `METRICS_TIMEZONE` | Yes | Timezone for "yesterday" |
| `STRATEGY_TAG_CATALOG` | Yes | Strategy tag JSON path |
| `METRICS_COLLECTION_TIME` | Yes | Daily run time (HH:MM) |
| `METRICS_BACKFILL_DAYS` | Yes | Backfill gap window |

## Feedback Loop

| Variable | Required | Description |
|----------|----------|-------------|
| `FEEDBACK_ENABLED` | Yes | Enable feedback loop |
| `FEEDBACK_WINDOW_DAYS` | Yes | Analysis window |
| `FEEDBACK_BASELINE_DAYS` | Yes | Baseline window |
| `FEEDBACK_MIN_SPEND_USD` | Yes | Minimum spend |
| `FEEDBACK_MIN_IMPRESSIONS` | Yes | Minimum impressions |
| `FEEDBACK_MIN_CLICKS_PROXY` | Yes | Minimum clicks proxy |
| `FEEDBACK_MIN_ORDERS` | Yes | Minimum orders |
| `FEEDBACK_ROAS_BAD` | Yes | ROAS bad threshold |
| `FEEDBACK_ROAS_GOOD` | Yes | ROAS good threshold |
| `FEEDBACK_CTR_BAD` | Yes | CTR bad threshold |
| `FEEDBACK_CTR_GOOD` | Yes | CTR good threshold |
| `FEEDBACK_MAX_ACTIONS_PER_RUN` | Yes | Max actions |
| `FEEDBACK_REQUIRE_APPROVAL` | Yes | Require approval |
| `FEEDBACK_APPROVAL_MODE` | Yes | manual | n8n | none |
| `FEEDBACK_DECISION_LOG_DIR` | Yes | Decision log dir |
| `FEEDBACK_ALLOW_DUMMY_PRODUCTS` | Optional | Test helper |
| `FEEDBACK_USE_STUB_LLM` | Optional | Test helper |
| `FEEDBACK_LLM_API_KEY` | If LLM | Override LLM key |
| `FEEDBACK_LLM_MAX_TOKENS` | Optional | Token limit |

## LLM Providers (optional)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Optional | OpenAI key |
| `ANTHROPIC_API_KEY` | Optional | Claude key (used if FEEDBACK_LLM_API_KEY not set) |
| `ANTHROPIC_MODEL` | Optional | Claude model name override |
| `GEMINI_API_KEY` | Optional | Google Gemini key |

## n8n (optional)

| Variable | Required | Description |
|----------|----------|-------------|
| `N8N_BASE_URL` | If n8n | Base URL |
| `N8N_WEBHOOK_URLS` | If n8n | Webhook endpoints |
| `N8N_CREDENTIAL_ID_SHOPIFY` | If n8n | Credential ID (demo/live) |
| `N8N_CREDENTIAL_ID_META` | If n8n | Credential ID (demo/live) |
| `N8N_API_KEY` | If API use | n8n REST API key |

## Infrastructure / Logging (optional)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | If Postgres | Connection string |
| `LOG_LEVEL` | Optional | DEBUG/INFO/WARNING/ERROR |
| `ENVIRONMENT` | Optional | Legacy alias for APEG_ENV |

---

## Where Values Come From (Quick Guide)

- **Shopify Admin Token / App Secrets**: Shopify Dev Dashboard -> App Settings.
- **Shopify Webhook Secret**: Shopify Dev Dashboard -> Webhooks.
- **Meta Access Token / App IDs**: Meta for Developers -> App Settings.
- **Meta Business/Page/Pixel/IG IDs**: Business Manager / Events Manager / Page settings.
- **n8n Credential IDs**: n8n Credentials UI (ID is in the URL).
- **Redis**: Local or hosted Redis instance.

---

## File Structure

```
project/
├── .env.example      # Canonical template (committed)
├── .env              # Local values (gitignored)
├── .env.integration  # Optional local profile (gitignored)
└── .gitignore        # Must include .env*
```
