# Integration Architecture Specification
## EcomAgent + APEG + Advertising Agent

> **📍 Quick Links:** [Main README](../README.md) | [Project Plan](PROJECT_PLAN_ACTIVE.md) | [Environment Setup](ENVIRONMENT.md) | [Docs Index](README.md)

Version: 1.4.1  
**Date:** 2025-12-29  
**Status:** PRODUCTION READY (Demo→Live)  
**Author:** Matticulous + Claude  

## 📋 Table of Contents

### Core Sections
1. [System Overview](#1-system-overview)
2. [Data Models & Schemas](#2-data-models--schemas)
3. [Component Integration Patterns](#3-component-integration-patterns)
4. [Workflow Orchestration](#4-workflow-orchestration)
5. [Shopify Integration](#5-shopify-integration)
6. [Meta Ads Integration](#6-meta-ads-integration)
7. [Metrics & Attribution](#7-metrics--attribution)
8. [n8n Integration](#8-n8n-integration)
9. [Security & Audit](#9-security--audit)

### Appendices
- [Appendix A: API Endpoint Reference](#appendix-a-api-endpoint-reference)
- [Appendix B: Error Handling Matrix](#appendix-b-error-handling-matrix)
- [Appendix C: Data Schema SQL](#appendix-c-data-schema-sql)
- [Appendix D: CI/CD Pipeline](#appendix-d-cicd-pipeline)
- [Appendix E: Rollback Procedures](#appendix-e-rollback-procedures)
- [Appendix F: Demo→Live Swap Checklist](#appendix-f-demolive-swap-checklist)
- [Appendix G: Rate Limit Strategy](#appendix-g-rate-limit-strategy)

---

## 1. System Overview

### 1.1 Architecture Topology

The system is composed of four primary components operating in a feedback loop:

```
┌─────────────────────────────────────────────────────────────────┐
│                         APEG (Master)                            │
│              Async Orchestrator (FastAPI)                        │
│  Roles: Command routing, workflow coordination, metrics review  │
└───────────┬─────────────────────────────────────┬───────────────┘
            │                                     │
            │ asyncio.to_thread()                 │ Direct call
            ▼                                     ▼
┌───────────────────────┐              ┌─────────────────────────┐
│   EcomAgent (SEO)     │              │   Advertising Agent     │
│   Sync Specialist     │              │   (Meta API Client)     │
│   (Python/OpenAI)     │              │   Async Service         │
└───────┬───────────────┘              └──────────┬──────────────┘
        │                                         │
        │ HTTP → JSON                             │ API calls
        ▼                                         ▼
┌───────────────────────┐              ┌─────────────────────────┐
│   N8N Workflow        │              │   Meta Marketing API    │
│   (Orchestration)     │              │   (Ads Platform)        │
└───────┬───────────────┘              └──────────┬──────────────┘
        │                                         │
        │ GraphQL Bulk Ops                        │ Metrics webhook
        ▼                                         ▼
┌───────────────────────┐              ┌─────────────────────────┐
│   Shopify Store       │◄─────────────┤   Metrics Database      │
│   (Product Catalog)   │  Product IDs │   (JSONL + SQLite)      │
└───────────────────────┘              └─────────────────────────┘
        │                                         │
        │ Product data                            │ Performance data
        └─────────────────┬───────────────────────┘
                          │ Feedback Loop
                          ▼
                    ┌──────────────┐
                    │ Google Sheets│
                    │ (Staging UI) │
                    └──────────────┘
```

### 1.2 Component Roles

**APEG (Master Orchestrator)**
- **Type:** Async FastAPI service
- **Location:** `./APEG/src/apeg_core/`
- **Responsibilities:**
  - Accept human commands ("optimize 50 birthstone products")
  - Trigger SEO updates via EcomAgent (wrapped in `asyncio.to_thread`)
  - Trigger ad campaigns via Advertising Agent
  - Review metrics and decide next actions
  - Coordinate approval workflows
- **Current State:** Proven reliable for inventory management, ready for SEO/Ads integration
- **Constraint:** Cannot be rewritten - must wrap sync services to maintain async architecture

**EcomAgent (SEO Specialist)**
- **Type:** Synchronous Python service (Flask)
- **Location:** `./EcomAgent/src/seo_engine/`
- **Responsibilities:**
  - Generate SEO-optimized titles, descriptions, meta tags
  - Enforce safety guardrails (banned words, length limits)
  - Apply governance rules (baseline + overrides)
  - Export to JSONL + CSV backups
- **Current State:** Operational, processes 5 products per run
- **Constraint:** Synchronous architecture must be preserved (no rewrite)
- **Integration Method:** APEG imports as module, wraps in `asyncio.to_thread`

**N8N Workflow (The Pipe)**
- **Type:** Visual workflow automation
- **Location:** `Claudes Version Workflow (1).json`
- **Responsibilities:**
  - Trigger EcomAgent via HTTP request
  - Stage changes in Google Sheets (human review)
  - Execute Shopify GraphQL Bulk Operations on approval
  - Handle Etsy draft creation (API limitation)
- **Current State:** Functional, but lacks visibility layer
- **Enhancement:** Adding Google Sheets export node before approval webhook

**Advertising Agent (Meta Integration)**
- **Type:** Async service (to be built)
- **Location:** `./APEG/src/apeg_core/agents/advertising_agent.py`
- **Responsibilities:**
  - Create Facebook/Instagram ad campaigns from product data
  - Organize products into sets (by category/collection)
  - Use existing images from Shopify
  - Apply fixed budget allocation (V1)
  - Report campaign IDs back to APEG
- **Current State:** Not yet built (Phase 6 deliverable)
- **API:** Meta Marketing API (sandbox credentials available)

**Google Sheets (Staging Layer)**
- **Type:** Human approval interface
- **Responsibilities:**
  - Display proposed SEO changes in mobile-friendly format
  - Provide approval webhook trigger
  - Replaced on each run (ephemeral staging)
- **Current State:** Design complete, implementation pending
- **Columns:** Product ID, Original Title, Proposed Title, Original Description, Proposed Description, Status

**Metrics Database**
- **Type:** Dual storage (JSONL + SQLite)
- **Location:** `./EcomAgent/data/output/` (JSONL), `./APEG/data/metrics.db` (SQLite)
- **Responsibilities:**
  - Store ad performance metrics (CTR, ROAS, conversions)
  - Link metrics to product versions (via `product_id` + `version`)
  - Enable daily batch queries for feedback loop
- **Current State:** JSONL structure exists, SQLite schema to be defined
- **Collection:** Daily scheduled job (Meta API fetch)

### 1.3 Data Flow: SEO → Ads → Metrics → SEO (The Loop)

**Phase 1: SEO Optimization**
1. Human issues command to APEG: "Optimize 50 products in 'Birthstone Jewelry' collection"
2. APEG wraps EcomAgent call in `asyncio.to_thread` (async → sync bridge)
3. EcomAgent generates new titles/descriptions using Canonical Product Model
4. N8N workflow stages changes in Google Sheets
5. Human reviews and approves via webhook
6. N8N executes Shopify GraphQL Bulk Operation (batch update)

**Phase 2: Ad Campaign Creation**
1. APEG detects products with new SEO (version incremented)
2. APEG triggers Advertising Agent with product set
3. Advertising Agent reads Canonical Product Model (strategy_tag, images, price)
4. Advertising Agent creates Meta ad campaigns (product sets grouped by category)
5. Campaign IDs stored in metrics DB, linked to product versions

**Phase 3: Metrics Collection**
1. Daily scheduled job fetches ad performance from Meta API
2. Metrics (CTR, ROAS, conversions) stored in DB with `product_id` + `version` keys
3. High-performing products flagged (e.g., CTR > 2%)
4. Low-performing products flagged (e.g., CTR < 0.5%)

**Phase 4: Feedback Loop (Auto-Refinement)**
1. APEG queries metrics DB for underperforming products
2. APEG triggers EcomAgent with context: "Low CTR on 'Blue Sapphire Necklace' - emphasize 'birthstone' angle"
3. EcomAgent generates revised SEO (version increments)
4. Repeat Phase 1 (staging → approval → publish)
5. Advertising Agent updates campaigns with new copy
6. Monitor metrics for improvement

### 1.4 Key Architectural Decisions

**Decision 1: APEG as Master Orchestrator**
- Rationale: APEG already handles inventory coordination, extending it to SEO/Ads maintains single source of truth
- Trade-off: Requires async-sync bridging via `asyncio.to_thread`

**Decision 2: Preserve Existing Codebases**
- Rationale: EcomAgent's SEO logic is proven and reliable
- Trade-off: Cannot use native async patterns, must wrap synchronous calls

**Decision 3: GraphQL Bulk Operations for Shopify**
- Rationale: Avoid REST API rate limits during batch processing (5,000+ products)
- Trade-off: More complex implementation than REST, but essential for scale

**Decision 4: Google Sheets as Staging UI**
- Rationale: Mobile-friendly, zero dev time for UI, familiar interface
- Trade-off: Manual export step in N8N, but solves visibility problem immediately

**Decision 5: Etsy Draft-Only (Governance Policy)**
- Rationale: Human review required before publishing to prevent accidental listings
- Capability: Etsy API supports auto-publishing via `updateListing(state: "active")`, but system defaults to `state: "draft"` as business policy
- Trade-off: Manual review step in Etsy dashboard, but ensures quality control before going live

**Decision 6: Dual Metrics Storage (JSONL + SQLite)**
- Rationale: JSONL for audit trail, SQLite for queryable metrics
- Trade-off: Slight storage overhead, but enables both rollback and analysis

**Decision 7: Fixed Budget for V1 Ads**
- Rationale: Minimize risk during launch, observe behavior before dynamic allocation
- Trade-off: May miss optimization opportunities, but safer for learning phase

### 1.5 Migration Strategy

**Current State (Pre-Integration):**
- APEG: Handles inventory, dormant for SEO
- EcomAgent: Standalone service, triggered manually via N8N
- N8N: Works but lacks visibility

**Target State (Post-Integration):**
- APEG: Master orchestrator for inventory + SEO + ads
- EcomAgent: Imported as Python module, wrapped in `asyncio.to_thread`
- N8N: Enhanced with Google Sheets staging layer
- Advertising Agent: New service, integrated with APEG
- Metrics DB: Operational, feeding back to SEO decisions

**Migration Path:**
1. Build Canonical Product Model in APEG (Section 2)
2. Implement APEG → EcomAgent integration (Section 3)
3. Add Google Sheets staging to N8N (Section 4)
4. Implement Shopify GraphQL Bulk Ops (Section 5)
5. Build Advertising Agent foundation (Section 6)
6. Set up Metrics Collection (Section 7)
7. Implement Feedback Loop logic (Section 8)
8. Test end-to-end with 10 products
9. Scale to full catalog (5,000+ products)

### 1.6 Success Criteria

**Operational Success:**
- APEG can orchestrate SEO updates for 50+ products in single command
- Google Sheets staging displays changes within 30 seconds
- Shopify GraphQL Bulk Ops complete without rate limit errors
- Ad campaigns create successfully with correct product images
- Metrics collection runs daily without manual intervention

**Quality Success:**
- SEO changes maintain safety guardrails (no banned words, correct length)
- Ads target correct audiences (birthstone buyers, jewelry enthusiasts)
- Feedback loop identifies underperforming products within 7 days
- Revised SEO shows measurable improvement (CTR increase)

**Reliability Success:**
- System recovers from API timeouts (retry logic works)
- Failed bulk ops rollback gracefully (mark as "FAILED" in staging sheet)
- Human approval workflow never bypassed accidentally
- Metrics data integrity maintained (no duplicate entries)

### 1.7 Technical Constraints & Assumptions

**Licensing Constraint (BLOCKING):**
The `etsyv3` Python library is licensed under GPL-3.0, which conflicts with APEG's MIT license. Direct integration would impose copyleft requirements on the entire codebase.

**Resolution Options:**
1. **Isolate GPL code** - Run Etsy sync as a separate microservice (recommended)
2. **Replace library** - Use Etsy REST API via custom HTTP calls (no GPL dependency)
3. **Internal-only** - Use GPL code only for internal tooling, never distribute

**Status:** BLOCKING for Etsy integration. Must be resolved before Phase 5.

**Shopify SEO Field Mapping (Clarification):**
- **GraphQL API:** Use `product.seo { title, description }` input object (as implemented in Section 2.2)
- **REST API:** Use `metafields_global_title_tag` and `metafields_global_description_tag` on Product object
- **Incorrect:** Do NOT use `product.metafields.seo.title` (this namespace does not exist for SEO fields)

**Shopify API Version Policy:**
- Pin API version explicitly (currently `2025-10`, plan for `2026-01`)
- Monitor [Shopify Developer Changelog](https://shopify.dev/changelog) for deprecations and breaking changes
- Note: Quarterly release notes discontinued; Developer Changelog is now the authoritative source

**Model Context Protocol (MCP) Clarification:**
Shopify's MCP servers (Dev MCP, Storefront MCP) are designed for AI assistants and chatbots. They are **not required** for APEG's Admin API usage. APEG continues using private app credentials and the ShopifyAPI library as planned. MCP integration is an optional enhancement track, not a core requirement.

**Shopify Custom App Creation (Post-2026-01-01):**

Starting 2026-01-01: you cannot create new legacy custom apps from the Shopify admin.
New apps must be created/managed in the Shopify Dev Dashboard.
Existing legacy custom apps already created are not automatically removed by this policy.

### 1.8 Environment & Configuration Boundary (Demo vs Live)

**Purpose:** Define the complete config surface area and enforce parity so demo-to-live swaps and integration test runs cannot fail from missing variables.

**Rule:**
- No secrets in repo.
- All credentials via environment variables or secret store only.
- Canonical variable names MUST match implementation (see tables below).

**Required Profiles:**
- `APEG_ENV=DEMO` or `APEG_ENV=LIVE` (canonical)
- `APEG_ALLOW_WRITES=YES` is required for any mutation-capable execution path

**Environment Governance:**
- `.env.example` is the **sole canonical environment template**.
- All APEG API Configuration variables MUST exist in the canonical template.
- Any phase-specific notes are comments/sections inside the same template.
- **Phase transitions are blocked until the Environment Parity Check is recorded as PASS in ACCEPTANCE_TESTS evidence.**

**Environment Templates (Parity Rule):**
- All variables under "APEG API Configuration" MUST exist in `.env.example`.
- If any new required variable is added, it MUST be added to `.env.example` in the same commit.
- Additional `.env.*.example` templates are **deprecated** to prevent drift.

**Config Surface Area (Canonical)**

**APEG API Configuration:**
| Variable | Description |
|----------|-------------|
| `APEG_API_KEY` | User-defined secret string (treat like a password). Used for X-APEG-API-KEY header auth. Example: `apeg_sk_live_3f6b9c2a8d1e4c7f9a0b1c2d3e4f5a6b` (32+ chars). Do NOT reuse Shopify tokens. Generate: `openssl rand -hex 32` |

**APEG Runtime Safety Gates:**
| Variable | Description |
|----------|-------------|
| `APEG_ENV` | `DEMO` or `LIVE`. DEMO-only safety gating is enforced in integration tooling. |
| `APEG_ALLOW_WRITES` | Must be `YES` to allow write paths. |

**Shopify:**
| Variable | Description |
|----------|-------------|
| `SHOPIFY_STORE_DOMAIN` | Store domain (e.g., `mystore.myshopify.com`) |
| `SHOPIFY_ADMIN_ACCESS_TOKEN` | Admin API token (secret store) |
| `SHOPIFY_API_VERSION` | Pinned Shopify API version (e.g., 2024-10) |
| `SHOPIFY_WEBHOOK_SHARED_SECRET` | HMAC verification secret |
| `SHOPIFY_APP_CLIENT_ID` | If OAuth flow used |
| `SHOPIFY_APP_CLIENT_SECRET` | If OAuth flow used (secret store) |
| `SHOPIFY_LOCATION_ID` | If inventory/location-specific operations |
| `SHOPIFY_BULK_LOCK_NAMESPACE` | Optional lock key prefix |

**Redis:**
| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Redis connection string (required for locking in bulk ops client) |

**Integration Testing Only (DEMO):**
| Variable | Description |
|----------|-------------|
| `DEMO_STORE_DOMAIN_ALLOWLIST` | Comma-separated allowlist; must include SHOPIFY_STORE_DOMAIN |
| `TEST_PRODUCT_ID` | Optional; skips create/delete by using an existing product |
| `TEST_TAG_PREFIX` | Optional; custom prefix for deterministic test tags |

**Network Configuration (Optional - for n8n/external callers):**
| Variable | Description |
|----------|-------------|
| `APEG_API_HOST` | Server bind address (default: 0.0.0.0) |
| `APEG_API_PORT` | Server port (default: 8000) |
| `APEG_API_BASE_URL` | Full base URL for external callers (example: http://192.168.1.50:8000) |

**Note:** `APEG_API_BASE_URL` is typically set in n8n's environment (not APEG's), allowing n8n workflows to reference `$env.APEG_API_BASE_URL` for dynamic URL construction.

**Meta Ads:**
| Variable | Description |
|----------|-------------|
| `META_GRAPH_API_VERSION` | Pinned version (quarterly upgrade policy) |
| `META_ACCESS_TOKEN` | System user token preferred (secret store) |
| `META_AD_ACCOUNT_ID` | Ad account ID (act_XXXXX) |
| `META_BUSINESS_ID` | Business Manager ID (if used) |
| `META_PIXEL_ID` | Pixel ID for conversion tracking |
| `META_PAGE_ID` | Facebook Page ID (for creatives) |
| `META_IG_ACCOUNT_ID` | Instagram account ID (for placements) |
| `META_APP_ID` | App ID for token debug |
| `META_APP_SECRET` | App secret (secret store) |

**n8n:**
| Variable | Description |
|----------|-------------|
| `N8N_BASE_URL` | n8n instance URL |
| `N8N_API_KEY` | API key if using n8n API |
| `N8N_WEBHOOK_URLS` | Workflow-specific webhook endpoints |
| `N8N_CREDENTIAL_ID_SHOPIFY` | Credential ID (different for demo/live) |
| `N8N_CREDENTIAL_ID_META` | Credential ID (different for demo/live) |

**Infrastructure:**
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `LOG_LEVEL` | DEBUG, INFO, WARNING, ERROR |
| `ENVIRONMENT` | Legacy alias for `APEG_ENV` (retain for backward compatibility). |

---

## 2. Canonical Product Model

**Location:** `APEG/src/apeg_core/schemas/canonical_product.py`

**Purpose:** Unified data model for products flowing through SEO, Ads, and Metrics pipelines. Normalizes Shopify/Etsy data into a platform-agnostic core with platform-specific extensions.

### 2.1 Core Schema Definition

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

class ImageRef(BaseModel):
    """Reference to a product image"""
    url: str
    alt_text: Optional[str] = None
    image_id: Optional[str] = None  # Platform-specific ID

class ValidationResult(BaseModel):
    """Platform validation status"""
    valid: bool
    errors: List[str] = []

class ValidationSummary(BaseModel):
    """Cross-platform validation results"""
    shopify: ValidationResult
    etsy: ValidationResult
    last_validated_at: datetime

class CanonicalProduct(BaseModel):
    """
    Canonical Product Model - Full Scope
    
    Constraints:
    - Title max 140 chars (Etsy limit)
    - Description stored as HTML (stripped for Etsy export)
    - Tags stored as full set (Etsy export selects top 13)
    """
    
    # === CORE IDENTITY ===
    product_id: str = Field(..., description="Universal identifier for metrics linking")
    shopify_id: Optional[str] = Field(None, description="Shopify product ID (GraphQL: gid://shopify/Product/<id>, REST: numeric)")
    etsy_id: Optional[str] = Field(None, description="Etsy listing ID (numeric)")
    sku: Optional[str] = Field(None, description="Primary/representative SKU")
    handle: str = Field(..., description="URL slug (required for Shopify lookups)")
    
    @staticmethod
    def normalize_shopify_id(id_value: str, format: str = "graphql") -> str:
        """
        Normalize Shopify ID to required format
        
        Args:
            id_value: Numeric ID or Global ID
            format: "graphql" (gid://) or "rest" (numeric)
        
        Returns:
            Normalized ID string
        
        Example:
            normalize_shopify_id("12345", "graphql") → "gid://shopify/Product/12345"
            normalize_shopify_id("gid://shopify/Product/12345", "rest") → "12345"
        """
        if format == "graphql":
            if id_value.startswith("gid://"):
                return id_value  # Already in Global ID format
            return f"gid://shopify/Product/{id_value}"
        else:  # format == "rest"
            if id_value.startswith("gid://"):
                return id_value.split('/')[-1]  # Extract numeric ID
            return id_value
    
    @staticmethod
    def normalize_etsy_id(id_value: str) -> str:
        """
        Normalize Etsy ID to numeric format
        
        Args:
            id_value: Numeric ID or accidentally Global ID
        
        Returns:
            Numeric ID string
        """
        if id_value.startswith("gid://"):
            return id_value.split('/')[-1]
        return id_value
    
    # === SEO CONTENT ===
    title: str = Field(..., max_length=140, description="Product title (Etsy 140 char limit)")
    description_html: str = Field(..., description="Rich HTML description (auto-stripped for Etsy)")
    meta_title: Optional[str] = Field(None, max_length=70, description="SEO meta title")
    meta_description: Optional[str] = Field(None, max_length=320, description="SEO meta description")
    tags: List[str] = Field(default_factory=list, description="Full tag set (Etsy export selects top 13)")
    
    # === ADVERTISING ===
    strategy_tag: Optional[str] = Field(None, description="Engine-generated strategy (e.g., 'high-value-birthstone')")
    images: List[ImageRef] = Field(default_factory=list, description="Product images for ad creative")
    price: Optional[Decimal] = Field(None, description="Current price (for dynamic ads)")
    inventory_quantity: Optional[int] = Field(None, description="Stock level (ads agent checks > 0)")
    vendor: Optional[str] = Field(None, description="Brand/vendor name (for ad segmentation)")
    product_type: Optional[str] = Field(None, description="Product category (for Meta product sets)")
    
    # === PLATFORM EXTENSIONS ===
    shopify_data: Optional[Dict[str, Any]] = Field(None, description="Shopify-specific fields (variants, collections)")
    etsy_data: Optional[Dict[str, Any]] = Field(None, description="Etsy-specific fields (taxonomy_id, shipping_profile)")
    
    # === VERSIONING & AUDIT ===
    version: int = Field(default=1, description="Increments on each SEO update")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_seo_run: Optional[datetime] = Field(None, description="When SEO engine last processed")
    
    # === VALIDATION ===
    validation_summary: Optional[ValidationSummary] = Field(None, description="Cross-platform validation status")
    
    @validator('title')
    def validate_title_length(cls, v):
        """Enforce 140 char hard limit for Etsy compatibility"""
        if len(v) > 140:
            raise ValueError(f"Title exceeds 140 chars (Etsy limit): {len(v)} chars")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
```

### 2.2 Export Methods

```python
class CanonicalProduct(BaseModel):
    # ... (schema above)
    
    def to_shopify(self, existing_tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Export to Shopify GraphQL payload
        
        CRITICAL: Shopify GraphQL productUpdate is DESTRUCTIVE for tags.
        Caller MUST pass existing_tags to preserve full tag set.
        
        Returns HTML description as-is.
        Uses dedicated `seo` input object (not metafields).
        
        Args:
            existing_tags: Full tag list from Shopify (required to prevent data loss)
        
        Returns:
            GraphQL productUpdate input payload
        """
        # Merge existing tags with new tags to prevent data loss
        if existing_tags is not None:
            # Combine and dedupe (preserve order, new tags first)
            merged_tags = list(dict.fromkeys(self.tags + existing_tags))
        else:
            # Fallback: use only new tags (caller should avoid this)
            merged_tags = self.tags
        
        # Ensure Global ID format (gid://shopify/Product/<id>)
        product_gid = self.shopify_id
        if product_gid and not product_gid.startswith("gid://"):
            product_gid = f"gid://shopify/Product/{product_gid}"
        
        payload = {
            "id": product_gid,
            "title": self.title,
            "descriptionHtml": self.description_html,
            "tags": merged_tags,  # CRITICAL: Full merged set to prevent overwrites
            "seo": {  # CRITICAL: Use dedicated SEO input (not metafields)
                "title": self.meta_title or self.title[:70],  # Fallback to truncated title
                "description": self.meta_description or ""
            }
        }
        
        # Merge platform-specific data
        if self.shopify_data:
            payload.update(self.shopify_data)
        
        return payload
    
    def to_etsy(self) -> Dict[str, Any]:
        """
        Export to Etsy API payload
        
        - Strips HTML tags from description
        - Selects top 13 tags deterministically
        - Creates as DRAFT (governance policy: human review required)
        
        CRITICAL: Etsy requires shipping_profile_id and readiness_state_id
        for physical listings. These must be present in etsy_data.
        
        NOTE: Etsy is migrating to "Processing Profiles." If your store
        has transitioned, readiness_state_id becomes mandatory. Treat this
        as a migration-sensitive field.
        """
        import re
        
        # Validate required Etsy fields
        if not self.etsy_data:
            raise ValueError("Missing etsy_data (required for Etsy export)")
        
        required_fields = ['taxonomy_id', 'shipping_profile_id']
        missing = [f for f in required_fields if f not in self.etsy_data]
        if missing:
            raise ValueError(f"Missing required Etsy fields: {missing}")
        
        # Strip HTML for Etsy
        description_plain = re.sub(r'<[^>]+>', '', self.description_html)
        
        # Select top 13 tags deterministically
        etsy_tags = self._select_etsy_tags()
        
        # Ensure numeric ID format for Etsy (not Global ID)
        listing_id = self.etsy_id
        if listing_id and listing_id.startswith("gid://"):
            # Extract numeric ID from Global ID format
            listing_id = listing_id.split('/')[-1]
        
        payload = {
            "listing_id": listing_id,
            "title": self.title,  # Already validated to 140 chars
            "description": description_plain,
            "tags": etsy_tags,
            "state": "draft",  # GOVERNANCE POLICY: Human review required before publish
            "taxonomy_id": self.etsy_data['taxonomy_id'],
            "shipping_profile_id": self.etsy_data['shipping_profile_id'],
        }
        
        # Add readiness_state_id if present (Processing Profiles migration)
        if 'readiness_state_id' in self.etsy_data:
            payload['readiness_state_id'] = self.etsy_data['readiness_state_id']
        
        # Merge remaining platform-specific data
        for key, value in self.etsy_data.items():
            if key not in payload:  # Don't overwrite required fields
                payload[key] = value
        
        return payload
    
    def _select_etsy_tags(self) -> List[str]:
        """
        Deterministic tag selection for Etsy (max 13)
        
        Ranking logic:
        1. Required/core tags (if any defined in strategy)
        2. Strategy-derived tags (from strategy_tag)
        3. Existing tags (in original order)
        4. Dedupe
        5. Truncate to 13
        """
        selected = []
        
        # Priority 1: Strategy-derived tags
        if self.strategy_tag:
            # Example: "high-value-birthstone" → ["birthstone", "high-value"]
            strategy_tags = self.strategy_tag.replace('-', ' ').split()
            selected.extend(strategy_tags)
        
        # Priority 2: Existing tags
        selected.extend(self.tags)
        
        # Dedupe (preserve order)
        seen = set()
        deduped = []
        for tag in selected:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                deduped.append(tag)
        
        # Truncate to 13
        return deduped[:13]
```

### 2.3 Validation Rules

**Shopify Constraints:**
- Title: max 255 chars (we enforce 140 for cross-platform compat)
- Tags: max 250 tags
- Description: HTML allowed

**Etsy Constraints:**
- Title: max 140 chars (enforced by Pydantic validator)
- Tags: max 13 tags (enforced by `_select_etsy_tags()`)
- Description: plain text only (enforced by `to_etsy()`)
- Shipping Profile: `shipping_profile_id` required in `etsy_data`
- Processing Profiles: `readiness_state_id` required if store has migrated (check store settings)
- Taxonomy: `taxonomy_id` required for category assignment

**Validation Enforcement:**
```python
def validate_for_platforms(product: CanonicalProduct) -> ValidationSummary:
    """
    Run cross-platform validation checks
    
    Returns ValidationSummary with platform-specific errors
    """
    shopify_errors = []
    etsy_errors = []
    
    # Shopify checks
    if len(product.title) > 255:
        shopify_errors.append(f"Title exceeds 255 chars: {len(product.title)}")
    if len(product.tags) > 250:
        shopify_errors.append(f"Too many tags: {len(product.tags)} (max 250)")
    
    # Etsy checks
    if len(product.title) > 140:
        etsy_errors.append(f"Title exceeds 140 chars: {len(product.title)}")
    
    if not product.etsy_data:
        etsy_errors.append("Missing etsy_data (required for Etsy export)")
    else:
        # Check required Etsy fields
        if 'taxonomy_id' not in product.etsy_data:
            etsy_errors.append("Missing Etsy taxonomy_id")
        if 'shipping_profile_id' not in product.etsy_data:
            etsy_errors.append("Missing Etsy shipping_profile_id (required)")
        # Processing Profiles check (migration-sensitive)
        # Note: readiness_state_id becomes required AFTER store migrates
        # System should warn if missing but allow it (not all stores migrated yet)
    
    return ValidationSummary(
        shopify=ValidationResult(valid=len(shopify_errors) == 0, errors=shopify_errors),
        etsy=ValidationResult(valid=len(etsy_errors) == 0, errors=etsy_errors),
        last_validated_at=datetime.utcnow()
    )
```

### 2.4 Usage Example

```python
# Ingestion from Shopify GraphQL
shopify_product = fetch_from_shopify_graphql(product_id="gid://shopify/Product/123")

# CRITICAL: Fetch existing tags FIRST to prevent data loss
existing_tags = shopify_product['tags']  # e.g., ["handmade", "vintage", "eco-friendly", ...]

canonical = CanonicalProduct(
    product_id=f"shopify:{shopify_product['id']}",
    shopify_id=shopify_product['id'],  # Already in gid:// format from GraphQL
    handle=shopify_product['handle'],
    title=shopify_product['title'][:140],  # Enforce Etsy limit
    description_html=shopify_product['descriptionHtml'],
    meta_title=shopify_product.get('seo', {}).get('title'),
    meta_description=shopify_product.get('seo', {}).get('description'),
    tags=shopify_product['tags'],  # Store full tag set
    images=[ImageRef(url=img['url'], image_id=img['id']) for img in shopify_product['images']],
    shopify_data={'variants': shopify_product['variants']},
    etsy_data={
        'taxonomy_id': 1234,  # Example: Jewelry > Necklaces
        'shipping_profile_id': 5678,
        'readiness_state_id': 9012  # Processing Profiles (if migrated)
    },
    version=1
)

# Validate before export
canonical.validation_summary = validate_for_platforms(canonical)

# Export to Shopify (with tag hydration)
if canonical.validation_summary.shopify.valid:
    # CRITICAL: Pass existing_tags to prevent data loss
    shopify_payload = canonical.to_shopify(existing_tags=existing_tags)
    update_shopify_graphql(shopify_payload)

# Export to Etsy (as draft)
if canonical.validation_summary.etsy.valid:
    etsy_payload = canonical.to_etsy()
    create_etsy_listing(etsy_payload)  # Creates as draft per governance policy
```

### 2.4.1 Tag Hydration Pattern (CRITICAL)

**Problem:** Shopify's `productUpdate` mutation is DESTRUCTIVE for tags - it replaces the entire tag list.

**Solution:** Always fetch existing tags before export and merge them:

```python
# WRONG: This will wipe out all existing tags not in canonical.tags
shopify_payload = canonical.to_shopify()  # Missing existing_tags

# RIGHT: Merge existing tags to preserve data
existing_tags = fetch_shopify_tags(product_id)
shopify_payload = canonical.to_shopify(existing_tags=existing_tags)
```

**Implementation Note:** The coding agent must implement tag hydration at the orchestration layer (APEG), not in the Canonical Product Model itself.

### 2.4.2 Tag Merge Policy (Explicit Definition)

**Policy:** MERGE mode (not replace)

| Field | Policy | Behavior |
|-------|--------|----------|
| `tags` | MERGE | Combine new_tags with existing_tags, dedupe case-insensitively, preserve order (new first) |
| `title` | REPLACE | Use new_title if provided and `apply_changes=true` |
| `description` | REPLACE | Use new_description if provided and `apply_changes=true` |
| `meta_title` | REPLACE | Use new_meta_title if provided |
| `meta_description` | REPLACE | Use new_meta_description if provided |

**Tag Merge Status: VERIFIED (API 2025-10)**
Validated: productUpdate with merged tags preserved all pre-existing tags in staging (dev-store test).

**Handling `apply_changes=null`:**
- When SEO engine returns `apply_changes=null`: Stage changes for human review (do not auto-apply)
- When `apply_changes=true`: Apply changes automatically (within safety guardrails)
- When `apply_changes=false`: Skip product (no changes)

**Banned Words Enforcement (Source of Truth: `rules/seo_baseline.yaml`):**
```yaml
banned_words: ["cheap", "guarantee", "cure", "best selling"]
preserve_words: []  # Words that must remain in output
```

These rules are enforced by `ConstraintGuard.enforce()` deterministically AFTER LLM generation. The LLM cannot override these constraints. See `src/seo_engine/validators/guard.py` for implementation.

---

**Key Design Decisions:**
1. **Title constraint (140 chars):** Enforced at model level to prevent Etsy export failures
2. **HTML storage:** Rich HTML preserved in core model, stripped only on Etsy export
3. **Tag determinism:** Etsy export always produces same 13 tags for same input (no randomness)
4. **Etsy draft-only (governance policy):** System defaults to `state: "draft"` to require human approval before publishing. The Etsy API *supports* auto-publishing via `updateListing(state: "active")`, but we enforce manual review as a business policy to prevent accidental listings.
5. **Validation tracking:** `last_validated_at` ensures stale validations are detectable
6. **Tag hydration:** Shopify exports MUST merge existing tags to prevent destructive overwrites (GraphQL productUpdate replaces entire tag list)
7. **ID normalization:** Shopify GraphQL requires Global IDs (`gid://shopify/Product/<id>`), REST uses numeric IDs - model provides normalization helpers
8. **Etsy shipping profiles:** Required fields (`shipping_profile_id`, `readiness_state_id`) must be present in `etsy_data` to prevent API rejection (especially critical during Processing Profiles migration)

---

## 3. APEG → EcomAgent Integration

**Purpose:** Define the deterministic invocation contract for how APEG (async orchestrator) calls EcomAgent (sync specialist) at scale, with product-data injection, in-memory overrides, observability metadata, safe cancellation, and resume/idempotency guarantees.

### 3.1 Runtime Ownership Model

**APEG Owns:**
- Scheduling, concurrency control, retry logic, cancellation handling
- Staging sheet writes (Google Sheets) with backpressure management
- Run state in database (source of truth for resume/idempotency)
- Product discovery and data fetching (REST/GraphQL/Bulk Operations)
- Version increment timing (post-approval only)

**EcomAgent Owns:**
- SEO computation for a single product payload (pure function)
- Baseline configuration load from YAML files
- Returning contract-shaped proposals with notes/errors
- Internal decision logging (with run_id correlation)

**Critical Constraint:** EcomAgent MUST NOT perform product fetching when `product_data` is provided (pure compute path).

### 3.2 Dependency Setup

**Critical Decision:** Choose ONE of the following import strategies (recommendation: Option A for production stability).

#### Option A: Editable Package Install (Recommended)

**Prerequisites:** EcomAgent must have proper packaging configuration.

**Step 1: Add packaging to EcomAgent (if missing)**

Create `EcomAgent/pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ecomagent"
version = "1.0.0"
description = "SEO optimization engine for e-commerce products"
requires-python = ">=3.9"
dependencies = [
    "openai>=1.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0"
]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

**Step 2: Install as editable package**
```bash
# From APEG repository root
cd ../EcomAgent
pip install -e .

# Verify installation
python -c "from src.seo_engine.engine import SEOEngine; print('✓ Import successful')"
```

**Step 3: Import in APEG**
```python
# APEG startup (src/apeg_core/orchestrators/seo_orchestrator.py)
from src.seo_engine.engine import SEOEngine

class SEOOrchestrator:
    def __init__(self):
        # Instantiate ONCE at startup, reuse for all calls
        self.engine = SEOEngine()
        # ... rest of init
```

**Advantages:**
- Clean imports (no path manipulation)
- Dependency tracking (pip shows ecomagent as installed)
- Version pinning possible

**Disadvantages:**
- Requires adding packaging config to EcomAgent (one-time setup)

---

#### Option B: PYTHONPATH-based Import (Alternative)

**No packaging required** - use direct path manipulation.

**Step 1: Add EcomAgent to Python path**
```python
# APEG startup (src/apeg_core/orchestrators/seo_orchestrator.py)
import sys
from pathlib import Path

# Add EcomAgent to path
ECOMAGENT_PATH = Path(__file__).parent.parent.parent.parent / "EcomAgent"
if str(ECOMAGENT_PATH) not in sys.path:
    sys.path.insert(0, str(ECOMAGENT_PATH))

# Now import works
from src.seo_engine.engine import SEOEngine
```

**Step 2: Verify path is correct**
```python
# On APEG startup
try:
    from src.seo_engine.engine import SEOEngine
    logger.info(f"✓ EcomAgent import successful from {ECOMAGENT_PATH}")
except ImportError as e:
    logger.error(f"✗ EcomAgent import failed: {e}")
    logger.error(f"Expected path: {ECOMAGENT_PATH}")
    logger.error(f"Path exists: {ECOMAGENT_PATH.exists()}")
    sys.exit(1)
```

**Advantages:**
- No packaging config needed
- Works immediately with existing code

**Disadvantages:**
- Path manipulation required on every startup
- Dependencies not tracked by pip
- Harder to version-pin

---

**Recommendation:** Use **Option A** (editable package install). The one-time packaging setup provides long-term stability and proper dependency management.

**Import Validation (Both Options):**
```python
# On APEG startup, verify EcomAgent is importable
try:
    from src.seo_engine.engine import SEOEngine
    
    # Verify required methods exist
    assert hasattr(SEOEngine, 'optimize_product'), "Missing optimize_product method"
    
    # Test instantiation
    engine = SEOEngine()
    
    logger.info("✓ EcomAgent import successful")
    logger.info(f"✓ SEOEngine version: {getattr(engine, '__version__', 'unknown')}")

except ImportError as e:
    logger.error(f"✗ EcomAgent import failed: {e}")
    logger.error("Solutions:")
    logger.error("  Option A: Run 'pip install -e ../EcomAgent' (requires pyproject.toml)")
    logger.error("  Option B: Verify PYTHONPATH includes EcomAgent directory")
    sys.exit(1)

except AssertionError as e:
    logger.error(f"✗ EcomAgent API contract mismatch: {e}")
    logger.error("EcomAgent version may be incompatible with APEG")
    sys.exit(1)
```

**Orchestrator Initialization:**
```python
class SEOOrchestrator:
    def __init__(self):
        # Instantiate ONCE at startup, reuse for all calls
        self.engine = SEOEngine()
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_SEO)
        self.retry_policy = RetryPolicy(
            max_attempts=config.RETRY_MAX_ATTEMPTS,
            base_delay=config.RETRY_BASE_DELAY_S,
            backoff_factor=config.RETRY_BACKOFF_FACTOR,
            jitter=config.RETRY_JITTER
        )
        
        logger.info("SEOOrchestrator initialized")
        logger.info(f"  Concurrency limit: {config.MAX_CONCURRENT_SEO}")
        logger.info(f"  Retry policy: {self.retry_policy.max_attempts} attempts")
```

### 3.3 Configuration Strategy

**Baseline Config (Hands-Off):**
- EcomAgent loads `rules/seo_baseline.yaml` relative to its own repository root
- APEG does NOT edit YAML files on disk (V1 constraint)

**Runtime Overrides (In-Memory):**
```python
# APEG can pass job-level or batch-level overrides
overrides = {
    "seasonal_tone": "Use festive Christmas language",
    "force_title_length": 80,
    "suppress_collections": ["Whispers"]
}

result = await optimize_product_async(
    product_data=canonical_product,
    overrides=overrides,  # Merged in-memory, not written to disk
    meta={"run_id": run_id, "batch_id": batch_id}
)
```

**V2 Enhancement:** Dynamic override API (pass overrides as parameters without filesystem mutation).

### 3.4 Public Orchestrator Interface

**Call Contract (The ONLY Supported Path for V1):**

```python
@dataclass
class SEOResult:
    """Response from EcomAgent (contract-shaped)"""
    product_id: str
    status: str  # "ok" | "error"
    new_title: Optional[str]
    new_description: Optional[str]
    new_tags: Optional[List[str]]
    new_meta_title: Optional[str]
    new_meta_description: Optional[str]
    apply_changes: Optional[bool]
    notes: Optional[str]
    error: Optional[Dict[str, str]]
    
    # Observability metadata (best-effort)
    model_name: Optional[str] = None
    model_latency_ms: Optional[int] = None
    token_usage_input: Optional[int] = None
    token_usage_output: Optional[int] = None
    capability_flags: List[str] = field(default_factory=list)  # e.g., ["no_token_tracking"]


async def optimize_product_async(
    product_data: Union[Dict, CanonicalProduct],
    overrides: Optional[Dict] = None,
    meta: Optional[Dict] = None
) -> SEOResult:
    """
    Async wrapper for EcomAgent.optimize_product (sync)
    
    Args:
        product_data: Full product payload (CanonicalProduct or dict)
            MUST include: product_id, handle, title, description_html,
                          tags, images, current_seo, shopify_data/etsy_data
        overrides: Runtime config overrides (tone, constraints, etc.)
        meta: Correlation metadata (run_id, batch_id) injected by APEG
    
    Returns:
        SEOResult with proposals, metadata, and observability data
    
    Raises:
        ValidationError: Invalid input (fail-fast, no retry)
        TimeoutError: LLM call timeout (retry-worthy)
    """
    # Implementation in Section 3.5
```

### 3.5 Concurrency & Batching

**Concurrency Control:**
```python
class SEOOrchestrator:
    def __init__(self):
        # Configurable semaphore (default: 3, max safe: 5)
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_SEO)
    
    async def process_batch(self, products: List[CanonicalProduct]) -> List[SEOResult]:
        """
        Process products with limited concurrency
        
        Respects MAX_CONCURRENT_SEO to prevent overwhelming:
        - LLM API rate limits
        - Raspberry Pi CPU/memory
        - Staging sheet write capacity
        """
        if not config.ENABLE_CONCURRENT_SEO:
            # Fallback: sequential processing
            results = []
            for product in products:
                result = await self.optimize_product_async(product)
                results.append(result)
            return results
        
        # Concurrent processing with semaphore
        async def process_with_limit(product):
            async with self.semaphore:
                return await self.optimize_product_async(product)
        
        results = await asyncio.gather(*[
            process_with_limit(p) for p in products
        ], return_exceptions=True)
        
        # Handle exceptions from gather
        processed = []
        for product, result in zip(products, results):
            if isinstance(result, Exception):
                logger.error(f"Product {product.product_id} failed: {result}")
                processed.append(SEOResult(
                    product_id=product.product_id,
                    status="error",
                    error={"code": "ORCHESTRATION_ERROR", "message": str(result)}
                ))
            else:
                processed.append(result)
        
        return processed
```

**Memory Management (Large Runs):**
```python
async def process_large_catalog(run_id: str, collection: str):
    """
    Process 5000+ products without exhausting Pi memory
    
    Strategy:
    1. Bulk fetch from Shopify → write JSONL to disk
    2. Stream JSONL in chunks (default: 50 products)
    3. Process chunk-by-chunk with concurrency limit
    4. Preserve idempotency via (run_id, product_id) keys
    """
    # Step 1: Bulk fetch and persist
    bulk_fetch_to_jsonl(
        collection=collection,
        output_path=f"/tmp/{run_id}_products.jsonl"
    )
    
    # Step 2: Stream chunks
    chunk_size = config.CHUNK_SIZE_PRODUCTS  # default: 50
    async for chunk in stream_jsonl_chunks(f"/tmp/{run_id}_products.jsonl", chunk_size):
        # Step 3: Process with concurrency
        results = await self.process_batch(chunk)
        
        # Step 4: Stream to staging (preserves idempotency)
        await staging_writer.write_batch(results)
```

### 3.6 Retry Policy & Error Handling

**Retry Configuration:**
```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_factor: float = 2.0
    jitter: bool = True
    
    def calculate_delay(self, attempt: int) -> float:
        """Exponential backoff with jitter"""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        if self.jitter:
            delay += random.uniform(0, 0.5)  # 0-500ms jitter
        return delay
```

**Error Classification:**
```python
# Retry-worthy errors (transient failures)
RETRY_WORTHY_ERRORS = (
    TimeoutError,
    ConnectionError,
    asyncio.TimeoutError,
    # HTTP 429 Rate Limit (if LLM API returns this)
)

# Fail-fast errors (permanent failures)
FAIL_FAST_ERRORS = (
    ValidationError,
    ValueError,
    KeyError,  # Missing required field
    # Schema violations, constraint errors
)
```

**Retry Implementation:**
```python
async def optimize_product_async(
    product_data: Union[Dict, CanonicalProduct],
    overrides: Optional[Dict] = None,
    meta: Optional[Dict] = None
) -> SEOResult:
    """Async wrapper with retry logic"""
    
    for attempt in range(self.retry_policy.max_attempts):
        try:
            # Wrap synchronous call in thread
            result = await asyncio.to_thread(
                self.engine.optimize_product,
                self._prepare_request(product_data, overrides, meta)
            )
            
            # Success - return immediately
            return self._parse_result(result)
        
        except FAIL_FAST_ERRORS as e:
            # Permanent failure - don't retry
            logger.error(f"Fail-fast error: {e}")
            return SEOResult(
                product_id=product_data.get("product_id"),
                status="error",
                error={"code": "VALIDATION_ERROR", "message": str(e)}
            )
        
        except RETRY_WORTHY_ERRORS as e:
            if attempt < self.retry_policy.max_attempts - 1:
                # Retry with backoff
                delay = self.retry_policy.calculate_delay(attempt)
                logger.warning(f"Retry {attempt+1}/{self.retry_policy.max_attempts} after {delay:.2f}s: {e}")
                await asyncio.sleep(delay)
            else:
                # Max retries exhausted
                logger.error(f"Max retries exhausted: {e}")
                return SEOResult(
                    product_id=product_data.get("product_id"),
                    status="error",
                    error={"code": "TIMEOUT_ERROR", "message": str(e)}
                )
```

**Failure Rate Safety Stop (Replaces Circuit Breaker):**
```python
async def process_batch(self, products: List[CanonicalProduct]) -> List[SEOResult]:
    """Process with failure rate monitoring"""
    results = []
    failures = 0
    
    for i, product in enumerate(products):
        result = await self.optimize_product_async(product)
        results.append(result)
        
        if result.status == "error":
            failures += 1
        
        # Check failure rate after every 10 products
        if (i + 1) % 10 == 0:
            failure_rate = failures / (i + 1)
            if failure_rate > config.FAILURE_RATE_STOP_THRESHOLD:  # default: 0.25
                logger.error(f"Failure rate {failure_rate:.1%} exceeds threshold. Stopping run.")
                # Mark remaining products as INTERRUPTED
                for remaining in products[i+1:]:
                    results.append(SEOResult(
                        product_id=remaining.product_id,
                        status="error",
                        error={"code": "RUN_STOPPED", "message": "Failure rate exceeded threshold"}
                    ))
                break
    
    return results
```

### 3.7 Staging Output (Streaming + Backpressure)

**Staging Sheet Schema:**
```
Columns (Minimum Required):
- run_id (str)
- product_id (str)
- handle (str)
- status (str): PENDING | DONE | FAILED | SKIPPED | INTERRUPTED
- strategy_tag (str, nullable)
- error_code (str, nullable)
- error_message (str, nullable)
- updated_at (datetime)

Optional Columns (Nice-to-Have):
- original_title
- proposed_title
- original_description
- proposed_description
```

**Streaming Writer with Backpressure:**
```python
class StagingSheetWriter:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.batch_size = config.SHEETS_BATCH_ROWS  # default: 20
        self.batch_interval = config.SHEETS_BATCH_INTERVAL_S  # default: 2
        self.degraded_mode = False
    
    async def write_result(self, result: SEOResult, run_id: str):
        """Queue a result for writing (non-blocking)"""
        await self.queue.put((result, run_id))
    
    async def writer_loop(self):
        """Background task: batch writes to Google Sheets"""
        batch = []
        
        while True:
            try:
                # Wait for results or timeout
                result, run_id = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=self.batch_interval
                )
                batch.append((result, run_id))
                
                # Flush batch if full
                if len(batch) >= self.batch_size:
                    await self._flush_batch(batch)
                    batch = []
            
            except asyncio.TimeoutError:
                # Flush partial batch on timeout
                if batch:
                    await self._flush_batch(batch)
                    batch = []
    
    async def _flush_batch(self, batch: List[Tuple[SEOResult, str]]):
        """Write batch to Google Sheets with degradation handling"""
        if self.degraded_mode:
            # Skip Sheets, write to DB only
            await self._write_to_db_only(batch)
            return
        
        try:
            # Attempt Sheets write
            await google_sheets_api.append_rows(batch)
            # Also write to DB (dual storage)
            await self._write_to_db(batch)
        
        except GoogleSheetsRateLimitError:
            logger.warning("Google Sheets rate limit hit - degrading to DB-only")
            self.degraded_mode = True
            await self._write_to_db_only(batch)
            # Mark run as STAGING_DEGRADED
            await db.update_run_status(run_id, staging_degraded=True)
```

### 3.8 Idempotency & Resume Logic

**Database Schema:**
```sql
-- Run-level tracking
CREATE TABLE seo_runs (
    run_id TEXT PRIMARY KEY,
    collection TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    total_products INTEGER,
    completed_count INTEGER,
    failed_count INTEGER,
    status TEXT,  -- RUNNING | COMPLETED | INTERRUPTED | FAILED
    staging_degraded BOOLEAN DEFAULT FALSE
);

-- Product-level tracking (source of truth)
CREATE TABLE seo_run_items (
    run_id TEXT,
    product_id TEXT,
    handle TEXT,
    status TEXT,  -- PENDING | DONE | FAILED | SKIPPED | INTERRUPTED
    strategy_tag TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (run_id, product_id)
);
```

**Idempotency Key:** `(run_id, product_id)`

**Resume Detection:**
```python
async def should_process_product(run_id: str, product_id: str) -> bool:
    """
    Determine if product needs processing
    
    Rule: If DONE exists in DB for (run_id, product_id) → skip
    Do NOT rely on staging sheet status (may be stale/incomplete)
    """
    status = await db.get_item_status(run_id, product_id)
    
    if status == "DONE":
        logger.debug(f"Skipping {product_id} - already DONE")
        return False
    
    # Process if: PENDING, FAILED, INTERRUPTED, or not in DB
    return True
```

**Resume from Interruption:**
```python
async def resume_run(run_id: str):
    """Resume an interrupted run"""
    run = await db.get_run(run_id)
    
    if run.status not in ["RUNNING", "INTERRUPTED"]:
        raise ValueError(f"Cannot resume run with status: {run.status}")
    
    # Fetch original product list
    products = await fetch_products_for_collection(run.collection)
    
    # Filter to unprocessed items
    unprocessed = [
        p for p in products
        if await should_process_product(run_id, p.product_id)
    ]
    
    logger.info(f"Resuming run {run_id}: {len(unprocessed)} products remaining")
    
    # Process with same logic as new run
    await process_batch(unprocessed, run_id=run_id)
```

### 3.9 Version Control

**Version Increment Timing (Critical):**
```python
# WRONG: Increment version before approval
product.version += 1  # ✗ Don't do this

# RIGHT: Increment ONLY after Shopify confirms update
async def apply_approved_changes(run_id: str):
    """Apply changes after human approval"""
    approved_items = await db.get_approved_items(run_id)
    
    for item in approved_items:
        # Fetch canonical product
        product = await db.get_canonical_product(item.product_id)
        
        # Apply to Shopify
        success = await shopify_api.update_product(product)
        
        if success:
            # NOW increment version (post-confirmation)
            product.version += 1
            product.updated_at = datetime.utcnow()
            await db.save_canonical_product(product)
            
            logger.info(f"Product {product.product_id} updated to version {product.version}")
```

**EcomAgent Statelessness:**
- EcomAgent receives `current_version` as input (optional field in request)
- EcomAgent returns proposed content WITHOUT mutating version
- APEG is sole authority for version increments

### 3.10 Observability Metadata

**Required Fields in SEOResult:**
```python
@dataclass
class SEOResult:
    # ... (core fields from 3.4)
    
    # Observability metadata (best-effort)
    model_name: Optional[str] = None  # e.g., "gpt-4-turbo"
    model_latency_ms: Optional[int] = None  # LLM call duration
    token_usage_input: Optional[int] = None
    token_usage_output: Optional[int] = None
    capability_flags: List[str] = field(default_factory=list)
```

**Capability Flags (When Metadata Unavailable):**
```python
# If LLM API doesn't return token counts
result.capability_flags = ["no_token_tracking"]

# If model name not detectable
result.capability_flags = ["no_model_name"]
```

**Cost Analysis (Future Use):**
```sql
-- Aggregate observability data for cost per optimization
SELECT 
    AVG(model_latency_ms) as avg_latency,
    SUM(token_usage_input + token_usage_output) as total_tokens,
    COUNT(*) as optimization_count
FROM seo_run_items
WHERE run_id = 'run_20241228_123456'
  AND model_name = 'gpt-4-turbo';
```

### 3.11 Cancellation & Graceful Shutdown

**Stop Button Semantics:**
```python
class SEOOrchestrator:
    def __init__(self):
        self.cancellation_requested = False
    
    async def process_batch(self, products: List[CanonicalProduct], run_id: str):
        """Process with cancellation support"""
        try:
            for product in products:
                # Check cancellation before processing each product
                if self.cancellation_requested:
                    logger.info("Cancellation requested - stopping new work")
                    break
                
                result = await self.optimize_product_async(product)
                await staging_writer.write_result(result, run_id)
        
        except asyncio.CancelledError:
            logger.warning("Async task cancelled")
            raise  # Re-raise to trigger finally block
        
        finally:
            # Ensure cleanup even if cancelled
            await self._cleanup_run(run_id)
    
    async def _cleanup_run(self, run_id: str):
        """Graceful shutdown procedure"""
        logger.info(f"Cleaning up run {run_id}")
        
        # 1. Flush staging writer queue
        await staging_writer.flush()
        
        # 2. Mark run as INTERRUPTED
        await db.update_run_status(run_id, status="INTERRUPTED")
        
        # 3. Mark unprocessed items as INTERRUPTED
        await db.mark_unprocessed_items(run_id, status="INTERRUPTED")
        
        logger.info(f"Run {run_id} cleanup complete")
```

**Important:** Cannot hard-kill `asyncio.to_thread` calls safely. In-flight calls must complete before shutdown.

### 3.12 Configuration Reference

**Required Config Flags (V1):**
```python
# src/apeg_core/config.py
class SEOConfig:
    # Concurrency
    MAX_CONCURRENT_SEO: int = 3
    ENABLE_CONCURRENT_SEO: bool = True
    
    # Retry policy
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BASE_DELAY_S: float = 1.0
    RETRY_BACKOFF_FACTOR: float = 2.0
    RETRY_JITTER: bool = True
    
    # Staging sheet
    SHEETS_WRITE_MODE: str = "stream"  # stream | batch
    SHEETS_BATCH_ROWS: int = 20
    SHEETS_BATCH_INTERVAL_S: float = 2.0
    
    # Safety
    FAILURE_RATE_STOP_THRESHOLD: float = 0.25  # Stop if >25% fail
    
    # Memory management
    CHUNK_SIZE_PRODUCTS: int = 50  # JSONL streaming chunk size
```

### 3.13 Product Discovery (Entrypoint)

**V1 Selection Methods (Must Choose ONE):**

```python
# Method 1: By Collection
products = await shopify_api.fetch_products_by_collection("Birthstone Jewelry")

# Method 2: By Tag
products = await shopify_api.fetch_products_by_tag("needs-seo-update")

# Method 3: Explicit List
products = await shopify_api.fetch_products_by_ids([
    "gid://shopify/Product/123",
    "gid://shopify/Product/456"
])
```

**Critical:** V1 spec must define which method is used. Recommendation: **By Collection** (aligns with existing workflow).

### 3.14 Logging Ownership

**APEG Logger (Orchestration):**
```python
logger.info(
    "Processing product",
    extra={
        "run_id": run_id,
        "product_id": product_id,
        "attempt": attempt,
        "status": "starting"
    }
)
```

**EcomAgent Logger (Internal Decisions):**
```python
# EcomAgent logs its own decisions with run_id correlation
logger.debug(
    "Applied constraint: title truncated",
    extra={
        "run_id": run_id,  # Passed from APEG via meta
        "original_length": 85,
        "truncated_length": 70
    }
)
```

**Log Aggregation:** Both loggers write to same destination (systemd journal or file) with run_id for correlation.

---

**V2 Enhancements (Out of Scope for V1):**
- GraphQL-only mode (skip REST/JSONL intermediate)
- Bulk mutation API (direct productUpdate batches)
- Dynamic override API (pass config as params, no YAML at all)
- Real-time metrics dashboard (track progress via WebSocket)
- Auto-approval for low-risk changes (based on confidence scores)

---

## 4. N8N Staging Layer (Google Sheets)

**Purpose:** Provide mobile-friendly human approval interface for SEO changes before they're published to Shopify/Etsy. Implements streaming updates, degraded mode safety, and single-run enforcement.

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    APEG (Orchestrator)                           │
│  Generates SEO proposals, streams to N8N                        │
└───────────┬─────────────────────────────────────────────────────┘
            │ HTTP POST (streaming)
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                N8N Ingestion Workflow                            │
│  1. Check for active PENDING run (enforce single run)           │
│  2. Clear staging sheet range (A2:Z)                            │
│  3. Write metadata row (run_id, timestamp, status)              │
│  4. Stream results to sheet with throttling (20 rows/2s)        │
│  5. Handle degraded mode (Sheets API failures)                  │
└───────────┬─────────────────────────────────────────────────────┘
            │ Writes to
            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Google Sheets (Staging UI)                          │
│  Columns: run_id | product_id | handle | status | original_    │
│           title | proposed_title | shopify_admin_link | ...    │
└───────────┬─────────────────────────────────────────────────────┘
            │ Human edits status: PENDING → APPROVED
            │ Triggers via Apps Script onChange
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                N8N Executor Workflow                             │
│  1. Verify status == APPROVED (edge trigger idempotency)        │
│  2. Check processed_at cell is EMPTY                            │
│  3. Verify DB status != DONE (triple-check)                     │
│  4. Execute Shopify GraphQL Bulk Operation                      │
│  5. Mark processed_at timestamp                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Google Sheets Schema

**Sheet Name:** `SEO_Staging` (persistent sheet, cleared per run)

**Metadata Row (Row 1):**
```
A1: run_id           B1: run_timestamp      C1: run_status      D1: shop_admin_base_url
A2: run_123456       B2: 2024-12-28 14:30   C2: PENDING         D2: https://kfmah5-gr.myshopify.com/admin
```

**Header Row (Row 3):**
```
A3: run_id
B3: product_id
C3: handle
D3: status
E3: original_title
F3: proposed_title
G3: original_description
H3: proposed_description
I3: original_tags
J3: proposed_tags
K3: strategy_tag
L3: shopify_admin_link
M3: error_code
N3: error_message
O3: processed_at
P3: updated_at
```

**Data Rows (Row 4+):**
Example:
```
A4: run_123456
B4: gid://shopify/Product/7796940308582
C4: handmade-sterling-silver-tanzanite-anklet
D4: PENDING
E4: Sterling Silver Tanzanite Anklet
F4: Handcrafted Tanzanite December Birthstone Anklet - Premium...
G4: <Original HTML description>
H4: <Proposed HTML description>
I4: December Birthstone, Sterling Silver
J4: December Birthstone, Tanzanite Jewelry, Handcrafted
K4: high-value-birthstone
L4: =HYPERLINK("https://kfmah5-gr.myshopify.com/admin/products/7796940308582", "View Product")
M4: [empty]
N4: [empty]
O4: [empty - set after execution]
P4: 2024-12-28 14:32:15
```

### 4.3 Authentication & Setup

**Google Sheets API Access:**
1. N8N uses **OAuth 2.0** (user grant) for Google Sheets
2. Setup: N8N Settings → Credentials → Add Google Sheets OAuth2
3. Grant permissions: `https://www.googleapis.com/auth/spreadsheets`

**Sheet Preparation (One-Time):**
1. Create sheet named `SEO_Staging`
2. Set sharing: Owner (you) + N8N service account (if using service account) OR just owner if OAuth
3. Note Sheet ID from URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`

**Configuration:**
```javascript
// N8N workflow variables
const SHEET_ID = "{{$env.GOOGLE_SHEETS_STAGING_ID}}";
const SHOP_ADMIN_BASE_URL = "{{$env.SHOPIFY_ADMIN_BASE_URL}}";  // e.g., https://kfmah5-gr.myshopify.com/admin
```

### 4.4 N8N Ingestion Workflow

**Trigger:** HTTP POST from APEG

**Node 1: Single Run Enforcement**
```javascript
// Check if there's an active PENDING run
const sheets = $node["Google Sheets"].json;
const metadataRow = sheets.values[0];  // Row 1

const currentRunStatus = metadataRow[2];  // C1: run_status

if (currentRunStatus === "PENDING") {
  // Active run exists - REJECT or QUEUE
  return {
    json: {
      error: "ACTIVE_RUN_EXISTS",
      message: "Cannot start new run while previous run is PENDING approval",
      active_run_id: metadataRow[0],  // A1: run_id
      active_run_timestamp: metadataRow[1]
    }
  };
}

// No active run - proceed
return { json: { proceed: true } };
```

**Node 2: Clear Staging Sheet**
```javascript
// Clear data range (preserve headers)
// Range: A2:Z (clears metadata + all data rows)
const clearRange = "A2:Z";

return {
  json: {
    spreadsheetId: SHEET_ID,
    range: clearRange,
    values: [[]]  // Empty array clears range
  }
};
```

**Node 3: Write Metadata Row**
```javascript
// Write run metadata to row 1
const runId = $json.run_id;
const timestamp = new Date().toISOString();

return {
  json: {
    spreadsheetId: SHEET_ID,
    range: "A1:D1",
    values: [[
      runId,
      timestamp,
      "PENDING",
      SHOP_ADMIN_BASE_URL
    ]]
  }
};
```

**Node 4: Stream Results with Throttling**
```javascript
// N8N nodes:
// 1. SplitInBatches (batch size: 20)
// 2. Google Sheets Append
// 3. Wait (2 seconds)
// 4. Loop back to SplitInBatches

// Format each result for Sheets
const result = $json;

const row = [
  result.run_id,
  result.product_id,
  result.handle,
  "PENDING",  // Initial status
  result.original_title,
  result.proposed_title,
  result.original_description,
  result.proposed_description,
  result.original_tags ? result.original_tags.join(", ") : "",
  result.proposed_tags ? result.proposed_tags.join(", ") : "",
  result.strategy_tag || "",
  `=HYPERLINK("${SHOP_ADMIN_BASE_URL}/products/${result.product_id.split('/').pop()}", "View Product")`,
  result.error_code || "",
  result.error_message || "",
  "",  // processed_at (empty until execution)
  new Date().toISOString()  // updated_at
];

return {
  json: {
    spreadsheetId: SHEET_ID,
    range: "A4:P",  // Append to data rows
    values: [row]
  }
};
```

**Node 5: Degraded Mode Handler**
```javascript
// If Google Sheets API returns 429 or 500
const error = $json.error;

if (error && (error.code === 429 || error.code >= 500)) {
  // DEGRADED MODE: Write to DB only, mark run as STAGING_DEGRADED
  
  // Log to APEG database
  await db.saveResults(results, { staging_degraded: true });
  
  // Update run status
  await db.updateRunStatus(runId, { 
    status: "STAGING_DEGRADED",
    notes: "Google Sheets unavailable - results saved to DB only"
  });
  
  // Send notification
  await sendNotification({
    type: "WARNING",
    message: `Run ${runId} degraded: Staging failed. Review/approve via CLI or retry staging later.`,
    urgency: "high"
  });
  
  // CRITICAL: Do NOT proceed to Executor workflow
  // Human must manually approve via DB/CLI before execution
  
  return {
    json: {
      degraded: true,
      message: "Staging degraded - execution PAUSED"
    }
  };
}

// Normal mode - continue
return { json: { degraded: false } };
```

### 4.5 Approval Mechanism

**Status Column (D) Values:**
- `PENDING` - Awaiting human review
- `APPROVED` - Ready for execution
- `REJECTED` - Human rejected this change
- `EXPIRED` - Timeout reached (12h default)

**Approval Trigger (Apps Script):**

Google Sheets → Extensions → Apps Script

```javascript
// Triggered on cell edit
function onEdit(e) {
  const sheet = e.source.getActiveSheet();
  const range = e.range;
  
  // Only trigger on status column (D) edits
  if (range.getColumn() !== 4) return;
  
  const row = range.getRow();
  if (row < 4) return;  // Skip metadata and header rows
  
  const newStatus = range.getValue();
  
  if (newStatus === "APPROVED") {
    // Trigger N8N Executor workflow via webhook
    const webhookUrl = "https://n8n.your-domain.com/webhook/seo-executor";
    
    const rowData = sheet.getRange(row, 1, 1, 16).getValues()[0];
    
    const payload = {
      run_id: rowData[0],
      product_id: rowData[1],
      handle: rowData[2],
      status: rowData[3],
      proposed_title: rowData[5],
      proposed_description: rowData[7],
      proposed_tags: rowData[9],
      row_number: row
    };
    
    UrlFetchApp.fetch(webhookUrl, {
      method: "POST",
      contentType: "application/json",
      payload: JSON.stringify(payload)
    });
  }
}
```

### 4.6 N8N Executor Workflow

**Trigger:** Webhook from Apps Script (status changed to APPROVED)

**Node 1: Edge Trigger Idempotency (CRITICAL)**
```javascript
// Triple-check to prevent double execution
const payload = $json;

// Check 1: Status is APPROVED
if (payload.status !== "APPROVED") {
  return { json: { skip: true, reason: "Status not APPROVED" } };
}

// Check 2: processed_at cell is EMPTY
const sheet = await googleSheets.getRange(SHEET_ID, `O${payload.row_number}`);
if (sheet.values[0][0]) {  // If processed_at has a value
  return { json: { skip: true, reason: "Already processed (timestamp exists)" } };
}

// Check 3: DB confirms item is not DONE
const dbStatus = await db.getItemStatus(payload.run_id, payload.product_id);
if (dbStatus === "DONE") {
  return { json: { skip: true, reason: "DB shows DONE - preventing double execution" } };
}

// All checks passed - proceed with execution
return { json: { proceed: true } };
```

**Node 2: Fetch Canonical Product**
```javascript
// Fetch full product data from APEG DB
const product = await db.getCanonicalProduct(payload.product_id);

// Fetch existing tags for hydration (CRITICAL - prevent tag loss)
const existingTags = await shopifyGraphQL.query(`
  query {
    product(id: "${payload.product_id}") {
      tags
    }
  }
`);

return {
  json: {
    product: product,
    existing_tags: existingTags.data.product.tags,
    proposed_changes: payload
  }
};
```

**Node 3: Build Shopify GraphQL Mutation**
```javascript
// Use Canonical Product Model export method
const shopifyPayload = product.to_shopify(existing_tags);

// Build GraphQL mutation
const mutation = `
  mutation productUpdate($input: ProductInput!) {
    productUpdate(input: $input) {
      product {
        id
        title
        descriptionHtml
        seo {
          title
          description
        }
      }
      userErrors {
        field
        message
      }
    }
  }
`;

const variables = {
  input: shopifyPayload
};

return {
  json: {
    mutation: mutation,
    variables: variables
  }
};
```

**Node 4: Execute Shopify GraphQL**
```javascript
// Execute mutation
const response = await shopifyGraphQL.mutate(mutation, variables);

// Check for errors
if (response.data.productUpdate.userErrors.length > 0) {
  const errors = response.data.productUpdate.userErrors;
  
  // Log error
  await db.updateItemStatus(payload.run_id, payload.product_id, {
    status: "FAILED",
    error_code: "SHOPIFY_MUTATION_ERROR",
    error_message: JSON.stringify(errors)
  });
  
  // Update sheet
  await googleSheets.updateCell(SHEET_ID, `M${payload.row_number}`, "SHOPIFY_ERROR");
  await googleSheets.updateCell(SHEET_ID, `N${payload.row_number}`, errors[0].message);
  
  return {
    json: {
      success: false,
      errors: errors
    }
  };
}

// Success - increment version and mark DONE
const updatedProduct = response.data.productUpdate.product;

// Increment version in APEG DB (post-confirmation)
await db.incrementProductVersion(payload.product_id);

// Mark item as DONE
await db.updateItemStatus(payload.run_id, payload.product_id, {
  status: "DONE"
});

return {
  json: {
    success: true,
    product: updatedProduct
  }
};
```

**Node 5: Mark Processed Timestamp**
```javascript
// Write timestamp to processed_at column (O)
// This prevents double-execution even if Apps Script triggers again

const timestamp = new Date().toISOString();

await googleSheets.updateCell(SHEET_ID, `O${payload.row_number}`, timestamp);

return {
  json: {
    processed_at: timestamp,
    complete: true
  }
};
```

### 4.7 Timeout & Cleanup

**Scheduled Job (Every 12 Hours):**
```javascript
// Check for expired PENDING runs
const metadataRow = await googleSheets.getRange(SHEET_ID, "A1:C1");
const runStatus = metadataRow.values[0][2];
const runTimestamp = new Date(metadataRow.values[0][1]);

if (runStatus === "PENDING") {
  const hoursSincePending = (Date.now() - runTimestamp) / (1000 * 60 * 60);
  
  if (hoursSincePending > 12) {  // Configurable timeout
    // Mark run as EXPIRED
    await googleSheets.updateCell(SHEET_ID, "C1", "EXPIRED");
    
    // Update DB
    await db.updateRunStatus(runId, {
      status: "EXPIRED",
      notes: "Approval timeout exceeded (12 hours)"
    });
    
    // Notify
    await sendNotification({
      type: "INFO",
      message: `Run ${runId} expired after 12 hours without approval. Sheet is now available for new runs.`
    });
  }
}
```

### 4.8 Error Handling Matrix

| Error Condition | Action | Status Update |
|----------------|--------|---------------|
| Google Sheets API 429 (rate limit) | Enter degraded mode, write to DB only, PAUSE executor | `STAGING_DEGRADED` |
| Google Sheets API 500 (server error) | Retry 3x with backoff, then degrade | `STAGING_DEGRADED` |
| Active PENDING run exists | Reject new run with 409 Conflict | Return error to APEG |
| Shopify GraphQL mutation error | Mark item FAILED, log to sheet + DB | Item: `FAILED` |
| Double-execution attempt detected | Skip execution, log warning | No change (already `DONE`) |
| Approval timeout (12h) | Mark run EXPIRED, notify human | `EXPIRED` |

### 4.9 Configuration Reference

**N8N Environment Variables:**
```bash
GOOGLE_SHEETS_STAGING_ID=1ABC...XYZ
SHOPIFY_ADMIN_BASE_URL=https://kfmah5-gr.myshopify.com/admin
STAGING_TIMEOUT_HOURS=12
SHEETS_BATCH_SIZE=20
SHEETS_BATCH_DELAY_MS=2000
```

**Degraded Mode Behavior:**
- Sheets API failures do NOT block SEO generation
- Results saved to APEG database (`seo_run_items` table)
- Executor workflow PAUSED (requires manual intervention)
- Human notified via configured channel (email/Slack)
- Run marked `STAGING_DEGRADED` for visibility

**Single Run Enforcement:**
- Only one run can have status `PENDING` at a time
- New run attempts while PENDING → Return `409 Conflict`
- Alternative: Queue runs (V2 enhancement)
- Run becomes available after: APPROVED (all rows processed), REJECTED (manual), or EXPIRED (timeout)

### 4.10 Mobile Review Workflow

**Typical User Experience:**
1. Receive notification: "SEO run ready for review"
2. Open Google Sheets on mobile
3. Review original vs proposed changes
4. Tap "View Product" link → Opens Shopify admin
5. Change status from `PENDING` to `APPROVED` (or `REJECTED`)
6. Apps Script triggers N8N Executor
7. Receive confirmation: "Changes applied to Shopify"

**Sheet Optimizations for Mobile:**
- Freeze header rows (1-3)
- Set column widths: Status (80px), Titles (200px), Descriptions (300px)
- Use data validation dropdown for status column (PENDING | APPROVED | REJECTED)
- Hyperlinked product IDs for quick access

---

**V2 Enhancements (Out of Scope):**
- Multi-run support with tabbed sheets
- Partial approval (approve individual rows, not all-or-nothing)
- Inline editing (modify proposed title directly in sheet)
- Rollback capability (undo applied changes)
- Automated approval for high-confidence changes (based on safety score)

---

## 5. Shopify GraphQL Bulk Operations

**Purpose:** Execute large-scale product updates (50-5,000+ products) via Shopify's GraphQL Bulk Operations API with safety guarantees: idempotent execution, per-row success tracking, tag hydration, and robust error handling.

### 5.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    APEG (Orchestrator)                           │
│  1. Generate JSONL payload from approved changes                │
│  2. Acquire exclusive lock (1 bulk op at a time)                │
│  3. Upload to Google Cloud Storage (GCS)                        │
│  4. Start Shopify Bulk Operation                                │
│  5. Poll status + listen for webhook                            │
│  6. Download result JSONL, parse per-row success                │
│  7. Retry failures via REST API (fallback)                      │
│  8. Release lock, mark run complete                             │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Upload JSONL
┌─────────────────────────────────────────────────────────────────┐
│           Google Cloud Storage (Shopify-Managed)                 │
│  Staged uploads endpoint (time-limited signed URL)              │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ bulkOperationRunMutation
┌─────────────────────────────────────────────────────────────────┐
│           Shopify GraphQL Bulk Operations                        │
│  Status: CREATED → RUNNING → COMPLETED                          │
│  Result: JSONL file with per-row success/errors                 │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Webhook: BULK_OPERATIONS_FINISH
┌─────────────────────────────────────────────────────────────────┐
│                APEG Result Processor                             │
│  Parse output JSONL, extract userErrors, update DB              │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Batching Strategy (Variable by File Size)

**Constraint:** Shopify's hard limit for bulk operation JSONL files is 100MB.

**Configuration:**
```python
class BulkOperationConfig:
    TARGET_JSONL_MB: int = 20  # Start conservative (operational target)
    MAX_JSONL_MB: int = 100    # Shopify's hard cap (do not exceed)
    CHUNK_PRODUCTS_ESTIMATE: int = 250  # Rough estimate for planning
```

**Batching Logic:**
- **Operational target:** 50-80MB per batch (safe margin for reliability)
- **Hard cap:** 100MB (Shopify enforces this limit)
- **Default:** 20MB (conservative starting point)

**Batch Generation Logic:**
```python
async def generate_bulk_batches(products: List[CanonicalProduct]) -> List[Path]:
    """
    Split products into JSONL files by size, not count
    
    Returns list of JSONL file paths, each under MAX_JSONL_MB
    """
    batches = []
    current_batch = []
    current_size_mb = 0
    
    for product in products:
        # Serialize to JSONL line
        jsonl_line = product.to_shopify_bulk_jsonl()
        line_size_mb = len(jsonl_line.encode('utf-8')) / (1024 * 1024)
        
        # Check if adding this product would exceed target
        if current_size_mb + line_size_mb > config.TARGET_JSONL_MB:
            # Save current batch
            batch_file = await save_batch_to_jsonl(current_batch)
            batches.append(batch_file)
            
            # Start new batch
            current_batch = [product]
            current_size_mb = line_size_mb
        else:
            current_batch.append(product)
            current_size_mb += line_size_mb
    
    # Save final batch
    if current_batch:
        batch_file = await save_batch_to_jsonl(current_batch)
        batches.append(batch_file)
    
    logger.info(f"Generated {len(batches)} batches (target: {config.TARGET_JSONL_MB}MB each)")
    return batches
```

### 5.3 JSONL Payload Generation (Type Safety)

**CRITICAL: Strict Type Serialization**

```python
def to_shopify_bulk_jsonl(self, existing_tags: List[str]) -> str:
    """
    Generate JSONL line for Shopify Bulk Operation
    
    CRITICAL TYPE SAFETY:
    - All IDs must be strings
    - All Decimal values must be strings (not floats)
    - Tags must be hydrated and merged (prevent data loss)
    
    Returns:
        Single JSONL line (no newline at end)
    """
    # Hydrate tags (CRITICAL - prevent tag loss)
    merged_tags = list(dict.fromkeys(self.tags + existing_tags))
    
    # Build mutation input with strict types
    input_data = {
        "id": str(self.shopify_id),  # MUST be string
        "title": self.title,
        "descriptionHtml": self.description_html,
        "tags": merged_tags,  # Full merged set
        "seo": {
            "title": self.meta_title or self.title[:70],
            "description": self.meta_description or ""
        }
    }
    
    # If price is present, cast to string (CRITICAL)
    if self.price:
        input_data["variants"] = [{
            "price": str(self.price)  # Decimal → String
        }]
    
    # JSONL format: {"input": {...}}
    return json.dumps({"input": input_data}, ensure_ascii=False)
```

**Example JSONL Output:**
```jsonl
{"input":{"id":"gid://shopify/Product/123","title":"Sterling Silver Tanzanite Anklet","descriptionHtml":"<p>Handcrafted...</p>","tags":["December Birthstone","Tanzanite","Sterling Silver"],"seo":{"title":"Handcrafted Tanzanite Anklet - December Birthstone","description":"Discover our handcrafted sterling silver Tanzanite anklet..."}}}
{"input":{"id":"gid://shopify/Product/456","title":"Gold Garnet Necklace","descriptionHtml":"<p>Elegant...</p>","tags":["January Birthstone","Garnet","Gold"],"seo":{"title":"Elegant Gold Garnet Necklace - January Birthstone","description":"Experience the beauty of our gold Garnet necklace..."}}}
```

### 5.4 Upload to Google Cloud Storage (CRITICAL: Multipart Order)

**The Multipart Upload Order Rule (⚠️ UNVERIFIED - Integration Reality):**

Google Cloud Storage (GCS) validates the signature **before** accepting file content. If the file is sent first, GCS cannot validate the policy against the content length and will reject the upload.

**NOTE:** This constraint is not explicitly documented by Shopify but is a verified integration reality. **Testing Required:** Validate field ordering in N8N before committing to production uploads.

**CORRECT Implementation:**
```python
import aiohttp

async def upload_to_gcs(jsonl_file: Path, upload_params: Dict) -> str:
    """
    Upload JSONL to Google Cloud Storage via Shopify's staged upload URL
    
    CRITICAL: Authentication parameters MUST appear BEFORE file content
    in the multipart form data
    
    Args:
        jsonl_file: Path to JSONL batch file
        upload_params: From stagedUploadsCreate mutation
    
    Returns:
        Uploaded file key for bulkOperationRunMutation
    """
    # Extract parameters (from Shopify's stagedUploadsCreate response)
    url = upload_params['url']
    parameters = upload_params['parameters']
    
    # Build ordered form data (order matters!)
    form = aiohttp.FormData()
    
    # Step 1: Add authentication parameters FIRST
    for param in parameters:
        form.add_field(param['name'], param['value'])
    
    # Step 2: Add file content LAST
    form.add_field(
        'file',
        open(jsonl_file, 'rb'),
        filename=jsonl_file.name,
        content_type='text/jsonl'
    )
    
    # Step 3: Upload
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=form) as response:
            if response.status != 201:
                error_text = await response.text()
                raise Exception(f"GCS upload failed: {response.status} - {error_text}")
            
            logger.info(f"✓ Uploaded {jsonl_file.name} to GCS")
            return upload_params['resourceUrl']
```

**WRONG Implementation (Will Fail):**
```python
# ✗ WRONG: File added before authentication parameters
form.add_field('file', ...)  # File first
form.add_field('GoogleAccessId', ...)  # Auth second → REJECTED
```

### 5.5 Bulk Operation Execution (Idempotency)

**Identity & Idempotency (Addition #1):**

```python
@dataclass
class BulkOperationRecord:
    """Database record for bulk operation tracking"""
    run_id: str
    batch_id: str
    bulk_operation_id: Optional[str]  # Shopify's GID
    status: str  # CREATED | RUNNING | COMPLETED | FAILED
    jsonl_file_path: str
    mutation_hash: str  # Hash of intended mutations
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result_url: Optional[str]
    webhook_received: bool
    row_count: int
    success_count: int
    error_count: int

async def start_bulk_operation(
    run_id: str,
    batch_id: str,
    jsonl_file: Path,
    mutation_type: str = "productUpdate"
) -> BulkOperationRecord:
    """
    Start Shopify Bulk Operation with idempotency tracking
    
    CRITICAL: Persist record BEFORE execution to enable resume
    """
    # Generate mutation hash for idempotency
    mutation_hash = hashlib.sha256(jsonl_file.read_bytes()).hexdigest()
    
    # Check if this exact mutation already executed
    existing = await db.get_bulk_operation(run_id, batch_id, mutation_hash)
    if existing and existing.status == "COMPLETED":
        logger.info(f"Bulk operation already completed: {existing.bulk_operation_id}")
        return existing
    
    # Step 1: Create staged upload
    staged_upload = await shopify_graphql.mutation("""
        mutation {
          stagedUploadsCreate(input: [{
            resource: BULK_MUTATION_VARIABLES,
            filename: "bulk-products.jsonl",
            mimeType: "text/jsonl",
            httpMethod: POST
          }]) {
            stagedTargets {
              url
              resourceUrl
              parameters {
                name
                value
              }
            }
            userErrors {
              field
              message
            }
          }
        }
    """)
    
    if staged_upload['data']['stagedUploadsCreate']['userErrors']:
        raise Exception("Staged upload creation failed")
    
    # Step 2: Upload JSONL to GCS (HARD GATE - SHOP-03 VERIFIED)
    # CRITICAL: Upload is a hard-gated step. If upload fails, do NOT call bulkOperationRunMutation.
    # Evidence: Failed upload causes "JSONL file could not be found" error
    # Avoid shell eval/quoting issues - use requests library or curl without eval
    upload_target = staged_upload['data']['stagedUploadsCreate']['stagedTargets'][0]
    
    try:
        staged_url = await upload_to_gcs(jsonl_file, upload_target)
    except Exception as e:
        logger.error(f"Staged upload FAILED - aborting bulk mutation: {e}")
        raise Exception(f"HARD GATE: Upload failed, cannot proceed to bulkOperationRunMutation: {e}")
    
    # Step 3: Start bulk operation
    # CRITICAL: stagedUploadPath MUST be a Shopify-staged bulk upload path
    # - NEVER use local filesystem paths (e.g., /tmp/file.jsonl)
    # - MUST match Shopify-provided bulk/ bucket path from stagedUploadsCreate
    # Evidence: bulkOperationRunMutation rejects non-staged paths (dev-store test)
    #
    # Required sequence:
    # 1) stagedUploadsCreate (resource: BULK_MUTATION_VARIABLES)
    # 2) multipart upload JSONL to returned URL using returned form fields
    # 3) bulkOperationRunMutation(..., stagedUploadPath: <returned resourceUrl>)
    #
    # CONSTRAINT: Mutation limited to ONE connection field in selection set
    bulk_op_response = await shopify_graphql.mutation("""
        mutation($stagedUploadPath: String!) {
          bulkOperationRunMutation(
            mutation: "mutation call { productUpdate(input: $input) { product { id title descriptionHtml } userErrors { message field } } }",
            stagedUploadPath: $stagedUploadPath
          ) {
            bulkOperation {
              id
              status
              url
              partialDataUrl
            }
            userErrors {
              field
              message
            }
          }
        }
    """, variables={"stagedUploadPath": staged_url})

**CRITICAL: groupObjects Parameter**

`groupObjects` is **query-only** (for `bulkOperationRunQuery`).
It is NOT accepted for `bulkOperationRunMutation` and will cause schema validation errors.
Do NOT include it in mutation variables.
    
    # Check for immediate errors (Addition #3: Start Failure Handling)
    user_errors = bulk_op_response['data']['bulkOperationRunMutation']['userErrors']
    if user_errors:
        logger.error(f"Bulk operation start failed: {user_errors}")
        raise Exception(f"Bulk operation rejected: {user_errors[0]['message']}")
    
    bulk_op = bulk_op_response['data']['bulkOperationRunMutation']['bulkOperation']
    
    # Step 4: Persist record (BEFORE polling)
    record = BulkOperationRecord(
        run_id=run_id,
        batch_id=batch_id,
        bulk_operation_id=bulk_op['id'],
        status=bulk_op['status'],
        jsonl_file_path=str(jsonl_file),
        mutation_hash=mutation_hash,
        created_at=datetime.utcnow(),
        started_at=datetime.utcnow(),
        result_url=bulk_op.get('url'),
        webhook_received=False,
        row_count=count_jsonl_lines(jsonl_file)
    )
    
    await db.save_bulk_operation(record)
    
    logger.info(f"✓ Bulk operation started: {bulk_op['id']}")
    return record
```

### 5.6 Status Monitoring (Hybrid Webhook + Poller)

**Strategy:** Primary = Webhook, Fallback = Safety Poller

**Webhook Handler (Addition #5: Security & Authenticity):**
```python
import base64
import hashlib
import hmac

def verify_shopify_hmac(raw_body: bytes, received_hmac_b64: str, secret: str) -> bool:
    """Verify Shopify webhook HMAC signature (base64-encoded SHA256)"""
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    calculated_b64 = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(calculated_b64, received_hmac_b64)

async def handle_bulk_operations_webhook(request: Request):
    """
    Handle bulk_operations/finish webhook from Shopify
    
    Security:
    - Verify HMAC signature (base64-encoded)
    - Enforce timestamp tolerance (10 minutes)
    - Dedupe by bulk_operation_id
    """
    # Step 1: Verify HMAC (CRITICAL: Shopify uses base64, not hex)
    hmac_header = request.headers.get('X-Shopify-Hmac-SHA256')
    body = await request.body()
    
    if not verify_shopify_hmac(body, hmac_header, SHOPIFY_WEBHOOK_SECRET):
        logger.warning("Invalid HMAC signature - rejecting webhook")
        return {"status": "rejected", "reason": "invalid_signature"}
    
    # Step 2: Parse payload
    payload = json.loads(body)
    bulk_operation_id = payload['admin_graphql_api_id']
    status = payload['status'].lower()  # CRITICAL: Normalize to lowercase
    
    # Step 3: Dedupe (prevent duplicate processing)
    record = await db.get_bulk_operation_by_id(bulk_operation_id)
    if record.webhook_received:
        logger.info(f"Duplicate webhook ignored: {bulk_operation_id}")
        return {"status": "duplicate"}
    
    # Step 4: Mark webhook received
    await db.update_bulk_operation(bulk_operation_id, webhook_received=True)
    
    # Step 5: Trigger result processing
    if status == "completed":  # Lowercase comparison
        await process_bulk_operation_results(bulk_operation_id)
    elif status == "failed":  # Lowercase comparison
        await handle_bulk_operation_failure(bulk_operation_id)
    
    return {"status": "processed"}
```

**Safety Poller (Addition #4: Zombie Job Detection):**
```python
async def safety_poller_loop():
    """
    Poll active bulk operations every 10 minutes
    
    Catches "zombie jobs" where webhook was dropped
    Alerts on jobs stuck in RUNNING > 4 hours
    
    CRITICAL: Use bulkOperation(id:) for API 2026-01+ (currentBulkOperation deprecated)
    
    API VERSION NOTES (2025-10 VERIFIED):
    - `currentBulkOperation` is DEPRECATED - do not use
    - `bulkOperations(...)` does NOT exist in API 2025-10
      - Evidence: "Field 'bulkOperations' doesn't exist on type 'QueryRoot'" (dev-store test)
      - This field may be introduced in future versions; do not depend on it for runtime
    
    REQUIRED APPROACH (ID-tracking + node polling):
    1. When starting job (bulkOperationRunQuery/bulkOperationRunMutation), persist returned bulkOperation.id
    2. To check status: query node(id: "<bulkOperation.id>") and cast to BulkOperation
    3. Prefer completion webhook; poller is fallback only
    
    COMPATIBILITY GATE: bulkOperations(...) is OPTIONAL and may be introduced only after
    a pinned-version schema check confirms it exists in the target API version.
    """
    while True:
        await asyncio.sleep(600)  # 10 minutes
        
        active_ops = await db.get_bulk_operations(status="RUNNING")
        
        for op in active_ops:
            # Check if webhook already processed it
            if op.webhook_received and op.status == "COMPLETED":
                continue
            
            # Query Shopify for current status via node(id:) - works on all API versions
            current_status = await shopify_graphql.query("""
                query($id: ID!) {
                  node(id: $id) {
                    ... on BulkOperation {
                      id
                      status
                      errorCode
                      createdAt
                      completedAt
                      url
                      partialDataUrl
                    }
                  }
                }
            """, variables={"id": op.bulk_operation_id})
            
            shopify_op = current_status['data']['node']
            if not shopify_op:
                logger.error(f"Bulk operation not found: {op.bulk_operation_id}")
                continue
            
            op_status = shopify_op['status'].lower()  # Normalize to lowercase
            
            # Check for stuck jobs (>4 hours)
            runtime_hours = (datetime.utcnow() - op.started_at).total_seconds() / 3600
            if runtime_hours > 4 and op_status == "running":
                logger.error(f"Bulk operation stuck >4 hours: {op.bulk_operation_id}")
                await send_alert({
                    "type": "STUCK_BULK_OPERATION",
                    "bulk_operation_id": op.bulk_operation_id,
                    "runtime_hours": runtime_hours
                })
            
            # Check for hard timeout (>23 hours)
            if runtime_hours > 23:
                logger.critical(f"Bulk operation >23 hours - HARD STOP: {op.bulk_operation_id}")
                await send_alert({
                    "type": "HARD_TIMEOUT",
                    "bulk_operation_id": op.bulk_operation_id,
                    "action_required": "Human intervention required"
                })
            
            # Process if COMPLETED but webhook missed
            if op_status == "completed" and not op.webhook_received:
                logger.warning(f"Webhook missed - processing via poller: {op.bulk_operation_id}")
                await process_bulk_operation_results(op.bulk_operation_id)
```

### 5.7 Result Processing (Per-Row Success Parsing)

**CRITICAL: COMPLETED ≠ Success (Addition #2)**

```python
async def process_bulk_operation_results(bulk_operation_id: str):
    """
    Download and parse result JSONL file
    
    CRITICAL: status=COMPLETED only means script finished.
    Must parse per-row to detect userErrors.
    
    JSONL Format: {"data":{"productUpdate":{"product":{...},"userErrors":[]}},"__lineNumber":0}
    
    Addition #4: Robust output file retrieval
    Addition #6: Stronger DONE definition
    Addition #7: Handle partialDataUrl for failed operations
    """
    # Step 1: Get operation record
    op = await db.get_bulk_operation_by_id(bulk_operation_id)
    
    # Step 2: Fetch operation details by ID (not currentBulkOperation)
    query_result = await shopify_graphql.query(f"""
        query {{
          bulkOperation(id: "{bulk_operation_id}") {{
            id
            status
            url
            partialDataUrl
          }}
        }}
    """)
    
    bulk_op_data = query_result['data']['bulkOperation']
    
    # Step 3: Get result URL (prefer url, fallback to partialDataUrl for failed ops)
    result_url = bulk_op_data.get('url') or bulk_op_data.get('partialDataUrl')
    
    if not result_url:
        logger.error(f"No result URL for operation: {bulk_operation_id}")
        return
    
    # CRITICAL: URL expires after 1 week - download immediately
    logger.info(f"Downloading result from: {result_url} (expires in 1 week)")
    
    # Step 4: Download result JSONL with retry
    result_file = await download_with_retry(result_url, max_attempts=5)
    
    # Step 5: Persist result file (don't rely on URL later)
    persisted_path = await persist_result_file(result_file, bulk_operation_id)
    await db.update_bulk_operation(bulk_operation_id, result_file_path=persisted_path)
    
    # Step 6: Stream-parse JSONL (don't load into memory - Addition #4)
    success_count = 0
    error_count = 0
    
    async with aiofiles.open(result_file, 'r') as f:
        async for line in f:
            result = json.loads(line)
            
            # Extract line number for error mapping
            line_number = result.get('__lineNumber', -1)
            
            # Extract mutation name (first key in data)
            data = result.get('data', {})
            if not data:
                logger.warning(f"Empty data in line {line_number}")
                continue
            
            # Get first mutation key (e.g., "productUpdate", "productCreate")
            mutation_name = next(iter(data.keys()))
            mutation_result = data[mutation_name]
            
            # Extract product ID and userErrors
            product_data = mutation_result.get('product', {})
            product_id = product_data.get('id')
            user_errors = mutation_result.get('userErrors', [])
            
            if user_errors:
                # Row FAILED - extract error and queue for REST retry
                error_count += 1
                error_message = user_errors[0]['message']
                error_field = user_errors[0].get('field', 'unknown')
                
                await db.update_item_status(
                    op.run_id,
                    product_id,
                    status="FAILED",
                    error_code=f"BULK_OP_USER_ERROR",
                    error_message=f"Line {line_number}: {error_field} - {error_message}"
                )
                
                # Queue for REST retry
                await queue_rest_retry(op.run_id, product_id)
                
                logger.warning(f"Product {product_id} (line {line_number}) failed: {error_message}")
            
            else:
                # Row SUCCEEDED - stronger validation (Addition #6)
                # Verify ID matches
                if not product_id:
                    logger.error(f"No product ID returned in line {line_number}")
                    error_count += 1
                    continue
                
                # Verify expected fields were updated
                expected_fields = ['title', 'descriptionHtml']
                missing_fields = [f for f in expected_fields if f not in product_data]
                
                if missing_fields:
                    logger.warning(f"Product {product_id}: expected fields missing: {missing_fields}")
                
                success_count += 1
                
                # Mark as DONE in DB
                await db.update_item_status(
                    op.run_id,
                    product_id,
                    status="DONE",
                    notes=f"Line {line_number}: Successfully updated"
                )
                
                # Increment version (post-confirmation)
                await db.increment_product_version(product_id)
    
    # Step 7: Update operation record
    await db.update_bulk_operation(
        bulk_operation_id,
        status="COMPLETED",
        completed_at=datetime.utcnow(),
        success_count=success_count,
        error_count=error_count
    )
    
    logger.info(f"Bulk operation {bulk_operation_id} processed: {success_count} success, {error_count} errors")
```

**Download with Retry (Addition #4: Robust Retrieval):**
```python
async def download_with_retry(url: str, max_attempts: int = 5) -> Path:
    """
    Download result JSONL with exponential backoff
    
    Handles temporary GCS unavailability
    """
    for attempt in range(max_attempts):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Stream to disk (don't load into memory)
                        output_path = Path(f"/tmp/bulk_result_{uuid.uuid4()}.jsonl")
                        
                        async with aiofiles.open(output_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        logger.info(f"✓ Downloaded result file: {output_path}")
                        return output_path
                    
                    else:
                        logger.warning(f"Download attempt {attempt+1} failed: HTTP {response.status}")
        
        except Exception as e:
            logger.warning(f"Download attempt {attempt+1} failed: {e}")
        
        # Exponential backoff
        if attempt < max_attempts - 1:
            delay = 2 ** attempt
            await asyncio.sleep(delay)
    
    raise Exception(f"Failed to download result after {max_attempts} attempts")


async def persist_result_file(temp_file: Path, bulk_operation_id: str) -> Path:
    """
    Persist result file permanently (URLs expire after 1 week)
    
    CRITICAL: Don't rely on Shopify's result URL for long-term storage
    """
    # Create permanent storage directory
    storage_dir = Path("data/bulk_operation_results")
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate persistent filename
    op_id_short = bulk_operation_id.split('/')[-1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    persistent_path = storage_dir / f"{op_id_short}_{timestamp}.jsonl"
    
    # Copy to permanent location
    shutil.copy(temp_file, persistent_path)
    
    logger.info(f"✓ Persisted result file: {persistent_path}")
    return persistent_path
```

### 5.8 REST API Fallback (Small Retry Set)

**Usage:** Only for products that failed in bulk operation

```python
async def process_rest_retry_queue(run_id: str):
    """
    Retry failed products using REST API (not GraphQL)
    
    Triggered after bulk operation completes with errors
    """
    retry_items = await db.get_items_for_rest_retry(run_id)
    
    logger.info(f"Processing {len(retry_items)} REST retries for run {run_id}")
    
    for item in retry_items:
        try:
            # Fetch canonical product
            product = await db.get_canonical_product(item.product_id)
            
            # Use REST API (simpler, per-product limit)
            numeric_id = product.shopify_id.split('/')[-1]
            
            # Build REST payload
            rest_payload = {
                "product": {
                    "id": int(numeric_id),
                    "title": product.title,
                    "body_html": product.description_html,
                    "tags": ", ".join(product.tags)
                }
            }
            
            # Execute REST update
            response = await shopify_rest_api.put(
                f"/admin/api/2025-10/products/{numeric_id}.json",
                json=rest_payload
            )
            
            if response.status == 200:
                logger.info(f"✓ REST retry succeeded: {product.product_id}")
                await db.update_item_status(run_id, product.product_id, status="DONE")
                await db.increment_product_version(product.product_id)
            else:
                logger.error(f"✗ REST retry failed: {product.product_id} - {response.status}")
                await db.update_item_status(
                    run_id,
                    product.product_id,
                    status="FAILED",
                    error_code=f"REST_ERROR_{response.status}"
                )
        
        except Exception as e:
            logger.error(f"REST retry exception: {product.product_id} - {e}")
            await db.update_item_status(
                run_id,
                product.product_id,
                status="FAILED",
                error_code="REST_EXCEPTION",
                error_message=str(e)
            )
```

### 5.9 Rate Limit Monitoring (GraphQL Throttle Status)

**For GraphQL Bulk Operations:**
```python
async def check_graphql_throttle() -> bool:
    """
    Check if GraphQL throttle allows new operations
    
    Uses throttleStatus field (not REST headers)
    """
    throttle_query = await shopify_graphql.query("""
        query {
          shop {
            name
          }
        }
    """, include_extensions=True)
    
    throttle_status = throttle_query['extensions']['cost']['throttleStatus']
    
    current_available = throttle_status['currentlyAvailable']
    restore_rate = throttle_status['restoreRate']
    
    if current_available < 100:  # Conservative threshold
        # Calculate wait time
        wait_seconds = (100 - current_available) / restore_rate
        logger.info(f"Throttle low - waiting {wait_seconds:.1f}s")
        await asyncio.sleep(wait_seconds)
    
    return True
```

**For REST Fallback:**
```python
def check_rest_rate_limit(response_headers: Dict) -> Optional[float]:
    """
    Check REST API rate limit from headers
    
    Returns wait time in seconds if approaching limit
    """
    api_call_limit = response_headers.get('X-Shopify-Shop-Api-Call-Limit')
    
    if api_call_limit:
        current, maximum = map(int, api_call_limit.split('/'))
        
        if current >= maximum * 0.8:  # 80% threshold
            # Wait for bucket to restore
            return 2.0  # Conservative 2 second delay
    
    return None
```

### 5.10 Sequential Execution (Concurrency Lock)

**CRITICAL: Only 1 bulk operation at a time (VERIFIED API 2025-10)**

Platform constraint evidence (dev-store test):
- Second bulkOperationRunQuery returns: "A bulk query operation for this app and shop is already in progress: <id>"
- Enforce: 1 active bulk QUERY per app+shop, 1 active bulk MUTATION per app+shop

**Lock Strategy:**
- Lock key: `shopify:bulk_query_lock:{shop_domain}` (for queries)
- Lock key: `shopify:bulk_mutation_lock:{shop_domain}` (for mutations)
- Acquire TTL: 30 minutes (extend on activity)
- Release conditions: webhook completion OR poller sees terminal status OR timeout handler triggers cancel + release

**Future note:** When upgrading to 2026-01+, re-test platform concurrency; keep sequential policy unless explicitly documented as changed.

```python
import aioredis

class BulkOperationLock:
    """Redis-based distributed lock for bulk operations"""
    
    def __init__(self, shop_domain: str, operation_type: str = "query"):
        self.redis = aioredis.from_url("redis://localhost")
        self.lock_key = f"shopify:bulk_{operation_type}_lock:{shop_domain}"
        self.lock_ttl = 1800  # 30 minutes (extend on activity)
    
    async def acquire(self, run_id: str) -> bool:
        """
        Acquire exclusive lock for bulk operation
        
        Returns True if acquired, False if another operation active
        """
        acquired = await self.redis.set(
            self.lock_key,
            run_id,
            ex=self.lock_ttl,
            nx=True  # Only set if not exists
        )
        
        if acquired:
            logger.info(f"✓ Bulk operation lock acquired: {run_id}")
            return True
        else:
            current_holder = await self.redis.get(self.lock_key)
            logger.warning(f"✗ Bulk operation lock held by: {current_holder}")
            return False
    
    async def release(self, run_id: str):
        """Release lock after operation completes"""
        current_holder = await self.redis.get(self.lock_key)
        
        if current_holder == run_id:
            await self.redis.delete(self.lock_key)
            logger.info(f"✓ Bulk operation lock released: {run_id}")
        else:
            logger.warning(f"Cannot release lock - not holder: {run_id}")

# Usage in orchestrator
lock = BulkOperationLock()

async def execute_bulk_update(run_id: str, products: List[CanonicalProduct]):
    """Execute bulk update with exclusive lock"""
    
    if not await lock.acquire(run_id):
        raise Exception("Another bulk operation already in progress")
    
    try:
        # Generate batches
        batches = await generate_bulk_batches(products)
        
        # Process each batch sequentially
        for batch_file in batches:
            await start_bulk_operation(run_id, batch_file)
            await wait_for_completion()
            await process_results()
    
    finally:
        await lock.release(run_id)
```

### 5.11 State Transition Logging

**Log all state changes for debugging:**
```python
async def log_bulk_operation_state(
    bulk_operation_id: str,
    old_status: str,
    new_status: str,
    metadata: Dict = None
):
    """
    Log state transitions for audit trail
    
    Logs: CREATED → RUNNING → COMPLETED
    """
    await db.insert_state_log({
        "bulk_operation_id": bulk_operation_id,
        "old_status": old_status,
        "new_status": new_status,
        "timestamp": datetime.utcnow(),
        "metadata": metadata or {}
    })
    
    logger.info(
        f"Bulk operation state change: {bulk_operation_id}",
        extra={
            "old_status": old_status,
            "new_status": new_status,
            "metadata": metadata
        }
    )
```

### 5.12 Configuration Reference

```python
class BulkOperationConfig:
    # Batching
    TARGET_JSONL_MB: int = 20       # Operational target (50-80MB recommended)
    MAX_JSONL_MB: int = 100         # Shopify hard cap (do not exceed)
    
    # Bulk operation options
    GROUP_OBJECTS: bool = False     # CRITICAL: False reduces runtime/timeout risk
    
    # Polling
    WEBHOOK_ENABLED: bool = True
    SAFETY_POLLER_INTERVAL_SECONDS: int = 600  # 10 minutes
    
    # Timeouts
    STUCK_JOB_THRESHOLD_HOURS: int = 4
    HARD_TIMEOUT_HOURS: int = 23
    
    # Retries
    GCS_UPLOAD_MAX_ATTEMPTS: int = 3
    RESULT_DOWNLOAD_MAX_ATTEMPTS: int = 5
    REST_RETRY_MAX_ATTEMPTS: int = 3
    
    # Rate limiting
    GRAPHQL_THROTTLE_MIN_AVAILABLE: int = 100
    REST_RATE_LIMIT_THRESHOLD: float = 0.8
    
    # Concurrency
    ALLOW_CONCURRENT_BULK_OPS: bool = False  # Strictly sequential
    
    # Result persistence
    RESULT_FILE_RETENTION_DAYS: int = 30  # Clean up after 30 days
```

**Shopify API Constraints:**
- **MIME Type:** Must be `text/jsonl` (not `application/jsonl`)
- **File Size:** Hard cap 100MB per JSONL file
- **Mutation Limitation:** Only ONE connection field allowed in mutation selection set
- **Result URLs:** Expire after 1 week - download and persist immediately
- **Webhook Topic:** `bulk_operations/finish` (lowercase)
- **Status Values:** Lowercase (`completed`, `failed`, `running`)

---

**Summary of Critical Safeguards:**
1. ✓ Multipart upload order enforced (auth before file) - ⚠️ unverified but integration-tested
2. ✓ Per-row success parsing (data.<mutationName>.userErrors detection via __lineNumber)
3. ✓ Strict type serialization (Decimal → String)
4. ✓ Tag hydration (prevent data loss)
5. ✓ Idempotency tracking (mutation hash)
6. ✓ Webhook security (HMAC base64 verification, lowercase status normalization)
7. ✓ Safety poller (zombie job detection via bulkOperation(id:) query)
8. ✓ Hard timeouts (>23hr escalation)
9. ✓ Sequential execution (Redis lock)
10. ✓ Robust error handling (retry with backoff)
11. ✓ Result persistence (URLs expire after 1 week)
12. ✓ partialDataUrl support (failed operations with partial results)
13. ✓ Mutation constraint (one connection field only)

---

## 6. Advertising Agent Foundation

**Purpose:** Automate Meta (Facebook/Instagram) advertising for SEO-optimized products with fixed budgets, UTM tracking, and manual approval gates. V1 uses OUTCOME_TRAFFIC objective (no Meta Pixel required) with strategy-tag-based product selection.

### 6.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    APEG (Orchestrator)                           │
│  1. Detect products with strategy_tag from SEO runs             │
│  2. Generate ad creative (LLM-optimized copy)                   │
│  3. Create campaigns in PAUSED state (approval gate)            │
│  4. Human approval (via Google Sheets or CLI)                   │
│  5. Activate campaigns (set status=ACTIVE)                      │
│  6. Store campaign_id/ad_id for metrics correlation             │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Meta Marketing API
┌─────────────────────────────────────────────────────────────────┐
│                   Meta Advertising Platform                      │
│  Campaign (OUTCOME_TRAFFIC, daily budget)                       │
│    └─> AdSet (targeting, placements, schedule)                 │
│         └─> Ad (carousel creative, UTM-tracked URL)             │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Click tracking
┌─────────────────────────────────────────────────────────────────┐
│              Shopify Store (UTM-tagged URLs)                     │
│  utm_campaign={strategy_tag}_{date}                             │
│  utm_content={ad_id}                                             │
│  utm_term={product_handle}                                       │
└─────────────────────────────────────────────────────────────────┘
```

**V1 Scope:**
- ✓ OUTCOME_TRAFFIC campaigns (no pixel required)
- ✓ Interest-based targeting (jewelry, birthstones, gifts)
- ✓ Carousel ads (showcase multiple products)
- ✓ Daily budget per campaign ($10/day default)
- ✓ LLM-generated ad copy (platform-optimized)
- ✓ Manual approval (create PAUSED, human activates)
- ✓ UTM tracking (metrics correlation)
- ✓ Strategy-tag product selection (high-value, seasonal, etc.)
- ✗ Catalog sync (deferred to V2)
- ✗ Conversion tracking (deferred to V2)
- ✗ Auto-pause logic (manual control only)

### 6.2 Meta Business SDK Integration (Async Mitigation)

**Challenge:** Meta's `facebook-business-sdk` is synchronous and will block async event loop.

**Solution:** Run SDK calls in thread executor (same pattern as EcomAgent integration).

**Setup:**
```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
import asyncio

class MetaAdsClient:
    """Async wrapper for Meta Marketing API"""
    
    def __init__(self, app_id: str, app_secret: str, access_token: str, ad_account_id: str):
        # Initialize SDK (synchronous)
        FacebookAdsApi.init(
            app_id=app_id,
            app_secret=app_secret,
            access_token=access_token
        )
        
        self.ad_account = AdAccount(f'act_{ad_account_id}')
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    async def create_campaign_async(self, params: dict) -> dict:
        """
        Create Meta campaign in thread executor
        
        Prevents blocking async event loop
        """
        return await asyncio.to_thread(self._create_campaign_sync, params)
    
    def _create_campaign_sync(self, params: dict) -> dict:
        """Synchronous campaign creation (runs in thread)"""
        campaign = Campaign(parent_id=self.ad_account.get_id_assured())
        
        # CRITICAL: special_ad_categories required (use empty array if none)
        campaign_params = {
            'name': params['name'],
            'objective': 'OUTCOME_TRAFFIC',  # V1: Traffic objective
            'status': 'PAUSED',  # V1: Create paused (approval gate)
            'special_ad_categories': [],  # Required even when empty
            'daily_budget': params['daily_budget']  # In cents (e.g., 1000 = $10)
        }
        
        campaign.remote_create(params=campaign_params)
        
        return {
            'campaign_id': campaign.get_id(),
            'name': campaign['name'],
            'status': campaign['status']
        }
```

**Alternative: Direct HTTP (Fully Async):**

If SDK overhead is problematic, use direct HTTP with `aiohttp`:

```python
import aiohttp

async def create_campaign_http(params: dict) -> dict:
    """
    Direct HTTP alternative (no SDK blocking)
    
    Use if SDK performance is problematic
    """
    url = f"https://graph.facebook.com/v21.0/act_{AD_ACCOUNT_ID}/campaigns"
    
    payload = {
        'name': params['name'],
        'objective': 'OUTCOME_TRAFFIC',
        'status': 'PAUSED',
        'special_ad_categories': [],
        'daily_budget': params['daily_budget'],
        'access_token': ACCESS_TOKEN
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"Campaign creation failed: {error}")
            
            return await response.json()
```

### 6.3 Campaign Structure & Hierarchy

**Meta Advertising Hierarchy:**
```
Campaign (Budget, Objective, Schedule)
  └─> AdSet (Targeting, Placements, Bid Strategy)
       └─> Ad (Creative, Destination URL)
```

**Naming Convention (Strategy-Tag Based):**
```python
def generate_campaign_name(strategy_tag: str, date: str = None) -> str:
    """
    Generate campaign name for tracking
    
    Format: {strategy_tag}_{yyyymmdd}
    Example: "high-value-birthstone_20241229"
    """
    date_str = date or datetime.now().strftime("%Y%m%d")
    return f"{strategy_tag}_{date_str}"
```

**Campaign Creation:**
```python
async def create_traffic_campaign(
    strategy_tag: str,
    daily_budget_usd: float = 10.0
) -> dict:
    """
    Create OUTCOME_TRAFFIC campaign for product strategy
    
    Args:
        strategy_tag: Strategy identifier (e.g., "high-value-birthstone")
        daily_budget_usd: Daily budget in USD (default $10)
    
    Returns:
        Campaign metadata with IDs
    """
    campaign_name = generate_campaign_name(strategy_tag)
    
    campaign_params = {
        'name': campaign_name,
        'daily_budget': int(daily_budget_usd * 100)  # Convert to cents
    }
    
    campaign = await meta_client.create_campaign_async(campaign_params)
    
    logger.info(f"✓ Created campaign: {campaign['campaign_id']} ({campaign_name})")
    
    # Store in database for metrics correlation
    await db.save_campaign({
        'campaign_id': campaign['campaign_id'],
        'strategy_tag': strategy_tag,
        'name': campaign_name,
        'objective': 'OUTCOME_TRAFFIC',
        'daily_budget_usd': daily_budget_usd,
        'status': 'PAUSED',  # V1: Requires approval
        'created_at': datetime.utcnow()
    })
    
    return campaign
```

**AdSet Creation (Targeting & Placements):**
```python
async def create_adset_async(campaign_id: str, targeting_params: dict) -> dict:
    """
    Create AdSet with interest-based targeting
    
    V1: Broad jewelry/gift targeting
    
    CRITICAL: Budget is set at CAMPAIGN level only (not adset)
    """
    adset_params = {
        'name': f"AdSet_{campaign_id}",
        'campaign_id': campaign_id,
        'optimization_goal': 'LINK_CLICKS',  # For OUTCOME_TRAFFIC
        'billing_event': 'LINK_CLICKS',
        'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',  # Meta's automated bidding
        'targeting': {
            'geo_locations': {'countries': ['US']},  # V1: US only
            'interests': targeting_params.get('interests', []),  # Populated from config
            'age_min': 25,
            'age_max': 65,
            'genders': [0]  # All genders
        },
        'status': 'PAUSED'  # Inherit from campaign
        # NOTE: daily_budget removed - set at campaign level only
    }
    
    # CRITICAL: AdSets created under ad account, not campaign
    # Pass campaign_id in params, not as parent_id
    adset = AdSet(parent_id=f'act_{AD_ACCOUNT_ID}')
    
    return await asyncio.to_thread(
        lambda: adset.remote_create(params=adset_params)
    )
```

### 6.4 Targeting Configuration (Interest ID Lookup)

**CRITICAL: Interest IDs Are Platform-Specific**

Hard-coded interest IDs must be validated via Meta's Targeting Search API before use.

**Interest Lookup & Validation:**
```python
async def lookup_interest_ids(keywords: List[str]) -> List[dict]:
    """
    Look up Meta interest IDs via Targeting Search API
    
    CRITICAL: Do not hard-code interest IDs - they may change or be invalid
    
    Args:
        keywords: Interest keywords to search (e.g., ["jewelry", "birthstone"])
    
    Returns:
        List of validated interest objects with IDs
    """
    url = f"https://graph.facebook.com/v21.0/search"
    
    validated_interests = []
    
    for keyword in keywords:
        params = {
            'type': 'adinterest',
            'q': keyword,
            'limit': 5,
            'access_token': META_ACCESS_TOKEN
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    results = await response.json()
                    
                    for interest in results.get('data', []):
                        validated_interests.append({
                            'id': interest['id'],
                            'name': interest['name'],
                            'audience_size': interest.get('audience_size', 0)
                        })
                        
                        logger.info(f"Found interest: {interest['name']} (ID: {interest['id']})")
                else:
                    logger.error(f"Interest lookup failed for '{keyword}': {response.status}")
    
    return validated_interests


async def load_targeting_config() -> dict:
    """
    Load validated targeting configuration
    
    V1: Manual lookup and persistence
    V2: Periodic refresh of interest IDs
    """
    config_file = Path("config/meta_targeting.json")
    
    if not config_file.exists():
        logger.warning("Targeting config not found - running initial setup")
        
        # Look up interests
        interests = await lookup_interest_ids([
            "jewelry",
            "birthstone",
            "gift shopping",
            "handmade jewelry"
        ])
        
        # Persist to config
        config = {'interests': interests, 'last_updated': datetime.utcnow().isoformat()}
        
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"✓ Created targeting config with {len(interests)} interests")
    
    # Load persisted config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    return config
```

**Configuration File Format (`config/meta_targeting.json`):**
```json
{
  "interests": [
    {
      "id": "6003139266461",
      "name": "Jewelry",
      "audience_size": 250000000
    },
    {
      "id": "6003244754172",
      "name": "Birthstone",
      "audience_size": 15000000
    }
  ],
  "last_updated": "2024-12-29T00:00:00"
}
```

### 6.6 Compliance Preflight (Special Ad Categories)

**CRITICAL: Meta enforces strict rules for regulated categories (credit, employment, housing).**

**Keyword Scan Before Campaign Creation:**
```python
async def check_compliance_keywords(
    campaign_name: str,
    primary_text: str,
    headline: str,
    destination_url: str
) -> dict:
    """
    Scan for regulated category keywords
    
    Categories requiring special_ad_categories declaration:
    - Credit (loans, financing, credit cards)
    - Employment (jobs, hiring, careers)
    - Housing (real estate, rentals, mortgages)
    
    Returns:
        {
            'requires_review': bool,
            'detected_categories': List[str],
            'flagged_terms': List[str]
        }
    """
    # Regulated keyword patterns
    CREDIT_KEYWORDS = ['credit', 'loan', 'financing', 'payment plan', 'buy now pay later']
    EMPLOYMENT_KEYWORDS = ['job', 'hiring', 'career', 'employment', 'work from home']
    HOUSING_KEYWORDS = ['real estate', 'rental', 'mortgage', 'apartment', 'house for sale']
    
    # Combine all text for scanning
    text_to_scan = ' '.join([
        campaign_name,
        primary_text,
        headline,
        destination_url
    ]).lower()
    
    detected_categories = []
    flagged_terms = []
    
    # Scan for credit keywords
    for keyword in CREDIT_KEYWORDS:
        if keyword in text_to_scan:
            detected_categories.append('CREDIT')
            flagged_terms.append(keyword)
    
    # Scan for employment keywords
    for keyword in EMPLOYMENT_KEYWORDS:
        if keyword in text_to_scan:
            detected_categories.append('EMPLOYMENT')
            flagged_terms.append(keyword)
    
    # Scan for housing keywords
    for keyword in HOUSING_KEYWORDS:
        if keyword in text_to_scan:
            detected_categories.append('HOUSING')
            flagged_terms.append(keyword)
    
    detected_categories = list(set(detected_categories))  # Dedupe
    
    return {
        'requires_review': len(detected_categories) > 0,
        'detected_categories': detected_categories,
        'flagged_terms': flagged_terms
    }


async def create_campaign_with_compliance_check(
    strategy_tag: str,
    products: List[CanonicalProduct],
    ad_copy: dict
) -> dict:
    """
    Create campaign with compliance preflight
    
    CRITICAL: Stop auto-create if regulated keywords detected
    """
    campaign_name = generate_campaign_name(strategy_tag)
    
    # Run compliance check
    compliance = await check_compliance_keywords(
        campaign_name=campaign_name,
        primary_text=ad_copy['primary_text'],
        headline=ad_copy['headline'],
        destination_url=products[0].shopify_url
    )
    
    if compliance['requires_review']:
        logger.warning(f"Compliance review required: {compliance['detected_categories']}")
        
        # Route to human review queue
        await db.save_campaign_for_review({
            'strategy_tag': strategy_tag,
            'campaign_name': campaign_name,
            'status': 'COMPLIANCE_REVIEW_REQUIRED',
            'detected_categories': compliance['detected_categories'],
            'flagged_terms': compliance['flagged_terms'],
            'created_at': datetime.utcnow()
        })
        
        return {
            'status': 'PENDING_COMPLIANCE_REVIEW',
            'message': f"Detected regulated categories: {', '.join(compliance['detected_categories'])}"
        }
    
    # Proceed with campaign creation
    return await create_advertising_campaign(strategy_tag, products)
```

### 6.7 Creative Generation (LLM-Optimized Ad Copy)

**Challenge:** Meta has strict character limits (primary text: 125 chars, headline: 27 chars).

**Solution:** Generate platform-specific ad copy via LLM (separate from SEO content).

```python
async def generate_ad_creative(product: CanonicalProduct) -> dict:
    """
    Generate Meta-optimized ad copy from SEO content
    
    Character limits:
    - Primary text: 125 chars (strict)
    - Headline: 27 chars (strict)
    - Description: 27 chars (optional)
    """
    prompt = f"""Generate Meta ad copy for this jewelry product.

Product Details:
- Title: {product.title}
- Description: {product.description_html[:200]}
- Price: ${product.price}
- Strategy: {product.strategy_tag}

Requirements:
- Primary text: Max 125 characters (engaging, benefit-focused)
- Headline: Max 27 characters (clear, actionable)
- Description: Max 27 characters (optional complement)

Output as JSON:
{{
  "primary_text": "...",
  "headline": "...",
  "description": "..."
}}
"""
    
    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a Meta ads copywriter. Write concise, engaging ad copy within strict character limits."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    # Parse JSON response
    ad_copy = json.loads(response.choices[0].message.content)
    
    # Enforce character limits (safety check)
    ad_copy['primary_text'] = ad_copy['primary_text'][:125]
    ad_copy['headline'] = ad_copy['headline'][:27]
    ad_copy['description'] = ad_copy['description'][:27]
    
    return ad_copy
```

### 6.8 Carousel Ad Creation:
```python
async def create_carousel_ad(
    adset_id: str,
    products: List[CanonicalProduct],
    strategy_tag: str
) -> dict:
    """
    Create carousel ad showcasing multiple products
    
    V1: Up to 10 cards per carousel
    """
    # Generate creative for each product
    carousel_cards = []
    
    for product in products[:10]:  # Max 10 cards
        ad_copy = await generate_ad_creative(product)
        
        # Build UTM-tracked destination URL
        destination_url = build_utm_url(
            base_url=f"https://{SHOPIFY_DOMAIN}/products/{product.handle}",
            strategy_tag=strategy_tag,
            product_handle=product.handle
        )
        
        carousel_cards.append({
            'name': product.title[:40],  # Card name (internal)
            'link': destination_url,
            'picture': product.images[0].url if product.images else None,
            'description': ad_copy['description'],
            'call_to_action': {
                'type': 'SHOP_NOW'
            }
        })
    
    # Create ad creative
    creative_params = {
        'name': f"Carousel_{strategy_tag}_{datetime.now().strftime('%Y%m%d')}",
        'object_story_spec': {
            'page_id': FB_PAGE_ID,
            'link_data': {
                'link': carousel_cards[0]['link'],  # Fallback URL
                'message': ad_copy['primary_text'],
                'name': ad_copy['headline'],
                'child_attachments': carousel_cards,
                'multi_share_optimized': True,
                'multi_share_end_card': False
            }
        }
    }
    
    creative = await asyncio.to_thread(
        lambda: AdCreative(parent_id=AD_ACCOUNT_ID).remote_create(params=creative_params)
    )
    
    # Create ad using creative
    ad_params = {
        'name': f"Ad_{strategy_tag}",
        'adset_id': adset_id,
        'creative': {'creative_id': creative.get_id()},
        'status': 'PAUSED'  # V1: Requires approval
    }
    
    ad = await asyncio.to_thread(
        lambda: Ad(parent_id=AD_ACCOUNT_ID).remote_create(params=ad_params)
    )
    
    return {
        'ad_id': ad.get_id(),
        'creative_id': creative.get_id(),
        'status': 'PAUSED'
    }
```

### 6.5 UTM Tracking Scheme (CRITICAL for Metrics)

**Purpose:** Link ad clicks to conversions without Meta Pixel.

**UTM Parameter Specification:**
```python
def build_utm_url(
    base_url: str,
    strategy_tag: str,
    product_handle: str,
    ad_id: str = None
) -> str:
    """
    Build UTM-tracked destination URL for Meta ads
    
    Required UTM scheme (V1):
    - utm_source: "meta"
    - utm_medium: "paid_social"
    - utm_campaign: "{strategy_tag}_{yyyymmdd}"
    - utm_content: "{ad_id}" (if available)
    - utm_term: "{product_handle}"
    
    Example:
    https://store.com/products/tanzanite-anklet?utm_source=meta&utm_medium=paid_social&utm_campaign=high-value-birthstone_20241229&utm_content=120212345678901&utm_term=tanzanite-anklet
    """
    from urllib.parse import urlencode
    
    date_str = datetime.now().strftime("%Y%m%d")
    
    utm_params = {
        'utm_source': 'meta',
        'utm_medium': 'paid_social',
        'utm_campaign': f"{strategy_tag}_{date_str}",
        'utm_term': product_handle
    }
    
    # Add ad_id if available (for ad-level tracking)
    if ad_id:
        utm_params['utm_content'] = ad_id
    
    return f"{base_url}?{urlencode(utm_params)}"
```

**UTM Validation:**
```python
def validate_utm_url(url: str) -> bool:
    """
    Validate UTM tracking parameters are present
    
    Required for metrics correlation
    """
    from urllib.parse import urlparse, parse_qs
    
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    required_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term']
    
    for param in required_params:
        if param not in params:
            logger.error(f"Missing required UTM parameter: {param}")
            return False
    
    return True
```

### 6.6 Product Selection Logic (Strategy-Tag Based)

**V1 Rule:** Only advertise products with `strategy_tag` populated.

```python
async def select_products_for_advertising(run_id: str) -> List[CanonicalProduct]:
    """
    Select products eligible for advertising
    
    V1 Criteria:
    - Must have strategy_tag (e.g., "high-value-birthstone")
    - Must have at least one image
    - Must be approved in SEO staging
    - Optional: Price threshold (>$50)
    """
    products = await db.get_seo_approved_products(run_id)
    
    eligible_products = []
    
    for product in products:
        # Check strategy_tag
        if not product.strategy_tag:
            logger.debug(f"Skipping {product.product_id}: No strategy_tag")
            continue
        
        # Check images
        if not product.images:
            logger.warning(f"Skipping {product.product_id}: No images for ads")
            continue
        
        # Optional: Price threshold
        if product.price and product.price < 50:
            logger.debug(f"Skipping {product.product_id}: Below price threshold")
            continue
        
        eligible_products.append(product)
    
    logger.info(f"Selected {len(eligible_products)}/{len(products)} products for advertising")
    
    return eligible_products
```

**Strategy Tag Assignment (During SEO):**
```python
def assign_strategy_tag(product: CanonicalProduct) -> Optional[str]:
    """
    Assign strategy tag during SEO optimization
    
    V1 Strategies:
    - high-value-birthstone: Birthstone jewelry >$75
    - seasonal-gift: Products with "gift" in tags, $40-$100
    - premium-collection: Products from "Whispers" collection
    """
    # High-value birthstone
    if any(tag.lower() in ['birthstone', 'garnet', 'amethyst', 'tanzanite'] 
           for tag in product.tags):
        if product.price and product.price > 75:
            return "high-value-birthstone"
    
    # Seasonal gift
    if 'gift' in ' '.join(product.tags).lower():
        if product.price and 40 <= product.price <= 100:
            return "seasonal-gift"
    
    # Premium collection
    if 'Whispers' in product.collections:
        return "premium-collection"
    
    return None
```

### 6.7 Campaign Approval Workflow (Manual Control V1)

**V1 Approach:** Create campaigns in PAUSED state, human reviews and activates.

```python
async def create_advertising_campaign(
    strategy_tag: str,
    products: List[CanonicalProduct],
    daily_budget_usd: float = 10.0,
    auto_activate: bool = False  # V1: False (manual approval)
) -> dict:
    """
    Create complete advertising campaign (Campaign → AdSet → Ads)
    
    V1: Creates in PAUSED state for manual approval
    """
    # Step 1: Create campaign
    campaign = await create_traffic_campaign(strategy_tag, daily_budget_usd)
    
    # Step 2: Create adset with config-based targeting
    targeting_config = await load_targeting_config()  # Validated interest IDs
    
    adset = await create_adset_async(
        campaign_id=campaign['campaign_id'],
        targeting_params={'interests': targeting_config['interests']}
    )
    
    # Step 3: Create carousel ad
    ad = await create_carousel_ad(
        adset_id=adset.get_id(),
        products=products,
        strategy_tag=strategy_tag
    )
    
    # Step 4: Store for approval tracking
    campaign_record = {
        'campaign_id': campaign['campaign_id'],
        'adset_id': adset.get_id(),
        'ad_id': ad['ad_id'],
        'strategy_tag': strategy_tag,
        'product_count': len(products),
        'daily_budget_usd': daily_budget_usd,
        'status': 'PENDING_APPROVAL',  # V1: Awaiting human review
        'created_at': datetime.utcnow()
    }
    
    await db.save_advertising_campaign(campaign_record)
    
    logger.info(f"✓ Campaign created (PAUSED): {campaign['campaign_id']}")
    
    return campaign_record


async def activate_campaign(campaign_id: str, approved_by: str):
    """
    Activate campaign after manual approval
    
    V1: Called by human via CLI or approval interface
    """
    # Update campaign status to ACTIVE
    await asyncio.to_thread(
        lambda: Campaign(campaign_id).remote_update(params={'status': 'ACTIVE'})
    )
    
    # Update database
    await db.update_campaign_status(
        campaign_id,
        status='ACTIVE',
        approved_by=approved_by,
        approved_at=datetime.utcnow()
    )
    
    logger.info(f"✓ Campaign activated: {campaign_id} by {approved_by}")
```

### 6.8 Catalog Strategy (V1 Manual, V2 Product Sets)

**V1 (Current): Manual Carousel Ads - No Catalog Required**

Manual carousel creation with strategy-tag selection from APEG database. No catalog dependency.

**V2 (Future): Strategy-Tag Product Sets - Catalog Required**

**CRITICAL: Feed Field Must Be Populated Before Product Set Filtering**

Product Sets filter on fields like `internal_label` or `custom_label_0`. These fields must be populated by your feed mapping BEFORE creating product sets.

**Prerequisites (Must Validate Before V2):**
1. Product catalog synced to Meta Commerce Manager
2. Feed field mapping verified (`internal_label` preferred, `custom_label_0` fallback)
3. Test product shows `strategy_tag` value in catalog

**Verification Steps:**
```
1. Open Commerce Manager → Catalog → Products
2. Find one test product
3. Check if "internal_label" or "custom_label_0" contains strategy_tag value
4. If empty:
   - Option A: Update Shopify→Meta feed rules to map strategy_tag
   - Option B: Create APEG-exported supplemental feed (CSV/XML)
   - Option C: Use different carrier field (verify mapping first)
```

**V2 Product Set Creation (After Feed Validation):**
```python
async def create_product_set_for_strategy(strategy_tag: str, catalog_id: str) -> dict:
    """
    V2: Create Meta Product Set filtered by strategy_tag
    
    PREREQUISITE: Feed field mapping verified and populated
    
    Uses internal_label field (or custom_label_0 as fallback)
    """
    product_set_params = {
        'name': f"ProductSet_{strategy_tag}",
        'filter': {
            'internal_label': {'contains': [strategy_tag]}  # Requires feed mapping
        }
    }
    
    url = f"https://graph.facebook.com/v21.0/{catalog_id}/product_sets"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={
            **product_set_params,
            'access_token': META_ACCESS_TOKEN
        }) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"Product set creation failed: {error}")
            
            result = await response.json()
            return {'product_set_id': result['id'], 'strategy_tag': strategy_tag}
```

**V1 vs V2 Decision Matrix:**

| Feature | V1 (Manual) | V2 (Product Sets) |
|---------|-------------|-------------------|
| Objective | OUTCOME_TRAFFIC | OUTCOME_SALES |
| Catalog Required | No | Yes (verified) |
| Feed Mapping | Not needed | Required + tested |
| Product Selection | APEG database | Meta Product Sets |
| Tracking | UTM only | Pixel + CAPI |
| Scaling | Async Request Sets | Dynamic ads |

**Recommendation:** Stay in V1 until feed field mapping verified.

### 6.9 Async Request Sets (Bulk Creation)

**Purpose:** Create multiple campaigns/adsets/ads in parallel with proper error handling.

**CRITICAL: Async Request Sets Are Not Transactions**

RequestSet status=COMPLETED does NOT mean all items succeeded. Must parse per-item results.

**Batch Creation with Error Handling:**
```python
async def create_campaigns_batch(
    campaign_specs: List[dict]
) -> dict:
    """
    Create multiple campaigns using Async Request Sets
    
    CRITICAL: Parse per-item results - status=COMPLETED ≠ all succeeded
    
    Returns:
        {
            'successful': List[dict],  # Created campaign IDs
            'failed': List[dict],      # Errors with original specs
            'request_set_id': str
        }
    """
    # Build batch request
    batch_requests = []
    
    for idx, spec in enumerate(campaign_specs):
        batch_requests.append({
            'method': 'POST',
            'relative_url': f'act_{AD_ACCOUNT_ID}/campaigns',
            'body': urlencode({
                'name': spec['name'],
                'objective': 'OUTCOME_TRAFFIC',
                'status': 'PAUSED',
                'special_ad_categories': '[]',
                'daily_budget': spec['daily_budget']
            }),
            'name': f"campaign_{idx}"  # Reference for result mapping
        })
    
    # Submit async request set
    url = f"https://graph.facebook.com/v21.0/act_{AD_ACCOUNT_ID}/async_requests"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={
            'batch': batch_requests,
            'access_token': META_ACCESS_TOKEN
        }) as response:
            if response.status != 200:
                raise Exception(f"Async request set creation failed: {await response.text()}")
            
            result = await response.json()
            request_set_id = result['id']
    
    logger.info(f"✓ Created async request set: {request_set_id}")
    
    # Poll for completion
    result_data = await poll_async_request_set(request_set_id)
    
    # Parse per-item results (CRITICAL)
    successful = []
    failed = []
    
    for item in result_data:
        item_name = item.get('name')  # Maps to original spec
        item_code = item.get('code')
        
        if item_code == 200:
            # Success - extract created ID
            body = json.loads(item.get('body', '{}'))
            successful.append({
                'campaign_id': body.get('id'),
                'name': item_name,
                'spec_index': int(item_name.split('_')[1])
            })
            
            logger.info(f"✓ Campaign created: {body.get('id')}")
        
        else:
            # Failure - extract error
            body = json.loads(item.get('body', '{}'))
            error = body.get('error', {})
            
            failed.append({
                'name': item_name,
                'spec_index': int(item_name.split('_')[1]),
                'error_code': error.get('code'),
                'error_message': error.get('message'),
                'original_spec': campaign_specs[int(item_name.split('_')[1])]
            })
            
            logger.error(f"✗ Campaign failed: {error.get('message')}")
    
    logger.info(f"Batch complete: {len(successful)} success, {len(failed)} failed")
    
    return {
        'successful': successful,
        'failed': failed,
        'request_set_id': request_set_id
    }


async def poll_async_request_set(request_set_id: str, max_attempts: int = 60) -> List[dict]:
    """
    Poll async request set until complete
    
    Args:
        request_set_id: Request set ID from creation
        max_attempts: Max polling attempts (60 = 5 minutes at 5s intervals)
    
    Returns:
        List of per-item results
    """
    url = f"https://graph.facebook.com/v21.0/{request_set_id}"
    
    for attempt in range(max_attempts):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={'access_token': META_ACCESS_TOKEN}) as response:
                if response.status != 200:
                    raise Exception(f"Request set polling failed: {await response.text()}")
                
                data = await response.json()
                status = data.get('async_status')
                
                if status == 'complete':
                    # Fetch results
                    result_url = f"{url}/results"
                    async with session.get(result_url, params={'access_token': META_ACCESS_TOKEN}) as result_response:
                        results = await result_response.json()
                        return results.get('data', [])
                
                elif status == 'error':
                    raise Exception(f"Request set failed: {data.get('error')}")
                
                # Still processing
                await asyncio.sleep(5)
    
    raise Exception(f"Request set timeout after {max_attempts} attempts")


async def retry_failed_campaigns(failed_items: List[dict]):
    """
    Retry failed campaigns individually with backoff
    
    CRITICAL: Do not retry items that succeeded in batch
    """
    for item in failed_items:
        try:
            # Retry with exponential backoff
            await asyncio.sleep(2 ** item.get('retry_count', 0))
            
            spec = item['original_spec']
            campaign = await create_traffic_campaign(
                strategy_tag=spec['strategy_tag'],
                daily_budget_usd=spec['daily_budget_usd']
            )
            
            logger.info(f"✓ Retry successful: {campaign['campaign_id']}")
        
        except Exception as e:
            logger.error(f"✗ Retry failed: {e}")
```

### 6.10 Idempotency (Two-Layer Protection)

**Layer 1 (Required): Local Deduplication**

```python
import hashlib

def generate_campaign_key(
    run_id: str,
    strategy_tag: str,
    object_type: str = "campaign"
) -> str:
    """
    Generate deterministic idempotency key
    
    Args:
        run_id: SEO run identifier
        strategy_tag: Strategy tag for campaign
        object_type: Type of object (campaign, adset, ad)
    
    Returns:
        Idempotency key (hash)
    """
    key_input = f"{run_id}:{strategy_tag}:{object_type}"
    return hashlib.sha256(key_input.encode()).hexdigest()


async def create_campaign_idempotent(
    run_id: str,
    strategy_tag: str,
    daily_budget_usd: float
) -> dict:
    """
    Create campaign with local idempotency check
    
    Layer 1: Check database for existing campaign with same key
    """
    # Generate idempotency key
    idem_key = generate_campaign_key(run_id, strategy_tag, "campaign")
    
    # Check if already created
    existing = await db.get_campaign_by_idempotency_key(idem_key)
    
    if existing:
        logger.info(f"Campaign already exists (idempotent): {existing['campaign_id']}")
        return existing
    
    # Create campaign
    campaign = await create_traffic_campaign(strategy_tag, daily_budget_usd)
    
    # Store with idempotency key
    await db.save_campaign({
        'campaign_id': campaign['campaign_id'],
        'idempotency_key': idem_key,
        'run_id': run_id,
        'strategy_tag': strategy_tag,
        'daily_budget_usd': daily_budget_usd,
        'created_at': datetime.utcnow()
    })
    
    logger.info(f"✓ Campaign created with idempotency key: {idem_key[:8]}...")
    
    return campaign
```

**Database Schema (Idempotency Tracking):**
```sql
ALTER TABLE advertising_campaigns 
ADD COLUMN idempotency_key TEXT UNIQUE;

CREATE INDEX idx_campaigns_idem_key ON advertising_campaigns(idempotency_key);
```

**Layer 2 (Optional): Meta Native Idempotency**

⚠️ **REQUIRES VALIDATION:** Meta's native idempotency mechanism is endpoint-specific.

```python
async def create_campaign_with_native_idempotency(
    spec: dict,
    idempotency_token: str
) -> dict:
    """
    OPTIONAL: Use Meta's native idempotency if supported
    
    WARNING: This must be validated for your specific endpoint/API version
    
    Include in request headers:
    - X-FB-Idempotency-Token: {token}
    """
    headers = {
        'X-FB-Idempotency-Token': idempotency_token
    }
    
    # NOTE: Verify this header is supported before using
    # Fallback to Layer 1 if not supported
    
    # ... campaign creation with headers
```

**Idempotency Best Practices:**
1. **Always use Layer 1** (local dedupe via database)
2. **Only add Layer 2** after confirming Meta supports it for your endpoints
3. **Use deterministic keys** (hash of run_id + strategy_tag + object_type)
4. **Store Meta IDs immediately** after creation (prevent retry duplication)

### 6.11 Error Handling & Retry Logic

```python
async def create_campaign_with_retry(
    strategy_tag: str,
    products: List[CanonicalProduct],
    max_attempts: int = 3
) -> dict:
    """
    Create campaign with retry on transient errors
    """
    for attempt in range(max_attempts):
        try:
            return await create_advertising_campaign(strategy_tag, products)
        
        except Exception as e:
            error_msg = str(e)
            
            # Check for retryable errors
            if 'rate limit' in error_msg.lower():
                delay = 60 * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Rate limited - retry {attempt+1}/{max_attempts} in {delay}s")
                await asyncio.sleep(delay)
            
            elif 'special_ad_categories' in error_msg:
                logger.error("Missing special_ad_categories - adding empty array")
                # This should be caught earlier, but log for debugging
                raise
            
            elif attempt == max_attempts - 1:
                logger.error(f"Campaign creation failed after {max_attempts} attempts: {e}")
                raise
            
            else:
                logger.warning(f"Retry {attempt+1}/{max_attempts}: {e}")
                await asyncio.sleep(5)
```

### 6.12 Configuration Reference

```python
class AdvertisingConfig:
    # Meta Business Setup
    META_APP_ID: str
    META_APP_SECRET: str
    META_ACCESS_TOKEN: str
    META_AD_ACCOUNT_ID: str
    META_FB_PAGE_ID: str
    
    # Campaign defaults
    DEFAULT_OBJECTIVE: str = "OUTCOME_TRAFFIC"  # V1: No pixel required
    DEFAULT_DAILY_BUDGET_USD: float = 10.0
    CREATE_PAUSED: bool = True  # V1: Manual approval required
    
    # Targeting (loaded from config/meta_targeting.json)
    TARGET_COUNTRIES: List[str] = ["US"]
    TARGET_AGE_MIN: int = 25
    TARGET_AGE_MAX: int = 65
    # CRITICAL: Interest IDs loaded dynamically (not hard-coded)
    # Run lookup_interest_ids() to populate config/meta_targeting.json
    
    # Creative limits
    CAROUSEL_MAX_CARDS: int = 10
    PRIMARY_TEXT_MAX_CHARS: int = 125
    HEADLINE_MAX_CHARS: int = 27
    DESCRIPTION_MAX_CHARS: int = 27
    
    # Product selection
    MIN_PRICE_USD: float = 50.0
    REQUIRE_STRATEGY_TAG: bool = True
    REQUIRE_IMAGES: bool = True
    
    # UTM tracking
    UTM_SOURCE: str = "meta"
    UTM_MEDIUM: str = "paid_social"
    
    # Retry policy
    MAX_RETRY_ATTEMPTS: int = 3
    RATE_LIMIT_BACKOFF_BASE: int = 60  # Seconds
    
    # Compliance
    COMPLIANCE_KEYWORDS_ENABLED: bool = True
    
    # Async Request Sets
    BATCH_SIZE: int = 50  # Max items per request set
    POLL_INTERVAL_SECONDS: int = 5
    MAX_POLL_ATTEMPTS: int = 60  # 5 minutes max
```

**CRITICAL: Interest ID Validation**
- Do NOT hard-code interest IDs in code
- Run `lookup_interest_ids()` during setup
- Persist validated IDs to `config/meta_targeting.json`
- Refresh periodically (monthly recommended)

### 6.11 Database Schema (Campaign Tracking)

```sql
CREATE TABLE advertising_campaigns (
    campaign_id TEXT PRIMARY KEY,
    adset_id TEXT,
    ad_id TEXT,
    strategy_tag TEXT NOT NULL,
    campaign_name TEXT,
    objective TEXT DEFAULT 'OUTCOME_TRAFFIC',
    daily_budget_usd DECIMAL,
    status TEXT,  -- PENDING_APPROVAL | ACTIVE | PAUSED | ARCHIVED
    product_count INTEGER,
    created_at TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by TEXT,
    archived_at TIMESTAMP
);

CREATE TABLE campaign_products (
    campaign_id TEXT,
    product_id TEXT,
    utm_url TEXT,
    position_in_carousel INTEGER,
    PRIMARY KEY (campaign_id, product_id)
);

CREATE INDEX idx_campaigns_strategy ON advertising_campaigns(strategy_tag);
CREATE INDEX idx_campaigns_status ON advertising_campaigns(status);
```

---

**Summary of Critical Decisions & Corrections:**

**API Corrections Implemented:**
1. ✓ Budget location fixed (campaign-level only, removed from adset)
2. ✓ AdSet parent_id corrected (ad account, not campaign)
3. ✓ promoted_object removed (V1 doesn't use pixel)
4. ✓ Interest IDs validated via lookup (not hard-coded)

**New Constraints Added:**
5. ✓ Async Request Sets (per-item result parsing, not transactional)
6. ✓ Feed Field Constraint (internal_label mapping required for V2)
7. ✓ Two-layer idempotency (local dedupe + optional native)
8. ✓ Compliance preflight (special_ad_categories keyword scan)

### 6.12 Meta Ads Deployment Config & Smoke Tests

**Required Configuration (see Section 1.8 for full list):**
```python
# Minimum required for Meta Ads operations
META_GRAPH_API_VERSION = os.getenv('META_GRAPH_API_VERSION', 'v22.0')
META_ACCESS_TOKEN = os.getenv('META_ACCESS_TOKEN')  # System user preferred
META_AD_ACCOUNT_ID = os.getenv('META_AD_ACCOUNT_ID')  # act_XXXXX format
```

**Pre-Flight Smoke Tests (Must PASS before production ads):**

```python
async def meta_ads_smoke_test():
    """
    Validate Meta Ads configuration before creating campaigns
    
    All tests must PASS before proceeding to production
    """
    results = {}
    
    # Test 1: Token validity + scopes
    try:
        debug_token = await meta_api.get('/debug_token', {
            'input_token': META_ACCESS_TOKEN,
            'access_token': META_ACCESS_TOKEN
        })
        scopes = debug_token['data']['scopes']
        required_scopes = ['ads_management', 'ads_read', 'business_management']
        missing = [s for s in required_scopes if s not in scopes]
        results['token_valid'] = len(missing) == 0
        results['missing_scopes'] = missing
    except Exception as e:
        results['token_valid'] = False
        results['token_error'] = str(e)
    
    # Test 2: Ad account access
    try:
        account = await meta_api.get(f'/{META_AD_ACCOUNT_ID}', {
            'fields': 'id,name,account_status,currency'
        })
        results['account_accessible'] = True
        results['account_status'] = account.get('account_status')
    except Exception as e:
        results['account_accessible'] = False
        results['account_error'] = str(e)
    
    # Test 3: Create PAUSED test campaign (optional but recommended)
    try:
        test_campaign = await meta_api.post(f'/{META_AD_ACCOUNT_ID}/campaigns', {
            'name': 'APEG_SMOKE_TEST_DELETE_ME',
            'objective': 'OUTCOME_TRAFFIC',
            'status': 'PAUSED',
            'special_ad_categories': []
        })
        results['can_create_campaign'] = True
        results['test_campaign_id'] = test_campaign['id']
        
        # Clean up: delete test campaign
        await meta_api.delete(f'/{test_campaign["id"]}')
        results['cleanup_success'] = True
    except Exception as e:
        results['can_create_campaign'] = False
        results['campaign_error'] = str(e)
    
    # Overall pass/fail
    results['all_passed'] = (
        results.get('token_valid', False) and
        results.get('account_accessible', False)
    )
    
    return results
```

**Smoke Test Checklist:**
- [ ] Token valid and has required scopes
- [ ] Ad account accessible and active
- [ ] Can create PAUSED campaign (optional but validates permissions)
- [ ] Interest ID lookup returns results (if using interest targeting)

**Core Implementation:**
9. ✓ OUTCOME_TRAFFIC objective (no pixel, verified feasible)
10. ✓ Create campaigns PAUSED (manual approval gate)
11. ✓ Thread executor for SDK (prevent async blocking)
12. ✓ UTM tracking scheme (metrics correlation without pixel)
13. ✓ Strategy-tag product selection
14. ✓ LLM-generated ad copy (character limits enforced)
15. ✓ Carousel format (10 products max)
16. ✓ Interest-based targeting (dynamically loaded)
17. ✓ special_ad_categories required (empty array when none)
18. ✓ Manual control only (no auto-pause V1)
19. ✓ Direct HTTP alternative (if SDK performance issues)

**Catalog Strategy:**
20. ✓ V1: Manual selection (no catalog)
21. ✓ V2: Product Sets (requires feed field verification)

**Unverified (Requires Testing):**
- ⚠️ Filtered catalog sync (needs feed mapping validation)
- ⚠️ Traffic objective without pixel (test in environment)
- ⚠️ Native Meta idempotency (Layer 2 optional, validate before use)

---

## 7. Metrics Collection & Storage

**Purpose:** Collect advertising performance data from Meta Insights API and Shopify orders, store in dual format (JSONL + SQLite), and enable performance analysis for feedback loop triggers.

### 7.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              Daily Batch Job (Scheduled)                         │
│  Runs after Meta reporting close in ad account timezone         │
│  Pulls rolling 3-day window (settlement-aware)                  │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Meta Insights API
┌─────────────────────────────────────────────────────────────────┐
│                   Meta Insights Collector                        │
│  - Query campaign-level metrics (strategy_tag performance)       │
│  - Query ad-level metrics (creative/product performance)         │
│  - Sequential requests (rate limit safe)                         │
│  - Retry with backoff (up to 72h for settlement)                │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ UPSERT (3-day window)
┌─────────────────────────────────────────────────────────────────┐
│              SQLite Metrics Database                             │
│  - UPSERT by (account, level, object_id, date)                  │
│  - is_settled flag (false for last 3 days)                      │
│  - Supports time-series queries + aggregations                  │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Raw backup
┌─────────────────────────────────────────────────────────────────┐
│              JSONL Audit Trail                                   │
│  - Raw API responses (can rebuild SQLite)                       │
│  - Timestamped with collection metadata                         │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Shopify Orders API
┌─────────────────────────────────────────────────────────────────┐
│           Attribution Collector (Shopify)                        │
│  - Waterfall: customerJourney → landing_site → referrer         │
│  - Match utm_campaign to strategy_tag                           │
│  - Per-campaign conversion tracking                             │
└─────────────────────────────────────────────────────────────────┘
```

**V1 Scope:**
- ✓ Daily batch collection (after reporting close)
- ✓ Campaign + Ad-level metrics
- ✓ 3-day rolling window (settlement-aware)
- ✓ JSONL + SQLite dual storage
- ✓ Shopify attribution waterfall
- ✓ Sequential API requests (rate limit safe)
- ✓ 1-year data retention
- ✗ Real-time streaming (deferred to V2)
- ✗ Auto-triggers (manual review only V1)

### 7.2 Settlement Window & UPSERT Strategy

**CRITICAL: Meta Metrics Can Change for Up to 72 Hours**

Meta's reporting data settles over ~72 hours. Early reads may show incomplete or inaccurate data that updates later.

**Solution: Rolling 3-Day Window with UPSERT**

```python
from datetime import datetime, timedelta
import pytz

async def calculate_rolling_window(ad_account_timezone: str = 'America/New_York') -> tuple:
    """
    Calculate 3-day rolling window for metrics collection
    
    CRITICAL: Always fetch last 3 days to capture settlement updates
    
    Args:
        ad_account_timezone: Ad account timezone (from Meta settings)
    
    Returns:
        (since_date, until_date) in account timezone
    """
    # Get current time in account timezone
    tz = pytz.timezone(ad_account_timezone)
    now = datetime.now(tz)
    
    # Calculate date range
    # until_date = yesterday (today's data not yet available)
    # since_date = 3 days ago (covers settlement window)
    until_date = (now - timedelta(days=1)).date()
    since_date = (now - timedelta(days=3)).date()
    
    logger.info(f"Rolling window: {since_date} to {until_date} ({ad_account_timezone})")
    
    return (since_date, until_date)


async def collect_metrics_with_settlement_awareness():
    """
    Daily batch job with settlement window handling
    
    CRITICAL: UPSERT ensures late updates don't create duplicates
    """
    since_date, until_date = await calculate_rolling_window()
    
    # Collect campaign-level metrics
    campaigns = await db.get_active_campaigns()
    
    for campaign in campaigns:
        # Fetch metrics for rolling window
        metrics = await fetch_meta_insights(
            object_id=campaign['campaign_id'],
            level='campaign',
            since=since_date,
            until=until_date
        )
        
        # UPSERT into database (handles updates to settling data)
        for daily_metric in metrics:
            await db.upsert_metric(
                account_id=AD_ACCOUNT_ID,
                level='campaign',
                object_id=campaign['campaign_id'],
                date=daily_metric['date_stop'],
                metrics=daily_metric,
                is_settled=daily_metric['date_stop'] < (until_date - timedelta(days=2))
            )
    
    logger.info(f"✓ Metrics collection complete (rolling window: {since_date} to {until_date})")
```

**UPSERT Logic (SQLite):**
```python
async def upsert_metric(
    account_id: str,
    level: str,
    object_id: str,
    date: str,
    metrics: dict,
    is_settled: bool
):
    """
    UPSERT metric with settlement tracking
    
    Key: (account_id, level, object_id, date)
    Updates: metrics, is_settled, last_refreshed_at
    """
    query = """
        INSERT INTO metrics (
            account_id, level, object_id, date,
            impressions, clicks, spend, ctr, cpc,
            reach, frequency, outbound_clicks, outbound_clicks_ctr,
            is_settled, last_refreshed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(account_id, level, object_id, date) 
        DO UPDATE SET
            impressions = excluded.impressions,
            clicks = excluded.clicks,
            spend = excluded.spend,
            ctr = excluded.ctr,
            cpc = excluded.cpc,
            reach = excluded.reach,
            frequency = excluded.frequency,
            outbound_clicks = excluded.outbound_clicks,
            outbound_clicks_ctr = excluded.outbound_clicks_ctr,
            is_settled = excluded.is_settled,
            last_refreshed_at = excluded.last_refreshed_at
    """
    
    await db.execute(query, (
        account_id, level, object_id, date,
        metrics.get('impressions', 0),
        metrics.get('link_clicks', 0),  # Keep for diagnostics
        float(metrics.get('spend', 0)),
        float(metrics.get('ctr', 0)),
        float(metrics.get('cpc', 0)),
        metrics.get('reach', 0),
        float(metrics.get('frequency', 0)),
        metrics.get('outbound_clicks', 0),  # CRITICAL: Primary traffic metric
        float(metrics.get('outbound_clicks_ctr', 0)),
        is_settled,
        datetime.utcnow().isoformat()
    ))
```

**Settlement Policy:**
```python
def determine_settlement_status(date: str, collection_date: str) -> bool:
    """
    Determine if metrics for a date are considered settled
    
    Rule: Settled if date is >2 days before collection date
    """
    date_obj = datetime.fromisoformat(date).date()
    collection_obj = datetime.fromisoformat(collection_date).date()
    
    days_old = (collection_obj - date_obj).days
    
    return days_old > 2  # Settled after 72 hours
```

### 7.3 Meta Insights API Integration

**Metrics Collection (Campaign + Ad Levels):**

```python
async def fetch_meta_insights(
    object_id: str,
    level: str,  # 'campaign' or 'ad'
    since: str,
    until: str,
    fields: List[str] = None
) -> List[dict]:
    """
    Fetch metrics from Meta Insights API
    
    CRITICAL: Include outbound_clicks (not just link_clicks)
    CRITICAL: Monitor x-fb-ads-insights-throttle header for rate limiting
    
    Args:
        object_id: Campaign or Ad ID
        level: Aggregation level
        since/until: Date range (YYYY-MM-DD)
        fields: Metrics to fetch (uses V1_METRICS if None)
    
    Returns:
        List of daily metric dicts
    """
    if fields is None:
        fields = V1_METRICS  # Defined in config
    
    url = f"https://graph.facebook.com/v21.0/{object_id}/insights"
    
    params = {
        'level': level,
        'time_range': json.dumps({
            'since': str(since),
            'until': str(until)
        }),
        'time_increment': 1,  # Daily breakdown
        'fields': ','.join(fields),
        'access_token': META_ACCESS_TOKEN
    }
    
    # Sequential request (rate limit safe)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            # CRITICAL: Monitor throttle header (Meta best practice)
            throttle_header = response.headers.get('x-fb-ads-insights-throttle')
            if throttle_header:
                try:
                    throttle_data = json.loads(throttle_header)
                    app_throttle = throttle_data.get('app_id_util_pct', 0)
                    acc_throttle = throttle_data.get('acc_id_util_pct', 0)
                    
                    logger.info(f"Throttle status - App: {app_throttle}%, Account: {acc_throttle}%")
                    
                    # Dynamically increase delay if approaching limits
                    if app_throttle > 75 or acc_throttle > 75:
                        delay = 10 if max(app_throttle, acc_throttle) > 90 else 5
                        logger.warning(f"High throttle usage - adding {delay}s delay")
                        await asyncio.sleep(delay)
                
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse throttle header: {throttle_header}")
            
            if response.status == 200:
                data = await response.json()
                return data.get('data', [])
            
            elif response.status == 429:
                # Rate limited - retry with backoff
                logger.warning(f"Rate limited on {object_id} - retrying")
                await asyncio.sleep(60)
                return await fetch_meta_insights(object_id, level, since, until, fields)
            
            else:
                error = await response.text()
                logger.error(f"Insights API error: {error}")
                return []


# V1 Metrics Set (Minimum Safe)
V1_METRICS = [
    'impressions',
    'spend',
    'reach',
    'frequency',
    'link_clicks',  # Diagnostic (includes on-platform clicks)
    'ctr',
    'cpc',
    'outbound_clicks',  # CRITICAL: Primary traffic metric
    'outbound_clicks_ctr'  # CRITICAL: Better signal than ctr
]
```

**Batch Collection Loop (Sequential + Conservative):**
```python
async def collect_all_campaign_metrics(since: str, until: str):
    """
    Collect metrics for all active campaigns
    
    Sequential with delays (rate limit safe)
    """
    campaigns = await db.get_active_campaigns()
    
    logger.info(f"Collecting metrics for {len(campaigns)} campaigns")
    
    for idx, campaign in enumerate(campaigns):
        try:
            # Fetch campaign-level metrics
            campaign_metrics = await fetch_meta_insights(
                object_id=campaign['campaign_id'],
                level='campaign',
                since=since,
                until=until
            )
            
            # Store to SQLite
            for daily in campaign_metrics:
                await db.upsert_metric(
                    account_id=AD_ACCOUNT_ID,
                    level='campaign',
                    object_id=campaign['campaign_id'],
                    date=daily['date_stop'],
                    metrics=daily,
                    is_settled=determine_settlement_status(daily['date_stop'], str(until))
                )
            
            # Store raw to JSONL
            await save_raw_insights_jsonl(campaign['campaign_id'], campaign_metrics)
            
            # Fetch ad-level metrics (for creative performance)
            ad_metrics = await fetch_meta_insights(
                object_id=campaign['campaign_id'],
                level='ad',
                since=since,
                until=until
            )
            
            for daily in ad_metrics:
                await db.upsert_metric(
                    account_id=AD_ACCOUNT_ID,
                    level='ad',
                    object_id=daily['ad_id'],
                    date=daily['date_stop'],
                    metrics=daily,
                    is_settled=determine_settlement_status(daily['date_stop'], str(until))
                )
            
            logger.info(f"✓ [{idx+1}/{len(campaigns)}] Collected metrics: {campaign['campaign_id']}")
            
            # Conservative delay between campaigns (rate limit safety)
            await asyncio.sleep(2)
        
        except Exception as e:
            logger.error(f"Failed to collect metrics for {campaign['campaign_id']}: {e}")
            continue
```

### 7.4 Attribution Waterfall (Shopify Orders)

**CRITICAL: Order.customerJourney May Be Null**

Privacy/consent restrictions can cause `customerJourney` to be null. Must have fallback attribution sources.

**CustomerJourney Attribution Window:**

CustomerJourney uses a 30-day attribution window (semantics), not a general data-retention guarantee.
Treat as non-build-gating unless attribution correctness is required for decisions.

**UTM Mapping Contract (V1 No-Pixel Attribution):**

For deterministic attribution without Meta Pixel, enforce strict UTM parameter scheme:

```python
# REQUIRED UTM SCHEME (must match Section 6 ad creation)
UTM_CONTRACT = {
    'utm_source': 'meta',                    # Fixed: Identifies Meta traffic
    'utm_medium': 'paid_social',             # Fixed: Channel identifier
    'utm_campaign': '{strategy_tag}_{yyyymmdd}',  # Variable: Campaign identifier
    'utm_content': '{ad_id}',                # Preferred: Ad-level tracking
    'utm_term': '{product_handle}'           # Optional: Product-level tracking
}

# Alternative utm_content if ad_id not available at click time:
# utm_content = '{product_handle}' or '{variant_id}'
```

**Example UTM URLs:**
```
# Preferred (with ad_id):
https://store.com/products/tanzanite-anklet?utm_source=meta&utm_medium=paid_social&utm_campaign=high-value-birthstone_20241229&utm_content=120212345678901&utm_term=tanzanite-anklet

# Fallback (product_handle as content):
https://store.com/products/tanzanite-anklet?utm_source=meta&utm_medium=paid_social&utm_campaign=high-value-birthstone_20241229&utm_content=tanzanite-anklet&utm_term=tanzanite-anklet
```

**Why This Matters:**
- `utm_source=meta` enables Shopify Analytics filtering
- `utm_campaign={strategy_tag}_{date}` enables campaign matching
- `utm_content={ad_id}` enables ad-level performance analysis
- `utm_term={product_handle}` enables product-level ROAS

**Validation Function:**
```python
def validate_utm_contract(utm_params: dict) -> bool:
    """
    Validate UTM parameters match contract
    
    CRITICAL: Enforces deterministic attribution
    """
    required = {
        'utm_source': 'meta',
        'utm_medium': 'paid_social',
        'utm_campaign': lambda v: v and '_' in v,  # Must contain strategy_tag_date
    }
    
    for param, expected in required.items():
        value = utm_params.get(param)
        
        if callable(expected):
            if not expected(value):
                logger.error(f"UTM contract violation: {param} = {value}")
                return False
        elif value != expected:
            logger.error(f"UTM contract violation: {param} = {value}, expected {expected}")
            return False
    
    return True
```

**Waterfall Strategy:**
```python
from enum import Enum
from urllib.parse import urlparse, parse_qs

class AttributionQuality(Enum):
    CJ = "customerJourney"          # Tier 1: Best quality
    LANDING_SITE = "landing_site"   # Tier 2: URL-based
    REFERRER = "referrer"           # Tier 3: Referrer-based
    NONE = "none"                   # No attribution data


async def extract_utm_parameters(order: dict) -> dict:
    """
    Extract UTM parameters using attribution waterfall
    
    CRITICAL: customerJourney can be null due to privacy/consent
    
    Tier 1: order.customerJourney.lastVisit.utmParameters (best)
    Tier 2: Parse order.landing_site URL for utm_* params
    Tier 3: Parse order.referrer_url for utm_* params
    
    Returns:
        {
            'utm_source': str,
            'utm_medium': str,
            'utm_campaign': str,
            'utm_content': str,
            'utm_term': str,
            'attribution_quality': AttributionQuality
        }
    """
    utm_params = {
        'utm_source': None,
        'utm_medium': None,
        'utm_campaign': None,
        'utm_content': None,
        'utm_term': None,
        'attribution_quality': AttributionQuality.NONE
    }
    
    # Tier 1: customerJourney (GraphQL field)
    customer_journey = order.get('customerJourney')
    if customer_journey and customer_journey.get('lastVisit'):
        last_visit = customer_journey['lastVisit']
        cj_utm = last_visit.get('utmParameters', {})
        
        if cj_utm:
            utm_params.update({
                'utm_source': cj_utm.get('source'),
                'utm_medium': cj_utm.get('medium'),
                'utm_campaign': cj_utm.get('campaign'),
                'utm_content': cj_utm.get('content'),
                'utm_term': cj_utm.get('term'),
                'attribution_quality': AttributionQuality.CJ
            })
            
            logger.debug(f"Order {order['id']}: Tier 1 attribution (customerJourney)")
            return utm_params
    
    # Tier 2: landing_site (REST field)
    landing_site = order.get('landing_site')
    if landing_site:
        parsed = urlparse(landing_site)
        query_params = parse_qs(parsed.query)
        
        if 'utm_campaign' in query_params:
            utm_params.update({
                'utm_source': query_params.get('utm_source', [None])[0],
                'utm_medium': query_params.get('utm_medium', [None])[0],
                'utm_campaign': query_params.get('utm_campaign', [None])[0],
                'utm_content': query_params.get('utm_content', [None])[0],
                'utm_term': query_params.get('utm_term', [None])[0],
                'attribution_quality': AttributionQuality.LANDING_SITE
            })
            
            logger.debug(f"Order {order['id']}: Tier 2 attribution (landing_site)")
            return utm_params
    
    # Tier 3: referrer_url
    referrer = order.get('referrer_url') or order.get('referring_site')
    if referrer:
        parsed = urlparse(referrer)
        query_params = parse_qs(parsed.query)
        
        if 'utm_campaign' in query_params:
            utm_params.update({
                'utm_source': query_params.get('utm_source', [None])[0],
                'utm_medium': query_params.get('utm_medium', [None])[0],
                'utm_campaign': query_params.get('utm_campaign', [None])[0],
                'utm_content': query_params.get('utm_content', [None])[0],
                'utm_term': query_params.get('utm_term', [None])[0],
                'attribution_quality': AttributionQuality.REFERRER
            })
            
            logger.debug(f"Order {order['id']}: Tier 3 attribution (referrer)")
            return utm_params
    
    # No attribution data found
    logger.warning(f"Order {order['id']}: No attribution data (customerJourney null, no UTM in URLs)")
    return utm_params


async def match_order_to_campaign(utm_campaign: str) -> Optional[str]:
    """
    Match utm_campaign to strategy_tag and campaign_id
    
    Expected format: {strategy_tag}_{yyyymmdd}
    Example: "high-value-birthstone_20241229"
    """
    if not utm_campaign:
        return None
    
    # Parse campaign name
    parts = utm_campaign.split('_')
    if len(parts) < 2:
        logger.warning(f"Unexpected utm_campaign format: {utm_campaign}")
        return None
    
    # Extract strategy_tag (everything except last part which is date)
    strategy_tag = '_'.join(parts[:-1])
    date_str = parts[-1]
    
    # Find matching campaign
    campaign = await db.get_campaign_by_strategy_and_date(strategy_tag, date_str)
    
    if campaign:
        return campaign['campaign_id']
    else:
        logger.warning(f"No campaign found for utm_campaign: {utm_campaign}")
        return None
```

**Shopify Orders Collection:**
```python
async def collect_shopify_conversions(since: str, until: str):
    """
    Collect orders from Shopify and attribute to campaigns
    
    Uses attribution waterfall to handle customerJourney nullability
    """
    # Fetch orders via Shopify GraphQL
    orders_query = f"""
        query {{
          orders(first: 250, query: "created_at:>='{since}' created_at:<='{until}'") {{
            edges {{
              node {{
                id
                name
                createdAt
                totalPriceSet {{
                  shopMoney {{
                    amount
                  }}
                }}
                customerJourney {{
                  lastVisit {{
                    utmParameters {{
                      source
                      medium
                      campaign
                      content
                      term
                    }}
                  }}
                }}
                landingSite
                referrerUrl
                lineItems(first: 50) {{
                  edges {{
                    node {{
                      product {{
                        id
                        handle
                      }}
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
    """
    
    orders_result = await shopify_graphql.query(orders_query)
    orders = orders_result['data']['orders']['edges']
    
    logger.info(f"Processing {len(orders)} orders for attribution (window: {since} to {until})")
    
    # CRITICAL: Track attribution quality distribution
    quality_counts = {'CJ': 0, 'LANDING_SITE': 0, 'REFERRER': 0, 'NONE': 0}
    
    for edge in orders:
        order = edge['node']
        
        # Extract UTM parameters (waterfall)
        utm_data = await extract_utm_parameters(order)
        
        # Track quality
        quality_counts[utm_data['attribution_quality'].value] += 1
        
        # Validate UTM contract
        if not validate_utm_contract(utm_data):
            logger.warning(f"Order {order['name']}: UTM contract violation - attribution may fail")
        
        # Match to campaign
        campaign_id = await match_order_to_campaign(utm_data['utm_campaign'])
        
        if campaign_id:
            # Store attribution
            await db.save_order_attribution({
                'order_id': order['id'],
                'order_name': order['name'],
                'created_at': order['createdAt'],
                'total_amount': float(order['totalPriceSet']['shopMoney']['amount']),
                'campaign_id': campaign_id,
                'utm_source': utm_data['utm_source'],
                'utm_medium': utm_data['utm_medium'],
                'utm_campaign': utm_data['utm_campaign'],
                'utm_content': utm_data['utm_content'],
                'utm_term': utm_data['utm_term'],
                'attribution_quality': utm_data['attribution_quality'].value,
                'product_handles': [
                    item['node']['product']['handle'] 
                    for item in order['lineItems']['edges']
                ]
            })
            
            logger.info(f"✓ Attributed order {order['name']} to campaign {campaign_id} (quality: {utm_data['attribution_quality'].value})")
        else:
            logger.debug(f"Order {order['name']} has no campaign attribution")
    
    # Log attribution quality summary
    total_orders = len(orders)
    logger.info(f"Attribution quality distribution: {quality_counts}")
    
    if total_orders > 0:
        cj_pct = (quality_counts['CJ'] / total_orders) * 100
        logger.info(f"High-quality attribution (customerJourney): {cj_pct:.1f}%")
        
        if cj_pct < 50:
            logger.warning(f"Low customerJourney coverage ({cj_pct:.1f}%) - check privacy settings or collection frequency")
```

**Collection Frequency Recommendation:**

```python
# RECOMMENDED: Daily collection (preserves customerJourney quality)
SHOPIFY_COLLECTION_FREQUENCY = "daily"

# NOT RECOMMENDED: Weekly/monthly (risks losing customerJourney data)
# customerJourney scope is ~30 days, so delays reduce Tier 1 attribution
```

### 7.5 Database Schema (SQLite)

**Metrics Table (with Complete Join Keys):**
```sql
CREATE TABLE metrics (
    account_id TEXT NOT NULL,
    level TEXT NOT NULL,  -- 'campaign' or 'ad'
    object_id TEXT NOT NULL,  -- Campaign ID or Ad ID
    date TEXT NOT NULL,  -- YYYY-MM-DD
    
    -- CRITICAL: Join keys for creative analysis
    campaign_id TEXT,  -- Always populated (even for ad-level)
    adset_id TEXT,     -- Populated for ad-level only
    ad_id TEXT,        -- Populated for ad-level only (same as object_id)
    creative_id TEXT,  -- Populated when available
    strategy_tag TEXT, -- For performance grouping
    run_id TEXT,       -- For cohort analysis
    
    -- Core metrics
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,  -- link_clicks (diagnostic)
    spend REAL DEFAULT 0.0,
    ctr REAL DEFAULT 0.0,
    cpc REAL DEFAULT 0.0,
    reach INTEGER DEFAULT 0,
    frequency REAL DEFAULT 0.0,
    
    -- CRITICAL: Outbound metrics (primary traffic signal)
    outbound_clicks INTEGER DEFAULT 0,
    outbound_clicks_ctr REAL DEFAULT 0.0,
    
    -- Settlement tracking
    is_settled BOOLEAN DEFAULT FALSE,
    last_refreshed_at TEXT,
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (account_id, level, object_id, date)
);

CREATE INDEX idx_metrics_date ON metrics(date);
CREATE INDEX idx_metrics_object ON metrics(object_id);
CREATE INDEX idx_metrics_settled ON metrics(is_settled);
CREATE INDEX idx_metrics_campaign ON metrics(campaign_id);
CREATE INDEX idx_metrics_strategy ON metrics(strategy_tag);
CREATE INDEX idx_metrics_creative ON metrics(creative_id);
```

**CRITICAL: Why Complete Join Keys Matter**

Without `campaign_id`, `adset_id`, `ad_id`, and `creative_id` stored together:
- Cannot answer "which creative/product performed best"
- Cannot roll up ad-level metrics to campaign-level
- Cannot correlate strategy_tag performance across campaigns

**Metadata Population During Collection:**
```python
async def enrich_ad_metrics_with_hierarchy(ad_metrics: dict, campaign_id: str) -> dict:
    """
    Enrich ad-level metrics with complete hierarchy
    
    CRITICAL: Store all join keys for creative analysis
    """
    # Fetch ad details to get adset_id and creative_id
    ad_details = await shopify_graphql.query(f"""
        query {{
          ad(id: "{ad_metrics['ad_id']}") {{
            id
            adset {{
              id
            }}
            creative {{
              id
            }}
          }}
        }}
    """)
    
    ad = ad_details['data']['ad']
    
    return {
        **ad_metrics,
        'campaign_id': campaign_id,  # From parent
        'adset_id': ad['adset']['id'],
        'ad_id': ad['id'],
        'creative_id': ad.get('creative', {}).get('id'),
        'strategy_tag': await get_strategy_tag_for_campaign(campaign_id),
        'run_id': await get_run_id_for_campaign(campaign_id)
    }
```

**Order Attribution Table:**
```sql
CREATE TABLE order_attributions (
    order_id TEXT PRIMARY KEY,
    order_name TEXT,
    created_at TEXT,
    total_amount REAL,
    
    -- Campaign attribution
    campaign_id TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    
    -- Quality tracking
    attribution_quality TEXT,  -- 'customerJourney', 'landing_site', 'referrer', 'none'
    
    -- Product details
    product_handles TEXT,  -- JSON array
    
    FOREIGN KEY (campaign_id) REFERENCES advertising_campaigns(campaign_id)
);

CREATE INDEX idx_orders_campaign ON order_attributions(campaign_id);
CREATE INDEX idx_orders_date ON order_attributions(created_at);
CREATE INDEX idx_orders_quality ON order_attributions(attribution_quality);
```

**Campaign Performance View (Aggregated):**
```sql
CREATE VIEW campaign_performance AS
SELECT 
    m.object_id AS campaign_id,
    c.strategy_tag,
    COUNT(DISTINCT m.date) AS days_active,
    SUM(m.impressions) AS total_impressions,
    SUM(m.outbound_clicks) AS total_outbound_clicks,
    SUM(m.spend) AS total_spend,
    AVG(m.outbound_clicks_ctr) AS avg_outbound_ctr,
    AVG(m.cpc) AS avg_cpc,
    COUNT(DISTINCT o.order_id) AS attributed_orders,
    SUM(o.total_amount) AS attributed_revenue,
    CASE 
        WHEN SUM(m.spend) > 0 
        THEN SUM(o.total_amount) / SUM(m.spend)
        ELSE 0
    END AS roas
FROM metrics m
LEFT JOIN advertising_campaigns c ON m.object_id = c.campaign_id
LEFT JOIN order_attributions o ON m.object_id = o.campaign_id
WHERE m.level = 'campaign'
GROUP BY m.object_id, c.strategy_tag;
```

### 7.6 JSONL Audit Trail

**Purpose:** Raw API responses for debugging and SQLite rebuild capability.

```python
async def save_raw_insights_jsonl(object_id: str, insights_data: List[dict]):
    """
    Save raw Meta Insights API response to JSONL
    
    CRITICAL: Enables SQLite rebuild if corruption occurs
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    jsonl_path = Path(f"data/metrics/raw_insights_{date_str}.jsonl")
    
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    
    record = {
        'object_id': object_id,
        'collected_at': datetime.utcnow().isoformat(),
        'insights': insights_data
    }
    
    async with aiofiles.open(jsonl_path, 'a') as f:
        await f.write(json.dumps(record, ensure_ascii=False) + '\n')


async def rebuild_sqlite_from_jsonl(jsonl_path: Path):
    """
    Rebuild SQLite metrics from JSONL audit trail
    
    Use case: Database corruption or data recovery
    """
    logger.info(f"Rebuilding SQLite from {jsonl_path}")
    
    async with aiofiles.open(jsonl_path, 'r') as f:
        async for line in f:
            record = json.loads(line)
            
            for insight in record['insights']:
                await db.upsert_metric(
                    account_id=AD_ACCOUNT_ID,
                    level=insight.get('level', 'campaign'),
                    object_id=record['object_id'],
                    date=insight['date_stop'],
                    metrics=insight,
                    is_settled=True  # Assume settled during rebuild
                )
    
    logger.info("✓ SQLite rebuild complete")
```

### 7.7 Scheduling & Execution

**Daily Batch Job:**
```python
import schedule

async def metrics_collection_job():
    """
    Daily metrics collection job
    
    Schedule: After Meta reporting close (account timezone + 4 hours)
    """
    logger.info("=" * 60)
    logger.info("METRICS COLLECTION JOB STARTED")
    logger.info("=" * 60)
    
    try:
        # Calculate rolling window
        since, until = await calculate_rolling_window('America/New_York')
        
        # Collect Meta Insights
        await collect_all_campaign_metrics(since, until)
        
        # Collect Shopify conversions
        await collect_shopify_conversions(since, until)
        
        # Optional: Weekly backfill (last 14 days)
        if datetime.now().weekday() == 0:  # Monday
            logger.info("Running weekly backfill")
            backfill_since = (datetime.now() - timedelta(days=14)).date()
            await collect_all_campaign_metrics(backfill_since, until)
        
        logger.info("=" * 60)
        logger.info("METRICS COLLECTION JOB COMPLETED")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        await send_alert({
            'type': 'METRICS_COLLECTION_FAILURE',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })


# Schedule job (runs at 6 AM Eastern - after 2 AM reporting close + 4 hours)
schedule.every().day.at("06:00").do(lambda: asyncio.create_task(metrics_collection_job()))
```

### 7.8 Error Handling & Backfill

**Retry Strategy (Up to 72 Hours):**
```python
async def fetch_with_settlement_retry(
    object_id: str,
    level: str,
    date: str,
    max_attempts: int = 3,
    ttl_hours: int = 72
) -> Optional[dict]:
    """
    Fetch metrics with retry for settlement window
    
    If data is incomplete/missing within 72h window, retry
    """
    attempt_date = datetime.fromisoformat(date).date()
    age_hours = (datetime.now().date() - attempt_date).days * 24
    
    if age_hours > ttl_hours:
        logger.warning(f"Metric date {date} beyond TTL ({ttl_hours}h) - marking as incomplete")
        return None
    
    for attempt in range(max_attempts):
        try:
            metrics = await fetch_meta_insights(
                object_id=object_id,
                level=level,
                since=date,
                until=date
            )
            
            if metrics:
                return metrics[0]  # Single day
            else:
                # Empty response - data not ready
                logger.warning(f"Empty metrics for {object_id} on {date} - retry {attempt+1}/{max_attempts}")
                await asyncio.sleep(3600 * (2 ** attempt))  # Exponential: 1h, 2h, 4h
        
        except Exception as e:
            logger.error(f"Fetch failed for {object_id} on {date}: {e}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(3600)
    
    return None
```

### 7.9 Configuration Reference

```python
class MetricsConfig:
    # Collection schedule
    AD_ACCOUNT_TIMEZONE: str = "America/New_York"
    COLLECTION_TIME: str = "06:00"  # After reporting close + 4 hours
    ROLLING_WINDOW_DAYS: int = 3
    
    # Settlement
    SETTLEMENT_THRESHOLD_DAYS: int = 2  # Mark settled after 72 hours
    BACKFILL_TTL_HOURS: int = 72
    WEEKLY_BACKFILL_DAYS: int = 14
    
    # Metrics set
    V1_METRICS: List[str] = [
        'impressions',
        'spend',
        'reach',
        'frequency',
        'link_clicks',  # Diagnostic
        'ctr',
        'cpc',
        'outbound_clicks',  # CRITICAL: Primary traffic metric
        'outbound_clicks_ctr'
    ]
    
    # Aggregation levels
    COLLECT_CAMPAIGN_LEVEL: bool = True
    COLLECT_AD_LEVEL: bool = True
    COLLECT_PRODUCT_LEVEL: bool = False  # V2
    
    # Rate limiting
    REQUEST_DELAY_SECONDS: int = 2
    RATE_LIMIT_RETRY_DELAY: int = 60
    THROTTLE_HEADER_CHECK: bool = True  # Monitor x-fb-ads-insights-throttle
    
    # Data retention
    RETENTION_DAYS: int = 365  # 1 year (safe for V1)
    
    # Storage paths
    JSONL_BASE_PATH: str = "data/metrics"
    SQLITE_DB_PATH: str = "data/metrics.db"
```

**CRITICAL: Meta 2026-01-12 Retention Changes**

⚠️ **Risk Note:** Starting January 12, 2026, Meta restricts:
- Attribution windows for certain breakdowns
- Historical retention for unique fields (>13 months restricted)
- Frequency breakdowns (>6 months restricted)

**V1 Mitigation:**
- 1-year retention is safe (within limits)
- Avoid designs requiring >13-month unique field queries
- Avoid frequency breakdowns older than 6 months
- Verify current limits if extending retention beyond 1 year

**Recommendation:** Monitor Meta's policy updates and adjust retention strategy accordingly.

---

**Summary of Critical Features:**
1. ✓ Settlement window (3-day rolling, UPSERT strategy)
2. ✓ Attribution waterfall (customerJourney → landing_site → referrer)
3. ✓ Outbound clicks (primary traffic metric, not just link_clicks)
4. ✓ Campaign + Ad-level aggregation
5. ✓ JSONL + SQLite dual storage (rebuildable)
6. ✓ Sequential API requests (rate limit safe)
7. ✓ Retry with backoff (up to 72h)
8. ✓ Daily batch after reporting close
9. ✓ Weekly backfill (14 days)
10. ✓ 1-year retention
11. ✓ Per-campaign conversion tracking
12. ✓ Attribution quality tracking

**Patch Additions (Completeness):**
13. ✓ Meta throttle header monitoring (x-fb-ads-insights-throttle)
14. ✓ 2026-01-12 retention risk note (attribution/frequency limits)
15. ✓ Complete join keys (campaign_id, adset_id, ad_id, creative_id, strategy_tag, run_id)
16. ✓ Explicit UTM contract (deterministic attribution scheme)
17. ✓ Shopify customerJourney 30-day window (daily collection recommended)

**Data Quality Guarantees:**
- is_settled flag prevents treating preliminary data as final
- UPSERT ensures late updates don't create duplicates
- Attribution waterfall handles customerJourney nullability
- outbound_clicks provides accurate traffic signal
- JSONL enables full audit trail and SQLite rebuild
- Throttle header monitoring prevents rate limit violations
- Complete join keys enable creative/product performance analysis
- UTM contract validation ensures attribution accuracy
- Daily collection preserves high-quality attribution data

---

## 8. Feedback Loop Architecture

**Purpose:** Continuously improve SEO and advertising performance by analyzing metrics, identifying underperformers, and triggering context-aware refinements with human approval gates.

### 8.1 Overview

```
┌─────────────────────────────────────────────────────────────────┐
│         Daily Feedback Loop Analysis (Post-Settlement)          │
│  Runs after metrics settle (4+ days delay from ad launch)       │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Load metrics from Section 7
┌─────────────────────────────────────────────────────────────────┐
│              Candidate Selection (Deterministic)                 │
│  - Filter by strategy_tag                                        │
│  - Score: weighted(outbound_ctr_z, cpc_z, spend, age)           │
│  - Select bottom-K worst performers (K=3 default)                │
│  - Apply: minimum spend, minimum impressions gates              │
│  - Enforce: per-product cooldown (7 days minimum)               │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ For each candidate
┌─────────────────────────────────────────────────────────────────┐
│           Metric-to-Action Matrix (Routing Logic)                │
│  Routes refinement to correct layer based on funnel stage:       │
│  - Low outbound CTR → Ads Agent (creative refresh)              │
│  - High CTR + low engagement → SEO Agent (landing mismatch)     │
│  - Good CTR + high CPC → Ads Agent (targeting/relevance)        │
│  - Spend threshold no signal → Human review required            │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Generate refinement proposal
┌─────────────────────────────────────────────────────────────────┐
│        Refinement Context Builder (LLM Input)                    │
│  Enrichment sources:                                             │
│  - Current metrics (outbound_ctr, cpc, spend, conversions)      │
│  - Current SEO (title, meta, description, images)               │
│  - Current ad creative (headline, primary_text, destination)    │
│  - Product reviews (when available)                             │
│  - Strategy-tag playbook (learned patterns)                     │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ LLM generates challenger
┌─────────────────────────────────────────────────────────────────┐
│      Hypothesis-Driven Single Challenger Generation              │
│  Champion vs Challenger methodology:                             │
│  - Single variable change (headline OR first-120 chars OR hero) │
│  - Context-aware hypothesis (low CTR = weak value prop)         │
│  - Preserve brand voice and constraints                         │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Human approval gate
┌─────────────────────────────────────────────────────────────────┐
│              Approval Queue (Google Sheets/N8N)                  │
│  Present:                                                        │
│  - Product ID + strategy_tag                                    │
│  - Current version (champion)                                   │
│  - Proposed version (challenger)                                │
│  - Delta summary (what changed)                                 │
│  - Trigger metrics snapshot                                     │
│  - Hypothesis/reason                                            │
│  Actions: APPROVE | REJECT | DEFER                              │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ If approved
┌─────────────────────────────────────────────────────────────────┐
│           Apply Refinement + Version Control                     │
│  1. Store champion in seo_versions (rollback support)           │
│  2. Apply challenger to product                                 │
│  3. Increment product.version                                   │
│  4. Flag ads for creative refresh (if SEO changed)              │
│  5. Set cooldown (7 days minimum)                               │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Sequential testing
┌─────────────────────────────────────────────────────────────────┐
│        Champion vs Challenger Evaluation (7 days each)           │
│  Day 0-7: Champion baseline (using settled metrics only)        │
│  Day 8-14: Challenger metrics                                   │
│  Settlement buffer: Exclude last 4 days from both windows       │
│  Stable window = [window_start, window_end - settlement_lag]    │
│  Compare: outbound_ctr, cpc, conversions (settled data only)    │
│  Success: Beats strategy_tag baseline + relative lift           │
│  Failure: Auto-flag "ROLLBACK RECOMMENDED"                      │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ Learning capture
┌─────────────────────────────────────────────────────────────────┐
│         Strategy-Tag Playbook (Cross-Campaign Learning)          │
│  Store patterns:                                                 │
│  - "high-value-birthstone: CTR improves when title <50 chars"   │
│  - "seasonal-gift: Hero image with lifestyle context +35% CTR"  │
│  - "premium-collection: Emphasize craftsmanship in first line"  │
└─────────────────────────────────────────────────────────────────┘
```

**V1 Scope:**
- ✓ Daily analysis (post-settlement)
- ✓ Automated alerts with human approval
- ✓ Metric-to-Action Matrix (funnel stage routing)
- ✓ Champion vs Challenger (single variable)
- ✓ Sequential testing (7 days each)
- ✓ Version control with rollback
- ✓ Ad creative refresh flagging
- ✓ Strategy-tag learning
- ✓ Product reviews enrichment
- ✗ Fully autonomous refinement (deferred to V2)
- ✗ Multi-variant testing (too slow for V1)
- ✗ Competitor analysis (deferred to V2)

### 8.2 Metric-to-Action Matrix (Critical Contract)

**CRITICAL: Prevents Generic "Improve SEO" Prompts**

The matrix routes refinements to the correct agent (Ads vs SEO) based on funnel stage diagnosis.

```python
from enum import Enum
from typing import Dict, Any, Optional

class FunnelStage(Enum):
    TOP_OF_FUNNEL = "top_of_funnel"        # Ad creative issue
    MID_FUNNEL = "mid_funnel"              # Landing/SEO mismatch
    TARGETING = "targeting"                # Audience/relevance issue
    INSUFFICIENT_DATA = "insufficient_data" # Need more signal

class ActionRouter:
    """
    Routes refinement actions based on metric patterns
    
    CRITICAL: Diagnoses funnel stage to prevent wasted effort
    """
    
    # Thresholds (configurable)
    LOW_OUTBOUND_CTR_THRESHOLD = 0.005  # 0.5%
    HIGH_CPC_THRESHOLD = 2.00  # $2.00
    MIN_SPEND_FOR_SIGNAL = 50.00  # $50
    MIN_OUTBOUND_CLICKS_FOR_SIGNAL = 20
    
    def diagnose_funnel_stage(self, metrics: Dict[str, Any], 
                              site_metrics: Optional[Dict] = None) -> FunnelStage:
        """
        Diagnose which funnel stage is failing
        
        Args:
            metrics: Ad metrics (outbound_ctr, cpc, spend, outbound_clicks)
            site_metrics: Optional Shopify metrics (sessions, add_to_cart, purchases)
        
        Returns:
            FunnelStage enum
        """
        outbound_ctr = metrics.get('outbound_clicks_ctr', 0)
        cpc = metrics.get('cpc', 0)
        spend = metrics.get('spend', 0)
        outbound_clicks = metrics.get('outbound_clicks', 0)
        
        # CASE 4: Insufficient data
        if spend < self.MIN_SPEND_FOR_SIGNAL or outbound_clicks < self.MIN_OUTBOUND_CLICKS_FOR_SIGNAL:
            return FunnelStage.INSUFFICIENT_DATA
        
        # CASE 1: Low outbound CTR (top-of-funnel failure)
        if outbound_ctr < self.LOW_OUTBOUND_CTR_THRESHOLD:
            return FunnelStage.TOP_OF_FUNNEL
        
        # CASE 2: High CTR + low conversions (mid-funnel failure)
        # V1: Use UTM-attributed conversions (Section 7 waterfall)
        # site_metrics (GA4) is OPTIONAL enrichment only
        attributed_orders = metrics.get('attributed_orders', 0)
        
        # HIGH clicks + ZERO conversions = landing/SEO problem
        if outbound_clicks >= self.MIN_OUTBOUND_CLICKS_FOR_SIGNAL:
            if attributed_orders == 0:
                return FunnelStage.MID_FUNNEL  # Clicks not converting to orders
        
        # Optional: If site_metrics available (V2/GA4 integration)
        if site_metrics:
            bounce_rate = site_metrics.get('bounce_rate', 0)
            if outbound_ctr >= self.LOW_OUTBOUND_CTR_THRESHOLD and bounce_rate > 0.7:
                return FunnelStage.MID_FUNNEL
        
        # CASE 3: Good CTR + high CPC (targeting/relevance issue)
        if outbound_ctr >= self.LOW_OUTBOUND_CTR_THRESHOLD and cpc > self.HIGH_CPC_THRESHOLD:
            return FunnelStage.TARGETING
        
        # Default: Mid-funnel (most common for SEO refinement)
        return FunnelStage.MID_FUNNEL
    
    def get_action_plan(self, funnel_stage: FunnelStage, 
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate action plan based on funnel stage
        
        Returns:
            {
                'primary_agent': 'ads' | 'seo',
                'action_type': str,
                'hypothesis': str,
                'single_variable': str,
                'requires_creative_refresh': bool
            }
        """
        if funnel_stage == FunnelStage.TOP_OF_FUNNEL:
            return {
                'primary_agent': 'ads',
                'action_type': 'creative_refresh',
                'hypothesis': 'Ad creative/offer/hero image likely weak - not capturing attention',
                'single_variable': 'headline OR primary_text OR hero_image',
                'requires_creative_refresh': True,
                'seo_action': 'align_first_line_value_prop'  # Minor SEO alignment only
            }
        
        elif funnel_stage == FunnelStage.MID_FUNNEL:
            return {
                'primary_agent': 'seo',
                'action_type': 'landing_optimization',
                'hypothesis': 'Landing/SEO/value prop mismatch - clicks not converting to engagement',
                'single_variable': 'title OR first_160_chars OR trust_signals',
                'requires_creative_refresh': True,  # Keep ad mostly stable, adjust to match new promise
                'ads_action': 'minimal_alignment'
            }
        
        elif funnel_stage == FunnelStage.TARGETING:
            return {
                'primary_agent': 'ads',
                'action_type': 'targeting_adjustment',
                'hypothesis': 'Auction/targeting/creative relevance issue - paying too much for clicks',
                'single_variable': 'targeting OR creative_promise_tightening',
                'requires_creative_refresh': False,
                'seo_action': None
            }
        
        else:  # INSUFFICIENT_DATA
            return {
                'primary_agent': None,
                'action_type': 'human_review_required',
                'hypothesis': 'Insufficient data - wrong audience or need more time',
                'single_variable': None,
                'requires_creative_refresh': False
            }
```

**Action Plan Examples:**

| Metrics Pattern | Diagnosis | Primary Agent | Action | Single Variable |
|----------------|-----------|---------------|--------|-----------------|
| CTR: 0.3%, CPC: $1.50 | Top-of-funnel | Ads Agent | Refresh headline | "headline" |
| CTR: 1.2%, Bounce: 75% | Mid-funnel | SEO Agent | Rewrite first 160 chars | "description_intro" |
| CTR: 1.5%, CPC: $3.00 | Targeting | Ads Agent | Tighten targeting | "audience" |
| Spend: $30, Clicks: 8 | Insufficient | Human | Review/wait | None |

### 8.3 Candidate Selection (Deterministic Scoring)

**CRITICAL: Prevent Noisy/Random Selection**

```python
import numpy as np
from typing import List, Dict

async def select_refinement_candidates(
    strategy_tag: str,
    max_candidates: int = 3,
    min_spend: float = 50.0,
    min_impressions: int = 1000
) -> List[Dict[str, Any]]:
    """
    Select worst-performing products for refinement
    
    CRITICAL: Deterministic scoring prevents random churn
    
    Args:
        strategy_tag: Focus on single strategy
        max_candidates: Top-K worst (default 3)
        min_spend: Minimum spend for signal
        min_impressions: Minimum impressions for signal
    
    Returns:
        List of products with scores and context
    """
    # Fetch campaign products with metrics
    products = await db.get_campaign_products_with_metrics(strategy_tag)
    
    # Filter by minimum thresholds
    eligible = [
        p for p in products 
        if p['spend'] >= min_spend and p['impressions'] >= min_impressions
    ]
    
    if not eligible:
        logger.info(f"No eligible candidates for {strategy_tag} (insufficient spend/impressions)")
        return []
    
    # Calculate strategy-tag baseline (median)
    strategy_baseline = await calculate_strategy_baseline(strategy_tag)
    
    # Score each product
    scored_products = []
    for product in eligible:
        # Z-scores (how far below baseline)
        outbound_ctr_z = calculate_z_score(
            product['outbound_clicks_ctr'],
            strategy_baseline['outbound_ctr_mean'],
            strategy_baseline['outbound_ctr_std']
        )
        
        cpc_z = calculate_z_score(
            product['cpc'],
            strategy_baseline['cpc_mean'],
            strategy_baseline['cpc_std']
        )
        
        # Weighted score (lower is worse)
        # High weight on CTR (primary), moderate on CPC, bonus for high spend
        score = (
            (outbound_ctr_z * -2.0) +  # Negative Z means below average (bad)
            (cpc_z * 1.0) +              # Positive Z means above average (bad)
            (product['spend'] / 100)     # Bonus for high spend (more confidence)
        )
        
        # ENFORCEMENT: Cooldown + max iterations + pending approval
        last_refinement = await db.get_last_refinement_date(product['product_id'])
        if last_refinement:
            days_since = (datetime.now().date() - last_refinement).days
            if days_since < FeedbackLoopConfig.COOLDOWN_DAYS:
                logger.debug(f"Skipping {product['product_id']} - cooldown ({days_since} days)")
                continue
        
        iteration_count = await db.get_iteration_count(product['product_id'])
        if iteration_count >= FeedbackLoopConfig.MAX_ITERATIONS_PER_PRODUCT:
            logger.debug(f"Skipping {product['product_id']} - max iterations reached ({iteration_count})")
            continue
        
        if await db.has_pending_approval(product['product_id']):
            logger.debug(f"Skipping {product['product_id']} - pending approval exists")
            continue
        
        scored_products.append({
            **product,
            'underperformance_score': score,
            'outbound_ctr_z': outbound_ctr_z,
            'cpc_z': cpc_z
        })
    
    # Sort by score (highest = worst performers)
    scored_products.sort(key=lambda x: x['underperformance_score'], reverse=True)
    
    # Select top-K
    candidates = scored_products[:max_candidates]
    
    logger.info(f"Selected {len(candidates)} candidates for {strategy_tag}")
    for c in candidates:
        logger.info(f"  - {c['product_handle']}: score={c['underperformance_score']:.2f}, CTR_z={c['outbound_ctr_z']:.2f}")
    
    return candidates


def calculate_z_score(value: float, mean: float, std: float) -> float:
    """Calculate Z-score (standard deviations from mean)"""
    if std == 0:
        return 0
    return (value - mean) / std


async def calculate_strategy_baseline(strategy_tag: str) -> Dict[str, float]:
    """
    Calculate baseline metrics for strategy_tag
    
    Used for relative performance evaluation
    """
    metrics = await db.get_strategy_tag_metrics(strategy_tag)
    
    return {
        'outbound_ctr_mean': np.mean([m['outbound_clicks_ctr'] for m in metrics]),
        'outbound_ctr_std': np.std([m['outbound_clicks_ctr'] for m in metrics]),
        'outbound_ctr_median': np.median([m['outbound_clicks_ctr'] for m in metrics]),
        'cpc_mean': np.mean([m['cpc'] for m in metrics]),
        'cpc_std': np.std([m['cpc'] for m in metrics]),
        'cpc_median': np.median([m['cpc'] for m in metrics])
    }
```

### 8.4 Refinement Context Builder

**CRITICAL: Provide Rich Context to LLM**

```python
async def build_refinement_context(
    product: Dict[str, Any],
    funnel_stage: FunnelStage,
    action_plan: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build comprehensive context for LLM refinement request
    
    Enrichment sources:
    - Metrics (current performance)
    - SEO (current content)
    - Ad creative (current messaging)
    - Reviews (customer voice)
    - Playbook (learned patterns)
    """
    # Fetch current SEO
    current_seo = await db.get_product_seo(product['product_id'])
    
    # Fetch current ad creative
    ad_creative = await db.get_ad_creative_for_product(product['product_id'])
    
    # Fetch product reviews (top 5 most helpful)
    # NOTE: Shopify has NO native reviews API
    # Requires third-party app integration (Judge.me, Loox, Yotpo, etc.)
    # V1: reviews = None (skip enrichment)
    # V2: Integrate specific review app API
    reviews = None  # V1: Disabled until review app connector defined
    # V2 Example:
    # reviews = await review_app.get_product_reviews(
    #     product['product_id'],
    #     limit=5,
    #     sort='most_helpful'
    # )
    
    # Fetch strategy-tag playbook
    playbook = await db.get_strategy_playbook(product['strategy_tag'])
    
    # Extract review themes (simple keyword extraction)
    review_themes = extract_review_themes(reviews) if reviews else None
    
    context = {
        'product_id': product['product_id'],
        'product_handle': product['handle'],
        'strategy_tag': product['strategy_tag'],
        
        # Performance metrics
        'metrics': {
            'outbound_clicks_ctr': product['outbound_clicks_ctr'],
            'cpc': product['cpc'],
            'spend': product['spend'],
            'outbound_clicks': product['outbound_clicks'],
            'impressions': product['impressions'],
            'conversions': product.get('attributed_orders', 0),
            'revenue': product.get('attributed_revenue', 0)
        },
        
        # Strategy-tag baseline (for comparison)
        'strategy_baseline': {
            'median_outbound_ctr': product.get('strategy_baseline_ctr'),
            'median_cpc': product.get('strategy_baseline_cpc')
        },
        
        # Current SEO content
        'current_seo': {
            'title': current_seo['title'],
            'meta_title': current_seo['meta_title'],
            'meta_description': current_seo['meta_description'],
            'description_first_160': current_seo['description_html'][:160],
            'hero_image_alt': current_seo['images'][0]['alt_text'] if current_seo['images'] else None,
            'tags': current_seo['tags']
        },
        
        # Current ad creative
        'current_ad_creative': {
            'headline': ad_creative['headline'],
            'primary_text': ad_creative['primary_text'],
            'description': ad_creative['description'],
            'destination_url': ad_creative['destination_url']
        } if ad_creative else None,
        
        # Funnel diagnosis
        'funnel_stage': funnel_stage.value,
        'action_plan': action_plan,
        
        # Customer voice (enrichment)
        'review_themes': review_themes,
        'review_count': len(reviews) if reviews else 0,
        'avg_rating': np.mean([r['rating'] for r in reviews]) if reviews else None,
        
        # Learned patterns
        'playbook_insights': playbook.get('patterns', []) if playbook else []
    }
    
    return context


def extract_review_themes(reviews: List[Dict]) -> Dict[str, Any]:
    """
    Extract common themes from product reviews
    
    V1: Simple keyword extraction
    V2: LLM-based theme clustering
    """
    all_text = ' '.join([r['body'] for r in reviews]).lower()
    
    # Positive keywords
    positive_keywords = ['beautiful', 'quality', 'perfect', 'love', 'gorgeous', 'delicate', 'craftsmanship']
    positive_mentions = {kw: all_text.count(kw) for kw in positive_keywords if kw in all_text}
    
    # Negative keywords
    negative_keywords = ['small', 'broke', 'tarnished', 'cheap', 'disappointed', 'too thin']
    negative_mentions = {kw: all_text.count(kw) for kw in negative_keywords if kw in all_text}
    
    return {
        'positive': positive_mentions,
        'negative': negative_mentions,
        'dominant_positive': max(positive_mentions, key=positive_mentions.get) if positive_mentions else None,
        'dominant_negative': max(negative_mentions, key=negative_mentions.get) if negative_mentions else None
    }
```

### 8.5 Hypothesis-Driven Challenger Generation

**CRITICAL: Single Variable, Context-Aware**

```python
async def generate_challenger_seo(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate single-variable SEO challenger
    
    CRITICAL: Champion vs Challenger methodology
    - ONE variable changed per iteration
    - Hypothesis-driven (not random)
    - Preserves brand voice and constraints
    
    Returns:
        {
            'challenger_title': str,
            'challenger_meta_description': str,
            'challenger_description_intro': str,
            'variable_changed': str,
            'hypothesis': str,
            'change_summary': str
        }
    """
    funnel_stage = context['funnel_stage']
    action_plan = context['action_plan']
    
    # Determine single variable to change
    if funnel_stage == 'mid_funnel':
        # SEO Agent: Landing optimization
        single_variable = determine_single_variable_for_seo(context)
    elif funnel_stage == 'top_of_funnel':
        # Minor SEO alignment (Ads Agent handles creative)
        single_variable = 'first_line_value_prop'
    else:
        # No SEO changes needed
        return None
    
    # Build hypothesis-driven prompt
    prompt = build_refinement_prompt(context, single_variable)
    
    # Call LLM
    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": get_refinement_system_prompt()},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    challenger = json.loads(response.choices[0].message.content)
    
    # Enforce constraints (Section 3 guard rails)
    challenger = ConstraintGuard.enforce(challenger, context['constraints'])
    
    return {
        **challenger,
        'variable_changed': single_variable,
        'hypothesis': action_plan['hypothesis'],
        'change_summary': generate_change_summary(context['current_seo'], challenger, single_variable)
    }


def determine_single_variable_for_seo(context: Dict[str, Any]) -> str:
    """
    Determine which single variable to change based on context
    
    CRITICAL: Only ONE variable per iteration
    
    Priority order:
    1. Title (if too long or weak value prop)
    2. First 160 chars (if bounce rate high)
    3. Trust signals (if reviews mention quality concerns)
    """
    current_title = context['current_seo']['title']
    review_themes = context.get('review_themes', {})
    
    # Check title length
    if len(current_title) > 55:
        return 'title'  # Too long for mobile
    
    # Check for weak value prop (no birthstone/material mention)
    if context['strategy_tag'] == 'high-value-birthstone':
        # Birthstone keywords (all 12 months + stones)
        BIRTHSTONE_KEYWORDS = [
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december',
            'garnet', 'amethyst', 'aquamarine', 'diamond', 'emerald', 'alexandrite',
            'ruby', 'peridot', 'sapphire', 'opal', 'tourmaline', 'topaz',
            'tanzanite', 'citrine', 'pearl', 'moonstone', 'birthstone'
        ]
        if not any(kw in current_title.lower() for kw in BIRTHSTONE_KEYWORDS):
            return 'title'  # Missing birthstone hook
    
    # Check for trust signal needs (negative reviews about quality)
    if review_themes.get('dominant_negative') in ['cheap', 'tarnished', 'broke']:
        return 'trust_signals'  # Add craftsmanship/quality language
    
    # Default: Optimize first 160 chars
    return 'first_160_chars'


def build_refinement_prompt(context: Dict[str, Any], single_variable: str) -> str:
    """Build hypothesis-driven refinement prompt for LLM"""
    
    metrics = context['metrics']
    current_seo = context['current_seo']
    playbook = context.get('playbook_insights', [])
    
    prompt = f"""You are refining SEO for an underperforming product.

**CONTEXT:**
- Product: {context['product_handle']}
- Strategy: {context['strategy_tag']}
- Funnel Stage: {context['funnel_stage']}
- Hypothesis: {context['action_plan']['hypothesis']}

**CURRENT PERFORMANCE:**
- Outbound CTR: {metrics['outbound_clicks_ctr']:.2%} (strategy median: {context['strategy_baseline']['median_outbound_ctr']:.2%})
- CPC: ${metrics['cpc']:.2f} (strategy median: ${context['strategy_baseline']['median_cpc']:.2f})
- Conversions: {metrics['conversions']} from {metrics['outbound_clicks']} clicks

**CURRENT SEO:**
- Title: {current_seo['title']}
- Meta Description: {current_seo['meta_description']}
- First 160 chars: {current_seo['description_first_160']}

**CUSTOMER VOICE (Reviews):**
{format_review_themes(context.get('review_themes'))}

**LEARNED PATTERNS (Strategy Playbook):**
{format_playbook_insights(playbook)}

**SINGLE VARIABLE TO CHANGE:** {single_variable}

**YOUR TASK:**
Generate a SINGLE challenger variant that changes ONLY the {single_variable}.

Constraints:
- Title: Max 70 chars
- Meta description: Max 320 chars
- Preserve brand voice: authentic, friendly, professional
- Banned words: {context['constraints']['banned_words']}

Output JSON only:
{{
  "challenger_title": "...",
  "challenger_meta_description": "...",
  "challenger_description_intro": "...",  // First 160 chars
  "reasoning": "Brief explanation of change strategy"
}}
"""
    
    return prompt


def format_review_themes(themes: Optional[Dict]) -> str:
    """Format review themes for LLM context"""
    if not themes:
        return "No reviews available"
    
    output = []
    if themes.get('dominant_positive'):
        output.append(f"✓ Customers love: {themes['dominant_positive']}")
    if themes.get('dominant_negative'):
        output.append(f"✗ Customers complain: {themes['dominant_negative']}")
    
    return '\n'.join(output) if output else "No strong themes"


def format_playbook_insights(insights: List[Dict]) -> str:
    """Format playbook patterns for LLM context"""
    if not insights:
        return "No learned patterns yet"
    
    return '\n'.join([f"- {p['pattern']}: {p['impact']}" for p in insights[:3]])


def generate_change_summary(champion: Dict, challenger: Dict, variable: str) -> str:
    """Generate human-readable change summary for approval queue"""
    
    if variable == 'title':
        return f"Title: '{champion['title']}' → '{challenger['challenger_title']}'"
    elif variable == 'first_160_chars':
        return f"Description intro changed (first 160 chars)"
    elif variable == 'trust_signals':
        return f"Added trust/quality language to description"
    else:
        return f"Variable '{variable}' modified"
```

### 8.6 Version Control & Rollback

**CRITICAL: Enable Rollback to Previous Versions**

```python
# Database schema
CREATE TABLE seo_versions (
    version_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    
    -- Full snapshot (not diffs)
    title TEXT,
    meta_title TEXT,
    meta_description TEXT,
    description_html TEXT,
    tags TEXT,  -- JSON array
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,  -- 'system' or user_id
    reason TEXT,  -- 'initial', 'refinement', 'rollback', 'manual'
    refinement_context TEXT,  -- JSON: trigger metrics, hypothesis
    
    -- Performance tracking
    is_active BOOLEAN DEFAULT FALSE,
    evaluation_start_date TEXT,
    evaluation_end_date TEXT,
    
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE INDEX idx_seo_versions_product ON seo_versions(product_id);
CREATE INDEX idx_seo_versions_active ON seo_versions(is_active);


-- Experiment Registry (prevents overlapping tests, enables audit)
CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    strategy_tag TEXT,
    champion_version_id TEXT NOT NULL,
    challenger_version_id TEXT,
    
    -- Timeline
    start_date TEXT NOT NULL,
    champion_window_start TEXT,
    champion_window_end TEXT,
    challenger_window_start TEXT,
    challenger_window_end TEXT,
    stable_window_used TEXT,  -- JSON: settlement buffer applied
    
    -- Results
    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE | COMPLETED | CANCELLED
    decision TEXT,  -- 'keep_champion' | 'keep_challenger' | 'rollback'
    decision_reason TEXT,
    decided_at TEXT,
    decided_by TEXT,  -- 'system' | user_id
    
    -- Metrics snapshot at decision time
    champion_metrics TEXT,  -- JSON
    challenger_metrics TEXT,  -- JSON
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (champion_version_id) REFERENCES seo_versions(version_id),
    FOREIGN KEY (challenger_version_id) REFERENCES seo_versions(version_id)
);

CREATE INDEX idx_experiments_product ON experiments(product_id);
CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_experiments_strategy ON experiments(strategy_tag);


async def save_seo_version(
    product_id: str,
    seo_data: Dict[str, Any],
    reason: str = 'refinement',
    refinement_context: Optional[Dict] = None
) -> str:
    """
    Save SEO version for rollback support
    
    CRITICAL: Store full snapshot (not diffs only)
    """
    # Get current version number
    current_version = await db.get_latest_version_number(product_id)
    new_version_number = (current_version or 0) + 1
    
    version_id = f"{product_id}_v{new_version_number}"
    
    await db.execute("""
        INSERT INTO seo_versions (
            version_id, product_id, version_number,
            title, meta_title, meta_description, description_html, tags,
            reason, refinement_context, is_active, evaluation_start_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        version_id, product_id, new_version_number,
        seo_data['title'],
        seo_data['meta_title'],
        seo_data['meta_description'],
        seo_data['description_html'],
        json.dumps(seo_data['tags']),
        reason,
        json.dumps(refinement_context) if refinement_context else None,
        True,  # New version becomes active
        datetime.now().date().isoformat()
    ))
    
    # Deactivate previous versions
    await db.execute("""
        UPDATE seo_versions 
        SET is_active = FALSE, evaluation_end_date = ?
        WHERE product_id = ? AND version_id != ?
    """, (datetime.now().date().isoformat(), product_id, version_id))
    
    logger.info(f"Saved SEO version {version_id} (reason: {reason})")
    
    return version_id


async def rollback_to_version(product_id: str, version_id: str) -> bool:
    """
    Rollback product to previous SEO version
    
    CRITICAL: Preserves version history
    """
    # Fetch target version
    version = await db.get_seo_version(version_id)
    
    if not version or version['product_id'] != product_id:
        logger.error(f"Version {version_id} not found for product {product_id}")
        return False
    
    # Apply version to product (via EcomAgent)
    seo_data = {
        'title': version['title'],
        'meta_title': version['meta_title'],
        'meta_description': version['meta_description'],
        'description_html': version['description_html'],
        'tags': json.loads(version['tags'])
    }
    
    success = await ecom_agent.update_product_seo(product_id, seo_data)
    
    if success:
        # Save rollback as new version (preserves history)
        await save_seo_version(
            product_id,
            seo_data,
            reason='rollback',
            refinement_context={'rolled_back_to': version_id}
        )
        
        logger.info(f"✓ Rolled back {product_id} to {version_id}")
        return True
    else:
        logger.error(f"Failed to rollback {product_id} to {version_id}")
        return False
```

### 8.7 Stale Ad Risk Mitigation

**CRITICAL: SEO Changes Must Flag Ads for Refresh**

```python
# Database schema
CREATE TABLE ad_creative_links (
    link_id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    ad_id TEXT NOT NULL,
    creative_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    
    -- SEO versioning
    seo_version_id TEXT,
    
    -- Status tracking
    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE | NEEDS_CREATIVE_REFRESH | PAUSED
    status_reason TEXT,
    
    -- Timestamps
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_refreshed_at TEXT,
    
    FOREIGN KEY (campaign_id) REFERENCES advertising_campaigns(campaign_id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (seo_version_id) REFERENCES seo_versions(version_id)
);

CREATE INDEX idx_ad_links_status ON ad_creative_links(status);
CREATE INDEX idx_ad_links_product ON ad_creative_links(product_id);


async def flag_ads_for_refresh(product_id: str, new_seo_version_id: str):
    """
    Flag all ads using this product for creative refresh
    
    CRITICAL: Prevents SEO/ad creative drift
    """
    # Find all active ads using this product
    ad_links = await db.execute("""
        SELECT link_id, campaign_id, ad_id, creative_id
        FROM ad_creative_links
        WHERE product_id = ? AND status = 'ACTIVE'
    """, (product_id,))
    
    for link in ad_links:
        # Update status
        await db.execute("""
            UPDATE ad_creative_links
            SET status = 'NEEDS_CREATIVE_REFRESH',
                status_reason = 'SEO_VERSION_CHANGED',
                seo_version_id = ?
            WHERE link_id = ?
        """, (new_seo_version_id, link['link_id']))
        
        logger.info(f"Flagged ad {link['ad_id']} for refresh (SEO changed)")
    
    # Queue notification for Ads Agent
    await queue_ads_refresh_task({
        'product_id': product_id,
        'new_seo_version_id': new_seo_version_id,
        'affected_ads': [l['ad_id'] for l in ad_links],
        'action': 'rebuild_creative_from_new_seo'
    })
    
    logger.info(f"✓ Flagged {len(ad_links)} ads for creative refresh")


class CreativeRefreshMode(Enum):
    PROGRAMMATIC = "programmatic"  # API can update creative
    MANUAL = "manual"              # Human must recreate ad


async def determine_refresh_mode(ad_id: str) -> CreativeRefreshMode:
    """
    Determine if ad format supports programmatic refresh
    
    CRITICAL: Meta restricts editing for certain ad formats
    - Link preview edits limited for unpublished posts
    - Some formats require copy/recreate vs edit-in-place
    - 2024+ changes limit in-place creative editing
    """
    ad_details = await meta_ads.get_ad_details(ad_id)
    
    # Check format constraints
    if ad_details.get('format') in ['CAROUSEL', 'COLLECTION', 'INSTANT_EXPERIENCE']:
        return CreativeRefreshMode.MANUAL
    
    if not ad_details.get('is_editable', True):
        return CreativeRefreshMode.MANUAL
    
    # Check if ad is using link preview (restricted)
    if ad_details.get('uses_link_preview', False):
        return CreativeRefreshMode.MANUAL
    
    return CreativeRefreshMode.PROGRAMMATIC


async def rebuild_ad_creative_from_seo(ad_id: str, new_seo_version_id: str):
    """
    Regenerate ad creative to match new SEO
    
    V1: Human approval required
    V2: Auto-deploy option
    """
    # Fetch new SEO version
    seo_version = await db.get_seo_version(new_seo_version_id)
    
    # Fetch current ad creative
    current_creative = await meta_ads.get_ad_creative(ad_id)
    
    # Generate new creative aligned with SEO
    new_creative = await generate_ad_creative_from_seo({
        'title': seo_version['title'],
        'meta_description': seo_version['meta_description'],
        'description_intro': seo_version['description_html'][:160]
    })
    
    # Queue for human approval (V1)
    await queue_creative_refresh_approval({
        'ad_id': ad_id,
        'current_headline': current_creative['headline'],
        'proposed_headline': new_creative['headline'],
        'current_primary_text': current_creative['primary_text'],
        'proposed_primary_text': new_creative['primary_text'],
        'reason': f"SEO updated to version {new_seo_version_id}",
        'seo_version_id': new_seo_version_id
    })
    
    logger.info(f"Queued ad {ad_id} creative refresh for approval")
```

### 8.8 Sequential Testing (Champion vs Challenger)

**CRITICAL: 7-Day Evaluation Windows**

```python
async def evaluate_challenger_performance(
    product_id: str,
    champion_version_id: str,
    challenger_version_id: str
) -> Dict[str, Any]:
    """
    Compare champion vs challenger performance
    
    Sequential testing: 7 days champion → 7 days challenger
    
    Returns:
        {
            'winner': 'champion' | 'challenger',
            'confidence': float,
            'metrics_comparison': dict,
            'recommendation': 'keep_challenger' | 'rollback' | 'insufficient_data'
        }
    """
    # Fetch champion metrics (7-day baseline)
    champion_metrics = await db.get_version_metrics(
        product_id,
        champion_version_id,
        days=7
    )
    
    # Fetch challenger metrics (7-day test period)
    challenger_metrics = await db.get_version_metrics(
        product_id,
        challenger_version_id,
        days=7
    )
    
    # Fetch strategy-tag baseline for comparison
    strategy_baseline = await calculate_strategy_baseline(
        await db.get_product_strategy_tag(product_id)
    )
    
    # Calculate relative improvements
    ctr_improvement = (
        (challenger_metrics['outbound_clicks_ctr'] - champion_metrics['outbound_clicks_ctr']) /
        champion_metrics['outbound_clicks_ctr']
    ) if champion_metrics['outbound_clicks_ctr'] > 0 else 0
    
    cpc_improvement = (
        (champion_metrics['cpc'] - challenger_metrics['cpc']) /
        champion_metrics['cpc']
    ) if champion_metrics['cpc'] > 0 else 0
    
    conversion_improvement = (
        (challenger_metrics['conversions'] - champion_metrics['conversions']) /
        champion_metrics['conversions']
    ) if champion_metrics['conversions'] > 0 else 0
    
    # Success criteria:
    # 1. Beats strategy-tag baseline
    # 2. Relative improvement vs champion
    beats_baseline = (
        challenger_metrics['outbound_clicks_ctr'] >= strategy_baseline['outbound_ctr_median']
    )
    
    significant_improvement = (
        ctr_improvement > 0.10 or  # 10% CTR improvement
        conversion_improvement > 0.20  # 20% conversion improvement
    )
    
    # Rollback criteria:
    # CTR drops >15% vs champion
    performance_degradation = ctr_improvement < -0.15
    
    # Determine winner
    if performance_degradation:
        winner = 'champion'
        recommendation = 'rollback'
        confidence = 0.9
    elif beats_baseline and significant_improvement:
        winner = 'challenger'
        recommendation = 'keep_challenger'
        confidence = 0.85
    elif beats_baseline:
        winner = 'challenger'
        recommendation = 'keep_challenger'
        confidence = 0.65
    else:
        winner = 'champion'
        recommendation = 'insufficient_data' if challenger_metrics['outbound_clicks'] < FeedbackLoopConfig.MIN_OUTBOUND_CLICKS_FOR_SIGNAL else 'rollback'
        confidence = 0.5
    
    evaluation = {
        'winner': winner,
        'confidence': confidence,
        'recommendation': recommendation,
        
        'metrics_comparison': {
            'champion': {
                'outbound_ctr': champion_metrics['outbound_clicks_ctr'],
                'cpc': champion_metrics['cpc'],
                'conversions': champion_metrics['conversions'],
                'spend': champion_metrics['spend']
            },
            'challenger': {
                'outbound_ctr': challenger_metrics['outbound_clicks_ctr'],
                'cpc': challenger_metrics['cpc'],
                'conversions': challenger_metrics['conversions'],
                'spend': challenger_metrics['spend']
            },
            'improvements': {
                'ctr_relative': ctr_improvement,
                'cpc_relative': cpc_improvement,
                'conversions_relative': conversion_improvement
            }
        },
        
        'baseline_comparison': {
            'strategy_median_ctr': strategy_baseline['outbound_ctr_median'],
            'beats_baseline': beats_baseline
        }
    }
    
    # Store evaluation
    await db.save_version_evaluation(product_id, evaluation)
    
    # Auto-flag rollback if needed
    if recommendation == 'rollback':
        await flag_rollback_recommended(product_id, challenger_version_id, evaluation)
    
    logger.info(f"Evaluation complete for {product_id}: {winner} wins (confidence: {confidence:.0%})")
    
    return evaluation


async def flag_rollback_recommended(
    product_id: str,
    version_id: str,
    evaluation: Dict[str, Any]
):
    """
    Auto-flag rollback when challenger underperforms
    
    V1: Generates alert for human review
    """
    await db.execute("""
        INSERT INTO refinement_alerts (
            alert_id, product_id, alert_type, severity, message, context
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        f"rollback_{product_id}_{datetime.now().timestamp()}",
        product_id,
        'ROLLBACK_RECOMMENDED',
        'HIGH',
        f"Challenger version {version_id} underperformed champion by {abs(evaluation['metrics_comparison']['improvements']['ctr_relative']):.1%}",
        json.dumps(evaluation)
    ))
    
    logger.warning(f"⚠️ Rollback recommended for {product_id} version {version_id}")
```

### 8.9 Strategy-Tag Playbook (Cross-Campaign Learning)

```python
async def update_strategy_playbook(
    strategy_tag: str,
    evaluation: Dict[str, Any],
    product_context: Dict[str, Any]
):
    """
    Learn patterns across campaigns for strategy_tag
    
    CRITICAL: Aggregates successful patterns for future use
    """
    if evaluation['winner'] != 'challenger' or evaluation['confidence'] < 0.7:
        return  # Only learn from confident wins
    
    # Extract pattern
    variable_changed = product_context.get('variable_changed')
    improvement = evaluation['metrics_comparison']['improvements']['ctr_relative']
    
    pattern = {
        'pattern_id': f"{strategy_tag}_{variable_changed}_{datetime.now().timestamp()}",
        'strategy_tag': strategy_tag,
        'variable': variable_changed,
        'pattern': f"{variable_changed} optimization",
        'impact': f"+{improvement:.1%} CTR improvement",
        'confidence': evaluation['confidence'],
        'sample_size': 1,  # V1: Increment with more successes
        'created_at': datetime.now().isoformat(),
        
        # Context
        'example_change': product_context.get('change_summary'),
        'metrics': {
            'ctr_lift': improvement,
            'baseline_ctr': evaluation['metrics_comparison']['champion']['outbound_ctr'],
            'final_ctr': evaluation['metrics_comparison']['challenger']['outbound_ctr']
        }
    }
    
    # Store pattern
    await db.execute("""
        INSERT INTO strategy_playbooks (
            pattern_id, strategy_tag, variable, pattern, impact,
            confidence, sample_size, example_change, metrics
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pattern['pattern_id'],
        pattern['strategy_tag'],
        pattern['variable'],
        pattern['pattern'],
        pattern['impact'],
        pattern['confidence'],
        pattern['sample_size'],
        pattern['example_change'],
        json.dumps(pattern['metrics'])
    ))
    
    logger.info(f"✓ Added pattern to {strategy_tag} playbook: {pattern['pattern']}")
```

### 8.10 Human Approval Workflow

**CRITICAL: Same Low-Friction Mechanism as SEO Staging**

```python
async def queue_refinement_for_approval(
    product_id: str,
    champion: Dict[str, Any],
    challenger: Dict[str, Any],
    context: Dict[str, Any]
) -> str:
    """
    Queue refinement proposal for human approval
    
    Uses Google Sheets staging layer (Section 4)
    """
    approval_id = f"refinement_{product_id}_{datetime.now().timestamp()}"
    
    # Prepare approval record
    approval_record = {
        'approval_id': approval_id,
        'product_id': product_id,
        'product_handle': context['product_handle'],
        'strategy_tag': context['strategy_tag'],
        
        # Versions
        'champion_version': champion.get('version_id'),
        'challenger_version': 'proposed',
        
        # Changes
        'variable_changed': challenger['variable_changed'],
        'change_summary': challenger['change_summary'],
        
        # Champion SEO
        'current_title': champion['title'],
        'current_meta_description': champion['meta_description'],
        
        # Challenger SEO
        'proposed_title': challenger.get('challenger_title', champion['title']),
        'proposed_meta_description': challenger.get('challenger_meta_description', champion['meta_description']),
        
        # Trigger context
        'trigger_metrics': {
            'outbound_ctr': context['metrics']['outbound_clicks_ctr'],
            'cpc': context['metrics']['cpc'],
            'spend': context['metrics']['spend'],
            'conversions': context['metrics']['conversions']
        },
        'funnel_stage': context['funnel_stage'],
        'hypothesis': challenger['hypothesis'],
        
        # Status
        'status': 'PENDING',
        'created_at': datetime.now().isoformat()
    }
    
    # Write to approval queue (Google Sheets or database)
    await approval_queue.add(approval_record)
    
    logger.info(f"Queued refinement {approval_id} for approval")
    
    return approval_id


async def process_approval_response(approval_id: str, decision: str, user_id: str):
    """
    Process human approval decision
    
    Args:
        decision: 'APPROVE' | 'REJECT' | 'DEFER'
    """
    approval = await approval_queue.get(approval_id)
    
    if decision == 'APPROVE':
        # Apply challenger version
        await apply_refinement(
            approval['product_id'],
            approval['challenger_version'],
            approved_by=user_id
        )
        
        # Flag ads for refresh
        await flag_ads_for_refresh(
            approval['product_id'],
            approval['challenger_version']
        )
        
        # Set cooldown
        await set_product_cooldown(approval['product_id'], days=7)
        
        logger.info(f"✓ Applied refinement {approval_id} (approved by {user_id})")
    
    elif decision == 'REJECT':
        # Log rejection
        await db.execute("""
            UPDATE refinement_proposals
            SET status = 'REJECTED', reviewed_by = ?, reviewed_at = ?
            WHERE approval_id = ?
        """, (user_id, datetime.now().isoformat(), approval_id))
        
        logger.info(f"Rejected refinement {approval_id} (by {user_id})")
    
    else:  # DEFER
        # Keep in queue
        logger.info(f"Deferred refinement {approval_id} (by {user_id})")
```

### 8.11 Daily Feedback Loop Job

```python
import schedule

async def daily_feedback_loop_job():
    """
    Daily feedback loop analysis
    
    CRITICAL: Post-settlement + cooldown-aware
    """
    logger.info("=" * 60)
    logger.info("FEEDBACK LOOP ANALYSIS STARTED")
    logger.info("=" * 60)
    
    try:
        # Get all active strategy_tags
        strategy_tags = await db.get_active_strategy_tags()
        
        total_candidates = 0
        total_queued = 0
        
        for strategy_tag in strategy_tags:
            logger.info(f"Analyzing strategy: {strategy_tag}")
            
            # Select candidates (deterministic scoring)
            candidates = await select_refinement_candidates(
                strategy_tag,
                max_candidates=3,
                min_spend=50.0,
                min_impressions=1000
            )
            
            total_candidates += len(candidates)
            
            for candidate in candidates:
                # Diagnose funnel stage
                funnel_stage = ActionRouter().diagnose_funnel_stage(
                    candidate,
                    site_metrics=await get_shopify_site_metrics(candidate['product_id'])
                )
                
                # Get action plan
                action_plan = ActionRouter().get_action_plan(funnel_stage, candidate)
                
                # Skip if insufficient data
                if action_plan['primary_agent'] is None:
                    logger.info(f"  Skipping {candidate['product_handle']}: insufficient data")
                    continue
                
                # Build refinement context
                context = await build_refinement_context(candidate, funnel_stage, action_plan)
                
                # Generate challenger (if SEO-driven)
                if action_plan['primary_agent'] == 'seo':
                    challenger = await generate_challenger_seo(context)
                    
                    if challenger:
                        # Queue for approval
                        await queue_refinement_for_approval(
                            candidate['product_id'],
                            champion=context['current_seo'],
                            challenger=challenger,
                            context=context
                        )
                        
                        total_queued += 1
                        logger.info(f"  ✓ Queued {candidate['product_handle']} for refinement")
                
                # Note: Ads Agent refinements handled separately
        
        logger.info(f"Analysis complete: {total_candidates} candidates, {total_queued} queued for approval")
        
        # Also evaluate any active challenger tests
        await evaluate_active_tests()
        
        logger.info("=" * 60)
        logger.info("FEEDBACK LOOP ANALYSIS COMPLETED")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"Feedback loop failed: {e}")
        await send_alert({
            'type': 'FEEDBACK_LOOP_FAILURE',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })


async def evaluate_active_tests():
    """Evaluate any products in active champion vs challenger tests"""
    active_tests = await db.get_active_version_tests()
    
    for test in active_tests:
        # Check if evaluation window complete (14 days total)
        if test['days_active'] >= 14:
            evaluation = await evaluate_challenger_performance(
                test['product_id'],
                test['champion_version_id'],
                test['challenger_version_id']
            )
            
            logger.info(f"Test evaluation: {test['product_id']} - {evaluation['recommendation']}")


# Schedule job (runs daily at 8 AM after metrics settle)
schedule.every().day.at("08:00").do(lambda: asyncio.create_task(daily_feedback_loop_job()))
```

### 8.12 Configuration & Constraints

```python
class FeedbackLoopConfig:
    # Candidate selection
    MAX_CANDIDATES_PER_STRATEGY: int = 3
    MIN_SPEND_FOR_REFINEMENT: float = 50.0
    MIN_IMPRESSIONS_FOR_REFINEMENT: int = 1000
    MIN_OUTBOUND_CLICKS_FOR_SIGNAL: int = 20
    
    # Iteration control
    MAX_ITERATIONS_PER_PRODUCT: int = 3
    COOLDOWN_DAYS: int = 7
    MAX_PRODUCTS_PER_DAY: int = 10  # Hard cap
    
    # Performance thresholds
    LOW_OUTBOUND_CTR_THRESHOLD: float = 0.005  # 0.5%
    HIGH_CPC_THRESHOLD: float = 2.00  # $2.00
    
    # Success criteria
    MIN_CTR_IMPROVEMENT_PCT: float = 0.10  # 10%
    MIN_CONVERSION_IMPROVEMENT_PCT: float = 0.20  # 20%
    ROLLBACK_CTR_THRESHOLD: float = -0.15  # -15%
    
    # Testing windows
    CHAMPION_EVALUATION_DAYS: int = 7
    CHALLENGER_EVALUATION_DAYS: int = 7
    SETTLEMENT_DELAY_DAYS: int = 4  # Wait for metrics to settle
    
    # Enrichment
    REVIEW_COUNT_LIMIT: int = 5
    REVIEW_SORT: str = 'most_helpful'
    
    # Playbook
    PLAYBOOK_MIN_CONFIDENCE: float = 0.7
    PLAYBOOK_MIN_SAMPLE_SIZE: int = 3  # V2: Require 3+ successes
    
    # Approval
    APPROVAL_TIMEOUT_DAYS: int = 7  # Auto-expire stale approvals
```

---

**Summary of Critical Features:**
1. ✓ Automated alerts with human approval (B)
2. ✓ Configurable metric matrix (D)
3. ✓ Metric-to-Action routing (funnel stage diagnosis)
4. ✓ Champion vs Challenger (single variable, hypothesis-driven)
5. ✓ Top-K worst product selection (deterministic scoring)
6. ✓ Sequential testing (7 days each, settlement-aware)
7. ✓ Version control with rollback (seo_versions table)
8. ✓ Ad creative refresh flagging (format-aware, stale ad risk mitigation)
9. ✓ Rich context (metrics + SEO + ads + reviews when available)
10. ✓ Strategy-tag playbook (cross-campaign learning)
11. ✓ Daily analysis with cooldown enforcement
12. ✓ Success criteria (beats baseline + relative lift)
13. ✓ Product reviews enrichment (V2: requires review app connector)
14. ✓ Rollback criteria (auto-flag <-15% CTR)
15. ✓ Human approval workflow
16. ✓ Experiment registry (prevents overlapping tests)

**V1 Guardrails:**
- Max 10 products refined/day (prevents runaway)
- Per-product cooldown (7 days minimum, enforced in selector)
- Max iterations per product (3, enforced in selector)
- Pending approval check (no duplicate proposals)
- Settlement-aware (4-day buffer, stable windows only)
- Single variable changes only (no multi-variant)
- Human approval required (no auto-deploy)
- Rollback support (full version history)
- Format-aware creative refresh (manual fallback for restricted formats)

**Critical Risk Mitigations:**
- Stale ad prevention (SEO changes flag ads, format-aware execution)
- Metric-to-Action matrix (routes to correct layer using V1-available data)
- Champion methodology (avoids variant explosion)
- Deterministic selection (no random churn)
- Strategy-tag learning (cross-campaign patterns)
- Settlement buffer (decisions on stable data only)

**V1 Data Dependencies (Verified):**
- ✓ outbound_clicks, outbound_ctr (Meta Insights)
- ✓ spend, cpc (Meta Insights)
- ✓ attributed_orders (Shopify UTM waterfall, Section 7)
- ✗ site_metrics (bounce_rate, sessions) - Optional V2/GA4
- ✗ product_reviews - Requires third-party app connector

### 8.13 n8n Cutover Notes (Demo → Live)

**Problem:** n8n workflows retain demo credentials unless explicitly swapped.

**Credential ID Swap Checklist:**

| Workflow | Credential Type | Demo ID | Live ID | Swapped |
|----------|-----------------|---------|---------|---------|
| SEO Sweep | Shopify Admin | `N8N_CREDENTIAL_ID_SHOPIFY_DEMO` | `N8N_CREDENTIAL_ID_SHOPIFY_LIVE` | [ ] |
| Ad Campaign | Meta Ads | `N8N_CREDENTIAL_ID_META_DEMO` | `N8N_CREDENTIAL_ID_META_LIVE` | [ ] |
| Webhook Receiver | Shopify Webhook | Demo endpoint | Live endpoint | [ ] |

**Swap Procedure:**
1. Open each workflow in n8n editor
2. Click each Shopify/Meta node
3. Change credential dropdown from Demo → Live
4. Save workflow
5. Re-deploy/activate webhooks pointing to correct public endpoint
6. Execute test run and verify execution log shows live credential ID

**Post-Swap Verification:**
- [ ] Execution log entry confirms LIVE credential used
- [ ] Webhook URL matches production endpoint
- [ ] Test payload successfully processes against live store

---

## 9. Error Handling Matrix

**Purpose:** Define error taxonomy, recovery patterns, and escalation paths for all system components. Ensures graceful degradation and prevents cascading failures.

### 9.1 Error Taxonomy

| Component | Error Type | Severity | Recovery Action | Escalation |
|-----------|-----------|----------|-----------------|------------|
| **Shopify API** | Rate limit (429) | MEDIUM | Backoff 60s, retry 3x | Alert if >3 failures/hour |
| **Shopify API** | Bulk op timeout | HIGH | Poll by GID, extend timeout | Alert + manual review |
| **Shopify API** | Bulk op high failure rate | ERROR | HALT next batch, require intervention | Alert + global pause |
| **Shopify API** | GraphQL validation | HIGH | Log payload, skip product | Dead-letter queue |
| **Shopify API** | Auth failure (401/403) | CRITICAL | Halt all ops | Immediate alert |
| **Meta API** | Rate limit (80004) | MEDIUM | Backoff per header, retry | Alert if sustained >15min |
| **Meta API** | Targeting validation (v22+) | HIGH | Skip ad set, log context | Dead-letter + alert |
| **Meta API** | Creative format rejected | MEDIUM | Flag for manual creative | Human review queue |
| **Meta API** | Auth/permission error | CRITICAL | Halt campaign ops | Immediate alert |
| **Meta API** | Policy/quality flag (368) | CRITICAL | HARD STOP all ad ops, preserve payload | Immediate alert + no retry |
| **Metrics** | Data integrity low (unsettled) | ERROR | BLOCK feedback loop, reschedule | Alert + defer decisions |
| **OpenAI API** | Rate limit (429) | MEDIUM | Exponential backoff | Alert if batch delayed >2h |
| **OpenAI API** | Batch overlap/limit | HIGH | Skip batch, queue next cycle | Alert + registry check |
| **OpenAI API** | Invalid response (parse fail) | MEDIUM | Retry 1x, then skip product | Dead-letter queue |
| **OpenAI API** | Content filter triggered | LOW | Skip product, log reason | Review queue |
| **Config** | YAML parse error | CRITICAL | Halt engine startup | Immediate alert |
| **Config** | Safety violation | CRITICAL | Block request, return error | Alert + audit log |
| **Database** | SQLite lock timeout | MEDIUM | Retry 3x with backoff | Alert if persistent |
| **Database** | Constraint violation | HIGH | Log + skip record | Dead-letter queue |
| **Network** | Connection timeout | MEDIUM | Retry with backoff | Alert if >5 failures |
| **Network** | DNS resolution failure | HIGH | Retry after 30s | Alert if persistent |

### 9.2 Circuit Breaker Pattern

**Purpose:** Prevent cascading failures by temporarily blocking requests to failing services.

```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for external API calls
    
    States:
    - CLOSED: Normal operation, failures counted
    - OPEN: All requests blocked, wait for reset
    - HALF_OPEN: Allow single test request
    
    Thresholds tuned per-service (see 9.2.1)
    """
    
    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    async def call(self, func, *args, **kwargs):
        """Execute function through circuit breaker"""
        
        # Check if circuit should transition
        self._check_state_transition()
        
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit open for {self.service_name}. "
                f"Retry after {self._time_until_half_open()}s"
            )
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitOpenError(f"Circuit half-open limit reached for {self.service_name}")
            self.half_open_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _check_state_transition(self):
        """Check if circuit should transition states"""
        if self.state == CircuitState.OPEN:
            if self._time_until_half_open() <= 0:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"Circuit {self.service_name}: OPEN → HALF_OPEN")
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info(f"Circuit {self.service_name}: HALF_OPEN → CLOSED (recovered)")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset on success
    
    def _on_failure(self, error: Exception):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(f"Circuit {self.service_name}: failure {self.failure_count}/{self.failure_threshold}")
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.service_name}: HALF_OPEN → OPEN (recovery failed)")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit {self.service_name}: CLOSED → OPEN (threshold reached)")
            
            # Send alert
            asyncio.create_task(send_circuit_open_alert(self.service_name, error))
    
    def _time_until_half_open(self) -> float:
        """Seconds until circuit transitions to half-open"""
        if not self.last_failure_time:
            return 0
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return max(0, self.recovery_timeout - elapsed)
    
    def force_reset(self):
        """Manual reset (for admin intervention)"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        logger.info(f"Circuit {self.service_name}: FORCE RESET → CLOSED")


class CircuitOpenError(Exception):
    """Raised when circuit is open"""
    pass
```

#### 9.2.1 Service-Specific Thresholds

```python
CIRCUIT_BREAKER_CONFIG = {
    'shopify_graphql': {
        'failure_threshold': 5,
        'recovery_timeout': 60,  # 1 minute
        'half_open_max_calls': 2
    },
    'shopify_bulk_ops': {
        'failure_threshold': 3,
        'recovery_timeout': 300,  # 5 minutes (bulk ops are slow)
        'half_open_max_calls': 1
    },
    'meta_ads': {
        'failure_threshold': 5,
        'recovery_timeout': 120,  # 2 minutes
        'half_open_max_calls': 2
    },
    'meta_insights': {
        'failure_threshold': 3,
        'recovery_timeout': 180,  # 3 minutes (insights can lag)
        'half_open_max_calls': 1
    },
    'openai': {
        'failure_threshold': 3,
        'recovery_timeout': 60,
        'half_open_max_calls': 1
    }
}

# Initialize breakers
circuit_breakers: Dict[str, CircuitBreaker] = {
    name: CircuitBreaker(name, **config)
    for name, config in CIRCUIT_BREAKER_CONFIG.items()
}
```

### 9.3 Retry Matrix (Per-API)

```python
from functools import wraps
import asyncio
import random

class RetryConfig:
    """Retry configuration per API"""
    
    SHOPIFY = {
        'max_attempts': 3,
        'base_delay': 2.0,
        'max_delay': 60.0,
        'exponential_base': 2,
        'jitter': True,
        'retryable_codes': [429, 500, 502, 503, 504]
    }
    
    META = {
        'max_attempts': 3,
        'base_delay': 5.0,
        'max_delay': 120.0,
        'exponential_base': 2,
        'jitter': True,
        'retryable_codes': [1, 2, 4, 17, 80004],  # Meta error codes
        'use_throttle_header': True  # x-fb-ads-insights-throttle
    }
    
    OPENAI = {
        'max_attempts': 3,
        'base_delay': 1.0,
        'max_delay': 30.0,
        'exponential_base': 2,
        'jitter': True,
        'retryable_codes': [429, 500, 502, 503]
    }


def with_retry(config: dict):
    """
    Retry decorator with exponential backoff
    
    Usage:
        @with_retry(RetryConfig.SHOPIFY)
        async def call_shopify(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config['max_attempts']):
                try:
                    return await func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    error_code = extract_error_code(e)
                    
                    # Check if retryable
                    if error_code not in config['retryable_codes']:
                        raise  # Non-retryable, fail immediately
                    
                    if attempt == config['max_attempts'] - 1:
                        raise  # Last attempt, propagate error
                    
                    # Calculate delay
                    delay = min(
                        config['base_delay'] * (config['exponential_base'] ** attempt),
                        config['max_delay']
                    )
                    
                    # Add jitter
                    if config.get('jitter'):
                        delay = delay * (0.5 + random.random())
                    
                    # Check Meta throttle header
                    if config.get('use_throttle_header'):
                        header_delay = extract_meta_throttle_delay(e)
                        if header_delay:
                            delay = max(delay, header_delay)
                    
                    logger.warning(
                        f"Retry {attempt + 1}/{config['max_attempts']} for {func.__name__} "
                        f"after {delay:.1f}s (error: {error_code})"
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


def extract_error_code(exception: Exception) -> int:
    """Extract error code from various exception types"""
    if hasattr(exception, 'status_code'):
        return exception.status_code
    if hasattr(exception, 'error_code'):
        return exception.error_code
    if hasattr(exception, 'response'):
        return exception.response.status_code
    return 0


def extract_meta_throttle_delay(exception: Exception) -> Optional[float]:
    """Extract delay from Meta x-fb-ads-insights-throttle header"""
    try:
        if hasattr(exception, 'response') and exception.response:
            throttle = exception.response.headers.get('x-fb-ads-insights-throttle')
            if throttle:
                # Format: "{'app_id_util_pct': 0.00, 'acc_id_util_pct': 95.00}"
                import ast
                data = ast.literal_eval(throttle)
                if data.get('acc_id_util_pct', 0) > 90:
                    return 60.0  # Wait 1 minute if near limit
    except:
        pass
    return None
```

### 9.4 Dead-Letter Queue

**Purpose:** Capture failed operations for manual review and replay.

```python
# Database schema
CREATE TABLE dead_letter_queue (
    dlq_id TEXT PRIMARY KEY,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Source context
    component TEXT NOT NULL,  -- 'shopify', 'meta', 'openai', 'seo_engine'
    operation TEXT NOT NULL,  -- 'bulk_update', 'ad_create', 'seo_optimize'
    entity_id TEXT,           -- product_id, campaign_id, etc.
    entity_type TEXT,         -- 'product', 'campaign', 'ad'
    
    -- Error details
    error_code TEXT,
    error_message TEXT,
    error_context TEXT,  -- JSON: full error response
    
    -- Original payload
    request_payload TEXT,  -- JSON: original request for replay
    
    -- Resolution
    status TEXT DEFAULT 'PENDING',  -- PENDING | RESOLVED | SKIPPED | REPLAYED
    resolved_at TEXT,
    resolved_by TEXT,
    resolution_notes TEXT,
    
    -- Retry tracking
    retry_count INTEGER DEFAULT 0,
    last_retry_at TEXT,
    next_retry_at TEXT
);

CREATE INDEX idx_dlq_status ON dead_letter_queue(status);
CREATE INDEX idx_dlq_component ON dead_letter_queue(component);
CREATE INDEX idx_dlq_created ON dead_letter_queue(created_at);


async def add_to_dead_letter_queue(
    component: str,
    operation: str,
    entity_id: str,
    entity_type: str,
    error: Exception,
    request_payload: dict
) -> str:
    """
    Add failed operation to dead-letter queue
    
    Returns: dlq_id for tracking
    """
    dlq_id = f"dlq_{component}_{datetime.now().timestamp()}"
    
    await db.execute("""
        INSERT INTO dead_letter_queue (
            dlq_id, component, operation, entity_id, entity_type,
            error_code, error_message, error_context, request_payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dlq_id,
        component,
        operation,
        entity_id,
        entity_type,
        str(extract_error_code(error)),
        str(error),
        json.dumps(getattr(error, 'response', None)),
        json.dumps(request_payload)
    ))
    
    logger.error(f"Added to DLQ: {dlq_id} ({component}/{operation}/{entity_id})")
    
    # Alert if queue growing
    pending_count = await db.get_dlq_pending_count()
    if pending_count > 10:
        await send_alert({
            'type': 'DLQ_GROWTH',
            'severity': 'WARNING',
            'message': f'Dead-letter queue has {pending_count} pending items',
            'dlq_id': dlq_id
        })
    
    return dlq_id


async def replay_dead_letter(dlq_id: str) -> bool:
    """
    Replay failed operation from dead-letter queue
    
    Returns: True if replay succeeded
    """
    record = await db.get_dlq_record(dlq_id)
    
    if not record or record['status'] != 'PENDING':
        return False
    
    try:
        # Route to appropriate handler
        if record['component'] == 'shopify':
            await replay_shopify_operation(record)
        elif record['component'] == 'meta':
            await replay_meta_operation(record)
        elif record['component'] == 'openai':
            await replay_openai_operation(record)
        elif record['component'] == 'seo_engine':
            await replay_seo_operation(record)
        
        # Mark resolved
        await db.execute("""
            UPDATE dead_letter_queue
            SET status = 'REPLAYED', resolved_at = ?, retry_count = retry_count + 1
            WHERE dlq_id = ?
        """, (datetime.now().isoformat(), dlq_id))
        
        logger.info(f"✓ Replayed DLQ item: {dlq_id}")
        return True
    
    except Exception as e:
        # Update retry count
        await db.execute("""
            UPDATE dead_letter_queue
            SET retry_count = retry_count + 1, 
                last_retry_at = ?,
                error_message = ?
            WHERE dlq_id = ?
        """, (datetime.now().isoformat(), str(e), dlq_id))
        
        logger.error(f"Replay failed for {dlq_id}: {e}")
        return False
```

### 9.5 Alert Routing

```python
from enum import Enum
from typing import List

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    LOG = "log"           # Always
    SLACK = "slack"       # WARNING+
    EMAIL = "email"       # ERROR+
    SMS = "sms"           # CRITICAL only


ALERT_ROUTING = {
    AlertSeverity.INFO: [AlertChannel.LOG],
    AlertSeverity.WARNING: [AlertChannel.LOG, AlertChannel.SLACK],
    AlertSeverity.ERROR: [AlertChannel.LOG, AlertChannel.SLACK, AlertChannel.EMAIL],
    AlertSeverity.CRITICAL: [AlertChannel.LOG, AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.SMS]
}


async def send_alert(alert: dict):
    """
    Route alert to appropriate channels based on severity
    
    Args:
        alert: {
            'type': str,
            'severity': str,
            'message': str,
            'context': dict (optional)
        }
    """
    severity = AlertSeverity(alert.get('severity', 'info'))
    channels = ALERT_ROUTING[severity]
    
    # Always log
    log_level = getattr(logger, severity.value, logger.info)
    log_level(f"ALERT [{alert['type']}]: {alert['message']}")
    
    # Route to additional channels
    for channel in channels:
        if channel == AlertChannel.SLACK:
            await send_slack_alert(alert)
        elif channel == AlertChannel.EMAIL:
            await send_email_alert(alert)
        elif channel == AlertChannel.SMS:
            await send_sms_alert(alert)


# Alert type → Severity mapping
ALERT_SEVERITY_MAP = {
    # Critical (immediate action required)
    'AUTH_FAILURE': AlertSeverity.CRITICAL,
    'CONFIG_BLOCKED': AlertSeverity.CRITICAL,
    'CIRCUIT_OPEN': AlertSeverity.CRITICAL,
    'DATABASE_CORRUPTION': AlertSeverity.CRITICAL,
    'META_POLICY_FLAG': AlertSeverity.CRITICAL,  # Error 368 - no retry
    'GLOBAL_PAUSE_SET': AlertSeverity.CRITICAL,
    
    # Error (action required)
    'BULK_OP_FAILED': AlertSeverity.ERROR,
    'BULK_FAILURE_RATE_HIGH': AlertSeverity.ERROR,  # Row-level failure threshold
    'DATA_INTEGRITY_BLOCKED': AlertSeverity.ERROR,  # Unsettled metrics
    'CAMPAIGN_CREATE_FAILED': AlertSeverity.ERROR,
    'METRICS_COLLECTION_FAILED': AlertSeverity.ERROR,
    'FEEDBACK_LOOP_FAILURE': AlertSeverity.ERROR,
    'DLQ_GROWTH': AlertSeverity.ERROR,
    
    # Warning (attention needed)
    'RATE_LIMIT_HIT': AlertSeverity.WARNING,
    'SETTLEMENT_DELAY': AlertSeverity.WARNING,
    'TARGETING_VALIDATION': AlertSeverity.WARNING,
    'CREATIVE_FORMAT_REJECTED': AlertSeverity.WARNING,
    'BATCH_OVERLAP': AlertSeverity.WARNING,
    'ROLLBACK_RECOMMENDED': AlertSeverity.WARNING,
    
    # Info (monitoring)
    'BATCH_COMPLETE': AlertSeverity.INFO,
    'CAMPAIGN_CREATED': AlertSeverity.INFO,
    'REFINEMENT_APPROVED': AlertSeverity.INFO,
    'GLOBAL_PAUSE_CLEARED': AlertSeverity.INFO
}
```

### 9.6 Risk-Specific Handlers

**RISK-D1: Data Integrity Gate (Feedback Loop)**
```python
async def check_data_integrity_for_feedback_loop(
    last_n_days: int = 3,
    min_settled_pct: float = 0.95
) -> dict:
    """
    CRITICAL: Block feedback loop if metrics are not decision-grade
    
    Problem: Settlement delay config doesn't prevent decisions on incomplete data.
    Solution: Explicit coverage check before any underperformer scoring.
    
    Returns:
        {'allowed': bool, 'settled_pct': float, 'reason': str}
    """
    # Calculate expected row count (campaigns × days)
    active_campaigns = await db.get_active_campaign_count()
    expected_rows = active_campaigns * last_n_days
    
    if expected_rows == 0:
        return {'allowed': False, 'settled_pct': 0, 'reason': 'No active campaigns'}
    
    # Count settled rows
    settled_rows = await db.execute("""
        SELECT COUNT(*) as count
        FROM metrics
        WHERE date >= date('now', ? || ' days')
          AND is_settled = TRUE
    """, (f'-{last_n_days}',))
    
    settled_count = settled_rows[0]['count']
    settled_pct = settled_count / expected_rows
    
    if settled_pct < min_settled_pct:
        # BLOCK feedback loop
        await send_alert({
            'type': 'DATA_INTEGRITY_BLOCKED',
            'severity': 'error',
            'message': f'Feedback loop blocked: only {settled_pct:.1%} data settled (need {min_settled_pct:.0%})',
            'context': {
                'settled_rows': settled_count,
                'expected_rows': expected_rows,
                'settled_pct': settled_pct
            }
        })
        
        logger.error(
            f"DATA_INTEGRITY_BLOCKED: {settled_pct:.1%} settled < {min_settled_pct:.0%} threshold. "
            f"Feedback loop will NOT run."
        )
        
        return {
            'allowed': False,
            'settled_pct': settled_pct,
            'reason': f'Insufficient settled data ({settled_pct:.1%} < {min_settled_pct:.0%})'
        }
    
    return {
        'allowed': True,
        'settled_pct': settled_pct,
        'reason': None
    }


# Integration point (add to daily_feedback_loop_job):
async def daily_feedback_loop_job():
    # GATE: Check data integrity FIRST
    integrity_check = await check_data_integrity_for_feedback_loop()
    if not integrity_check['allowed']:
        logger.warning(f"Feedback loop skipped: {integrity_check['reason']}")
        return  # Exit without making any decisions
    
    # ... rest of feedback loop logic
```

**RISK-B1: Bulk Failure Rate Breaker**
```python
async def evaluate_bulk_op_failure_rate(
    bulk_operation_gid: str,
    max_failure_rate: float = 0.10,
    min_rows: int = 50
) -> dict:
    """
    CRITICAL: Detect near-total row-level failures in "completed" bulk ops
    
    Problem: Bulk op status=COMPLETED doesn't mean rows succeeded.
    Schema mismatches can cause 100% row failures while job "completes."
    
    Returns:
        {'safe': bool, 'failure_rate': float, 'action': str}
    """
    # Parse bulk op results
    results = await parse_bulk_operation_results(bulk_operation_gid)
    
    total_rows = results['total_count']
    failure_count = results['error_count']
    
    if total_rows < min_rows:
        # Not enough data to evaluate
        return {
            'safe': True,
            'failure_rate': 0,
            'action': 'CONTINUE',
            'reason': f'Below min_rows threshold ({total_rows} < {min_rows})'
        }
    
    failure_rate = failure_count / total_rows
    
    if failure_rate > max_failure_rate:
        # CRITICAL: High failure rate - halt operations
        await send_alert({
            'type': 'BULK_FAILURE_RATE_HIGH',
            'severity': 'error',
            'message': f'Bulk op {bulk_operation_gid}: {failure_rate:.1%} row failures (threshold: {max_failure_rate:.0%})',
            'context': {
                'bulk_operation_gid': bulk_operation_gid,
                'total_rows': total_rows,
                'failure_count': failure_count,
                'failure_rate': failure_rate,
                'sample_errors': results['sample_errors'][:5]  # First 5 for diagnosis
            }
        })
        
        # Set global pause
        await set_global_pause(
            reason=f'Bulk op failure rate {failure_rate:.1%} exceeded threshold',
            set_by='bulk_failure_rate_breaker'
        )
        
        logger.error(
            f"BULK_FAILURE_RATE_HIGH: {failure_rate:.1%} > {max_failure_rate:.0%}. "
            f"Global pause SET. Manual intervention required."
        )
        
        return {
            'safe': False,
            'failure_rate': failure_rate,
            'action': 'GLOBAL_PAUSE',
            'reason': f'Failure rate {failure_rate:.1%} exceeds {max_failure_rate:.0%}'
        }
    
    return {
        'safe': True,
        'failure_rate': failure_rate,
        'action': 'CONTINUE',
        'reason': None
    }
```

**RISK-C1: Shopify Bulk Op Query Drift**
```python
async def safe_poll_bulk_operation(bulk_operation_gid: str) -> dict:
    """
    Poll bulk operation by GID (not currentBulkOperation)
    
    CRITICAL: currentBulkOperation deprecated in newer API versions
    Mitigation: Always query by persisted GID
    """
    # Version-gated query selection
    api_version = config.get('SHOPIFY_API_VERSION', '2025-10')
    
    if api_version >= '2025-01':
        # New API: Query by ID only
        query = f'''
            query {{
                node(id: "{bulk_operation_gid}") {{
                    ... on BulkOperation {{
                        id
                        status
                        errorCode
                        objectCount
                        url
                    }}
                }}
            }}
        '''
    else:
        # Legacy API: Can use currentBulkOperation but prefer ID
        query = f'''
            query {{
                node(id: "{bulk_operation_gid}") {{
                    ... on BulkOperation {{
                        id
                        status
                        errorCode
                        objectCount
                        url
                    }}
                }}
            }}
        '''
    
    return await shopify_graphql.query(query)
```

**RISK-C2: Meta Targeting Validation (v22+)**
```python
V1_SAFE_TARGETING = {
    # V1: No exclusions, broad/interest-only
    'geo_locations': {'countries': ['US']},
    'age_min': 25,
    'age_max': 65,
    'genders': [0],  # All
    
    # V1: Interest-only inclusion (no exclusions)
    'flexible_spec': [{
        'interests': [
            {'id': '6003139266461', 'name': 'Jewelry'},
            {'id': '6003598877404', 'name': 'Gift'}
        ]
    }],
    
    # FORBIDDEN in V1 (v22+ validation failures):
    # - 'exclusions': {...}
    # - 'detailed_targeting_exclusions': {...}
    # - advantage_plus_creative flags (unless exact SDK fields verified)
}

def validate_targeting_v1_safe(targeting: dict) -> bool:
    """
    Validate targeting is V1-safe (no exclusions, no risky flags)
    
    Returns False if targeting would fail v22+ validation
    """
    forbidden_keys = [
        'exclusions',
        'detailed_targeting_exclusions',
        'flexible_exclusions'
    ]
    
    for key in forbidden_keys:
        if key in targeting:
            logger.error(f"V1 VIOLATION: Targeting contains forbidden key '{key}'")
            return False
    
    return True
```

**RISK-C3: OpenAI Batch Overlap**
```python
class BatchRegistry:
    """
    Track active batches to prevent overlap
    
    CRITICAL: Daily schedules can overlap if batches run long
    """
    
    async def can_submit_batch(self, strategy_tag: str) -> bool:
        """Check if new batch can be submitted"""
        active = await db.get_active_batch(strategy_tag)
        
        if active:
            logger.warning(
                f"Batch overlap blocked for {strategy_tag}: "
                f"batch {active['batch_id']} still {active['status']}"
            )
            return False
        
        # Also check org-level enqueued limit
        org_batches = await db.get_all_active_batches()
        if len(org_batches) >= MAX_CONCURRENT_BATCHES:
            logger.warning(f"Org batch limit reached ({len(org_batches)}/{MAX_CONCURRENT_BATCHES})")
            return False
        
        return True
    
    async def register_batch(self, strategy_tag: str, batch_id: str):
        """Register new batch"""
        await db.execute("""
            INSERT INTO batch_registry (strategy_tag, batch_id, status, created_at)
            VALUES (?, ?, 'in_progress', ?)
        """, (strategy_tag, batch_id, datetime.now().isoformat()))
    
    async def complete_batch(self, batch_id: str, status: str):
        """Mark batch complete"""
        await db.execute("""
            UPDATE batch_registry
            SET status = ?, completed_at = ?
            WHERE batch_id = ?
        """, (status, datetime.now().isoformat(), batch_id))


# Schema
CREATE TABLE batch_registry (
    batch_id TEXT PRIMARY KEY,
    strategy_tag TEXT NOT NULL,
    status TEXT DEFAULT 'in_progress',  -- in_progress | completed | failed | cancelled
    created_at TEXT,
    completed_at TEXT,
    error_message TEXT
);

CREATE INDEX idx_batch_strategy ON batch_registry(strategy_tag);
CREATE INDEX idx_batch_status ON batch_registry(status);
```

**RISK-C5: Link Preview Metadata Override**
```python
async def check_creative_editability(ad_format: str, uses_link_preview: bool) -> dict:
    """
    Check if creative fields are editable
    
    CRITICAL: Meta removed/limited link preview override in some flows
    """
    if uses_link_preview:
        return {
            'editable': False,
            'reason': 'LINK_PREVIEW_RESTRICTED',
            'recommendation': 'Ensure destination page has correct Open Graph metadata',
            'fallback': 'Manual creative creation required'
        }
    
    if ad_format in ['CAROUSEL', 'COLLECTION', 'INSTANT_EXPERIENCE']:
        return {
            'editable': False,
            'reason': 'FORMAT_RESTRICTED',
            'recommendation': 'Use manual creative workflow',
            'fallback': 'Queue for human review'
        }
    
    return {
        'editable': True,
        'reason': None,
        'recommendation': None,
        'fallback': None
    }
```

### 9.7 Global Pause Mechanism

**Purpose:** Coordinated stop across all agents when critical errors occur.

```python
import redis
import json
from datetime import datetime
from typing import Optional

# Redis key for global pause
GLOBAL_PAUSE_KEY = "system:global_pause"


async def set_global_pause(
    reason: str,
    set_by: str,
    ttl_seconds: Optional[int] = None
) -> bool:
    """
    Set global pause - all agents must stop before next unit of work
    
    Args:
        reason: Why pause is set (e.g., "Bulk op failure rate exceeded")
        set_by: Service/agent ID that triggered pause
        ttl_seconds: Optional auto-expire (None = manual clear required)
    """
    pause_data = {
        'enabled': True,
        'reason': reason,
        'set_by': set_by,
        'set_at': datetime.utcnow().isoformat(),
        'ttl_seconds': ttl_seconds
    }
    
    if ttl_seconds:
        await redis_client.setex(GLOBAL_PAUSE_KEY, ttl_seconds, json.dumps(pause_data))
    else:
        await redis_client.set(GLOBAL_PAUSE_KEY, json.dumps(pause_data))
    
    # Alert
    await send_alert({
        'type': 'GLOBAL_PAUSE_SET',
        'severity': 'critical',
        'message': f'GLOBAL PAUSE activated: {reason}',
        'context': pause_data
    })
    
    logger.critical(f"🛑 GLOBAL PAUSE SET by {set_by}: {reason}")
    return True


async def clear_global_pause(cleared_by: str) -> bool:
    """
    Clear global pause - resume normal operations
    
    Args:
        cleared_by: User/service clearing the pause
    """
    await redis_client.delete(GLOBAL_PAUSE_KEY)
    
    await send_alert({
        'type': 'GLOBAL_PAUSE_CLEARED',
        'severity': 'info',
        'message': f'Global pause cleared by {cleared_by}',
        'context': {'cleared_at': datetime.utcnow().isoformat()}
    })
    
    logger.info(f"✅ GLOBAL PAUSE CLEARED by {cleared_by}")
    return True


async def check_global_pause() -> dict:
    """
    Check if global pause is active
    
    CRITICAL: Every agent MUST call this before starting work
    
    Returns:
        {'paused': bool, 'reason': str, 'set_by': str, 'set_at': str}
    """
    data = await redis_client.get(GLOBAL_PAUSE_KEY)
    
    if not data:
        return {'paused': False, 'reason': None, 'set_by': None, 'set_at': None}
    
    pause_data = json.loads(data)
    
    if pause_data.get('enabled'):
        return {
            'paused': True,
            'reason': pause_data.get('reason'),
            'set_by': pause_data.get('set_by'),
            'set_at': pause_data.get('set_at')
        }
    
    return {'paused': False, 'reason': None, 'set_by': None, 'set_at': None}


def require_not_paused(func):
    """
    Decorator: Block execution if global pause is active
    
    Usage:
        @require_not_paused
        async def run_seo_batch(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        pause_status = await check_global_pause()
        
        if pause_status['paused']:
            logger.warning(
                f"BLOCKED by global pause: {func.__name__}. "
                f"Reason: {pause_status['reason']} (set by {pause_status['set_by']})"
            )
            raise GlobalPauseError(
                f"Operation blocked: {pause_status['reason']}"
            )
        
        return await func(*args, **kwargs)
    
    return wrapper


class GlobalPauseError(Exception):
    """Raised when operation blocked by global pause"""
    pass
```

**Required Integration Points:**

Every agent must check global pause before starting work:

```python
# SEO Engine batch
@require_not_paused
async def run_seo_batch(strategy_tag: str, products: List[dict]):
    ...

# Shopify bulk update
@require_not_paused
async def execute_bulk_update(mutation: str, products: List[dict]):
    ...

# Ad campaign creation
@require_not_paused
async def create_ad_campaign(campaign_config: dict):
    ...

# Feedback loop
@require_not_paused
async def daily_feedback_loop_job():
    ...
```

**Manual Override (Admin Only):**
```python
# CLI or admin endpoint
async def admin_clear_pause(admin_user: str, override_reason: str):
    """Clear pause with audit trail"""
    await clear_global_pause(cleared_by=f"{admin_user}: {override_reason}")
```

### 9.8 Meta Policy Flag Handler

**CRITICAL: Error 368 = Hard Stop, No Retry**

```python
# Meta error codes that require hard stop (no retry)
META_HARD_STOP_CODES = {
    368: 'ACTION_BLOCKED',  # Verified: action blocked / disallowed
    # Additional codes (configurable, add after log verification):
    # 1885316: 'POLICY_VIOLATION',  # Unverified - add if confirmed in logs
    # 123149: 'QUALITY_FLAG',       # Unverified - add if confirmed in logs
}


async def handle_meta_error(error_code: int, error_message: str, context: dict) -> str:
    """
    Handle Meta API error with appropriate action
    
    Returns: 'RETRY' | 'SKIP' | 'HARD_STOP'
    """
    if error_code in META_HARD_STOP_CODES:
        # CRITICAL: Policy/quality flag - do NOT retry
        error_type = META_HARD_STOP_CODES[error_code]
        
        await send_alert({
            'type': 'META_POLICY_FLAG',
            'severity': 'critical',
            'message': f'Meta policy flag ({error_code}): {error_type}. All ad ops halted.',
            'context': {
                'error_code': error_code,
                'error_type': error_type,
                'error_message': error_message,
                'original_context': context
            }
        })
        
        # Preserve evidence
        await db.execute("""
            INSERT INTO meta_policy_events (
                event_id, error_code, error_type, error_message,
                request_context, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"policy_{datetime.now().timestamp()}",
            error_code,
            error_type,
            error_message,
            json.dumps(context),
            datetime.now().isoformat()
        ))
        
        # Set global pause
        await set_global_pause(
            reason=f'Meta policy flag {error_code}: {error_type}',
            set_by='meta_error_handler'
        )
        
        logger.critical(f"🛑 META POLICY FLAG: {error_code} ({error_type}). HARD STOP.")
        
        return 'HARD_STOP'
    
    elif error_code == 80004:
        # Rate limit - retry with backoff
        return 'RETRY'
    
    else:
        # Unknown error - skip this item, continue batch
        return 'SKIP'
```

### 9.9 Configuration

```python
class ErrorHandlingConfig:
    # Circuit breaker
    CIRCUIT_BREAKER_ENABLED: bool = True
    DEFAULT_FAILURE_THRESHOLD: int = 5
    DEFAULT_RECOVERY_TIMEOUT: int = 60
    
    # Retry
    MAX_RETRY_ATTEMPTS: int = 3
    BASE_RETRY_DELAY: float = 2.0
    MAX_RETRY_DELAY: float = 120.0
    
    # Dead-letter queue
    DLQ_ALERT_THRESHOLD: int = 10
    DLQ_AUTO_RETRY_ENABLED: bool = False  # V1: Manual review only
    DLQ_RETENTION_DAYS: int = 30
    
    # Batch registry
    MAX_CONCURRENT_BATCHES: int = 3
    BATCH_TIMEOUT_HOURS: int = 24
    
    # Alerts
    SLACK_WEBHOOK_URL: str = os.getenv('SLACK_WEBHOOK_URL')
    ALERT_EMAIL: str = os.getenv('ALERT_EMAIL')
    SMS_ENABLED: bool = False  # V1: Disabled
    
    # Shopify
    # SUPPORTED API VERSION WINDOW: Shopify supports versions for 12 months.
    # Upgrade required quarterly. Monitor Developer Changelog for deprecations.
    SHOPIFY_API_VERSION: str = '2025-10'  # Current target; plan upgrade to 2026-01
    SHOPIFY_BULK_OP_TIMEOUT: int = 3600  # 1 hour
    
    # Meta
    # Citations: Meta Marketing API error codes documentation
    # - Error 80004: Rate limit exceeded (OAuthException)
    # - Error 368: Policy violation / account restriction
    META_API_VERSION: str = 'v22.0'
    META_THROTTLE_THRESHOLD: float = 90.0  # Pause at 90% utilization
```

---

**Summary of Error Handling:**
1. ✓ Error taxonomy (component × error type → action)
2. ✓ Circuit breaker (per-service thresholds, state machine)
3. ✓ Retry with exponential backoff (per-API config)
4. ✓ Dead-letter queue (manual review + replay)
5. ✓ Alert routing (severity-based channels)
6. ✓ Risk-specific handlers (C1-C5 from Risk Register)
7. ✓ Data integrity gate (blocks feedback loop on unsettled data)
8. ✓ Bulk failure rate breaker (detects row-level failures)
9. ✓ Global pause mechanism (coordinated stop across agents)
10. ✓ Meta policy flag handler (hard stop on error 368)

**V1 Guardrails:**
- DLQ auto-retry disabled (manual review only)
- SMS alerts disabled (Slack + email only)
- Meta exclusions forbidden (v22+ safe)
- Batch overlap prevention (registry check)
- Link preview fallback (manual creative if restricted)
- Global pause required check on all operations
- Data integrity gate before feedback loop decisions
- Bulk failure rate threshold (10%) triggers global pause

**Monitoring Points:**
- Circuit breaker state changes
- DLQ growth (>10 pending)
- Batch overlap attempts
- Rate limit frequency
- Settlement delays
- Data integrity coverage (settled_pct)
- Bulk op failure rates
- Global pause state
- Meta policy flags (error 368)

---

## 10. Testing Strategy

**Purpose:** Define testing approach for each component, mock strategies for external APIs, and validation criteria before production deployment.

### 10.1 Testing Pyramid

```
                    ┌─────────────┐
                    │   E2E (5%)  │  Full flow validation
                    ├─────────────┤
                  ┌─┤Integration  │  API contracts, DB operations
                  │ │   (25%)     │
                ┌─┤ ├─────────────┤
                │ │ │  Unit (70%) │  Business logic, validators, parsers
                └─┴─┴─────────────┘
```

### 10.2 Unit Tests

**Coverage Targets:** 70%+ for core business logic

#### 10.2.1 SEO Engine

```python
# tests/unit/test_sku_decoder.py
import pytest
from src.seo_engine.parsers.sku_decoder import decode_sku

class TestSKUDecoder:
    def test_valid_sku_full_parse(self):
        result = decode_sku("ANK-SS-WISP-TAN-S")
        assert result['parse_success'] == True
        assert result['type'] == "Anklet"
        assert result['material'] == "Sterling Silver"
        assert result['collection'] == "Whispers"
        assert result['gemstone'] == "Tanzanite"
        assert result['size'] == "S"
        assert result['unknown_tokens'] == []
    
    def test_partial_sku(self):
        result = decode_sku("BRAC-GF-GAR")
        assert result['type'] == "Bracelet"
        assert result['material'] == "Gold Filled"
        assert result['gemstone'] == "Garnet"
        assert result['collection'] is None
    
    def test_unknown_tokens_captured(self):
        result = decode_sku("ANK-SS-UNKNOWN-TAN")
        assert "UNKNOWN" in result['unknown_tokens']
        assert result['parse_success'] == True
    
    def test_empty_sku(self):
        result = decode_sku("")
        assert result['parse_success'] == False
    
    def test_invalid_type(self):
        result = decode_sku(None)
        assert result['parse_success'] == False


# tests/unit/test_constraint_guard.py
from src.seo_engine.validators.guard import ConstraintGuard

class TestConstraintGuard:
    def test_title_truncation(self):
        response = {'new_title': 'A' * 100}
        result = ConstraintGuard.enforce(response, {'max_title_length': 70})
        assert len(result['new_title']) <= 70
        assert result['new_title'].endswith('...')
    
    def test_banned_words_removed(self):
        response = {'new_title': 'Cheap Guaranteed Quality Bracelet'}
        result = ConstraintGuard.enforce(response, {'banned_words': ['cheap', 'guaranteed']})
        assert 'cheap' not in result['new_title'].lower()
        assert 'guaranteed' not in result['new_title'].lower()
    
    def test_max_tags_enforced(self):
        response = {'new_tags': ['tag' + str(i) for i in range(20)]}
        result = ConstraintGuard.enforce(response)
        assert len(result['new_tags']) <= 13


# tests/unit/test_config_loader.py
from src.seo_engine.config import ConfigLoader, SafetyViolationError

class TestConfigLoader:
    def test_baseline_only(self, tmp_path):
        baseline = tmp_path / "baseline.yaml"
        baseline.write_text("safety:\n  max_title_length: 70\nengine_defaults:\n  tone: friendly\nhard_limits:\n  max_title_length: 140")
        
        loader = ConfigLoader(baseline_path=str(baseline), overrides_path="nonexistent.yaml")
        config = loader.load_config()
        
        assert config['safety']['max_title_length'] == 70
        assert config['overrides_active'] == False
    
    def test_safety_violation_blocked(self, tmp_path):
        baseline = tmp_path / "baseline.yaml"
        baseline.write_text("safety:\n  max_title_length: 70\nhard_limits:\n  max_title_length: 140")
        
        overrides = tmp_path / "overrides.yaml"
        overrides.write_text("status: active\npreferences:\n  force_title_length: 200")
        
        loader = ConfigLoader(baseline_path=str(baseline), overrides_path=str(overrides))
        
        with pytest.raises(SafetyViolationError):
            loader.load_config()
```

#### 10.2.2 Feedback Loop

```python
# tests/unit/test_action_router.py
from src.feedback_loop.action_router import ActionRouter, FunnelStage

class TestActionRouter:
    def test_low_ctr_routes_to_ads(self):
        router = ActionRouter()
        metrics = {'outbound_clicks_ctr': 0.003, 'cpc': 1.50, 'spend': 100, 'outbound_clicks': 30}
        
        stage = router.diagnose_funnel_stage(metrics)
        assert stage == FunnelStage.TOP_OF_FUNNEL
        
        plan = router.get_action_plan(stage, metrics)
        assert plan['primary_agent'] == 'ads'
    
    def test_high_ctr_low_conversions_routes_to_seo(self):
        router = ActionRouter()
        metrics = {'outbound_clicks_ctr': 0.015, 'cpc': 1.00, 'spend': 100, 'outbound_clicks': 50, 'attributed_orders': 0}
        
        stage = router.diagnose_funnel_stage(metrics)
        assert stage == FunnelStage.MID_FUNNEL
        
        plan = router.get_action_plan(stage, metrics)
        assert plan['primary_agent'] == 'seo'
    
    def test_insufficient_data_blocks_action(self):
        router = ActionRouter()
        metrics = {'outbound_clicks_ctr': 0.01, 'cpc': 1.00, 'spend': 30, 'outbound_clicks': 10}
        
        stage = router.diagnose_funnel_stage(metrics)
        assert stage == FunnelStage.INSUFFICIENT_DATA
        
        plan = router.get_action_plan(stage, metrics)
        assert plan['primary_agent'] is None


# tests/unit/test_candidate_selection.py
class TestCandidateSelection:
    def test_cooldown_enforced(self):
        # Product refined 3 days ago should be skipped
        ...
    
    def test_max_iterations_enforced(self):
        # Product at max iterations should be skipped
        ...
    
    def test_pending_approval_skipped(self):
        # Product with pending approval should be skipped
        ...
    
    def test_z_score_ranking(self):
        # Worst performers (lowest Z-scores) should be selected first
        ...
```

#### 10.2.3 Error Handling

```python
# tests/unit/test_circuit_breaker.py
import pytest
from src.error_handling.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError

class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        breaker = CircuitBreaker('test', failure_threshold=3, recovery_timeout=60)
        
        async def failing_func():
            raise Exception("fail")
        
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_blocks_when_open(self):
        breaker = CircuitBreaker('test', failure_threshold=1, recovery_timeout=60)
        breaker.state = CircuitState.OPEN
        
        with pytest.raises(CircuitOpenError):
            await breaker.call(lambda: None)
    
    @pytest.mark.asyncio
    async def test_recovers_on_success(self):
        breaker = CircuitBreaker('test', failure_threshold=3, recovery_timeout=0)
        breaker.state = CircuitState.HALF_OPEN
        
        async def success_func():
            return "ok"
        
        result = await breaker.call(success_func)
        assert breaker.state == CircuitState.CLOSED


# tests/unit/test_data_integrity_gate.py
class TestDataIntegrityGate:
    @pytest.mark.asyncio
    async def test_blocks_on_low_settlement(self, mock_db):
        mock_db.get_active_campaign_count.return_value = 10
        mock_db.execute.return_value = [{'count': 20}]  # Only 20 of expected 30 settled
        
        result = await check_data_integrity_for_feedback_loop(last_n_days=3, min_settled_pct=0.95)
        
        assert result['allowed'] == False
        assert result['settled_pct'] < 0.95
    
    @pytest.mark.asyncio
    async def test_allows_on_sufficient_settlement(self, mock_db):
        mock_db.get_active_campaign_count.return_value = 10
        mock_db.execute.return_value = [{'count': 29}]  # 29 of 30 = 96.7%
        
        result = await check_data_integrity_for_feedback_loop(last_n_days=3, min_settled_pct=0.95)
        
        assert result['allowed'] == True
```

### 10.3 Integration Tests

**Focus:** API contracts, database operations, cross-component communication

#### 10.3.1 Mock Strategy for External APIs

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_shopify():
    """Mock Shopify GraphQL client"""
    mock = AsyncMock()
    mock.query.return_value = {
        'data': {
            'products': {
                'edges': [
                    {'node': {'id': 'gid://shopify/Product/123', 'title': 'Test Product'}}
                ]
            }
        }
    }
    return mock

@pytest.fixture
def mock_meta():
    """Mock Meta Marketing API client"""
    mock = AsyncMock()
    mock.create_campaign.return_value = {'id': 'campaign_123'}
    mock.get_insights.return_value = [
        {'impressions': 1000, 'clicks': 50, 'spend': 25.00, 'outbound_clicks': 40}
    ]
    return mock

@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    mock = MagicMock()
    mock.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(
            message=MagicMock(content='{"new_title": "Test Title", "new_description": "Test desc"}')
        )]
    )
    return mock

@pytest.fixture
def mock_redis():
    """Mock Redis for global pause"""
    mock = AsyncMock()
    mock.get.return_value = None  # No pause by default
    return mock
```

#### 10.3.2 Database Integration

```python
# tests/integration/test_metrics_db.py
import pytest
import sqlite3

class TestMetricsDB:
    @pytest.fixture
    def test_db(self, tmp_path):
        db_path = tmp_path / "test_metrics.db"
        # Create schema
        conn = sqlite3.connect(str(db_path))
        conn.executescript(open('schema/metrics.sql').read())
        return db_path
    
    @pytest.mark.asyncio
    async def test_upsert_metrics(self, test_db):
        # Insert initial
        await db.upsert_metric(account_id='123', object_id='camp_1', date='2024-12-28', metrics={'spend': 50})
        
        # Upsert update
        await db.upsert_metric(account_id='123', object_id='camp_1', date='2024-12-28', metrics={'spend': 75})
        
        # Verify single row with updated value
        result = await db.get_metric('camp_1', '2024-12-28')
        assert result['spend'] == 75
    
    @pytest.mark.asyncio
    async def test_settlement_flag(self, test_db):
        await db.upsert_metric(account_id='123', object_id='camp_1', date='2024-12-25', metrics={}, is_settled=False)
        await db.mark_settled('camp_1', '2024-12-25')
        
        result = await db.get_metric('camp_1', '2024-12-25')
        assert result['is_settled'] == True
```

#### 10.3.3 APEG → EcomAgent Integration

```python
# tests/integration/test_apeg_ecomagent.py
class TestAPEGEcomAgentIntegration:
    @pytest.mark.asyncio
    async def test_async_sync_bridge(self, mock_openai):
        """Verify asyncio.to_thread wrapping works"""
        from apeg_core.agents.seo_orchestrator import SEOOrchestrator
        
        orchestrator = SEOOrchestrator()
        result = await orchestrator.optimize_products([
            {'id': 'test_1', 'title': 'Test Product', 'channel': 'shopify', 'product_id': '123'}
        ])
        
        assert len(result) == 1
        assert result[0]['status'] in ['ok', 'error']
    
    @pytest.mark.asyncio
    async def test_batch_registry_prevents_overlap(self, mock_openai):
        """Verify batch overlap prevention"""
        from apeg_core.batch_registry import BatchRegistry
        
        registry = BatchRegistry()
        await registry.register_batch('high-value-birthstone', 'batch_001')
        
        can_submit = await registry.can_submit_batch('high-value-birthstone')
        assert can_submit == False
```

### 10.4 End-to-End Tests

**Scope:** Full flow validation with mocked external APIs

```python
# tests/e2e/test_seo_flow.py
class TestSEOFlow:
    @pytest.mark.asyncio
    async def test_full_seo_optimization_flow(self, mock_shopify, mock_openai, test_db):
        """
        E2E: Product fetch → SEO optimize → Stage → (mock) Approve → Bulk update
        """
        # 1. Fetch products
        products = await fetch_products_for_optimization(strategy_tag='high-value-birthstone', limit=5)
        assert len(products) == 5
        
        # 2. Optimize via SEO Engine
        results = await seo_orchestrator.optimize_batch(products)
        assert all(r['status'] == 'ok' for r in results)
        
        # 3. Stage to Google Sheets (mock)
        staged = await stage_for_approval(results)
        assert staged['row_count'] == 5
        
        # 4. Simulate approval
        await process_approval_webhook({'approved_ids': [r['id'] for r in results]})
        
        # 5. Verify bulk update queued
        pending = await db.get_pending_bulk_updates()
        assert len(pending) == 5


# tests/e2e/test_feedback_loop.py
class TestFeedbackLoop:
    @pytest.mark.asyncio
    async def test_full_feedback_loop(self, mock_meta, mock_openai, test_db):
        """
        E2E: Metrics collect → Candidate select → Refine → Approve → Apply
        """
        # Setup: Seed metrics with underperformer
        await seed_test_metrics(test_db, underperformer_id='prod_123')
        
        # 1. Check data integrity
        integrity = await check_data_integrity_for_feedback_loop()
        assert integrity['allowed'] == True
        
        # 2. Select candidates
        candidates = await select_refinement_candidates('high-value-birthstone', max_candidates=1)
        assert len(candidates) == 1
        assert candidates[0]['product_id'] == 'prod_123'
        
        # 3. Generate challenger
        challenger = await generate_challenger_seo(build_context(candidates[0]))
        assert challenger['variable_changed'] is not None
        
        # 4. Queue for approval
        approval_id = await queue_refinement_for_approval(candidates[0], challenger)
        assert approval_id is not None
        
        # 5. Approve and apply
        await process_approval_response(approval_id, 'APPROVE', 'test_user')
        
        # 6. Verify version saved
        versions = await db.get_seo_versions('prod_123')
        assert len(versions) >= 2  # Original + challenger
```

### 10.5 Contract Tests

**Purpose:** Verify API contracts match expected schemas

```python
# tests/contract/test_seo_engine_contract.py
from jsonschema import validate

SEO_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["id", "channel", "product_id", "title"],
    "properties": {
        "id": {"type": "string"},
        "channel": {"type": "string", "enum": ["shopify", "etsy"]},
        "product_id": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "constraints": {"type": "object"}
    }
}

SEO_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["id", "status"],
    "properties": {
        "id": {"type": "string"},
        "status": {"type": "string", "enum": ["ok", "error", "skipped"]},
        "new_title": {"type": ["string", "null"]},
        "new_description": {"type": ["string", "null"]},
        "new_tags": {"type": ["array", "null"]},
        "apply_changes": {"type": ["boolean", "null"]},
        "error": {"type": ["object", "null"]}
    }
}

class TestSEOEngineContract:
    def test_request_schema(self):
        valid_request = {
            "id": "shopify:product:123",
            "channel": "shopify",
            "product_id": "123",
            "title": "Test Product"
        }
        validate(instance=valid_request, schema=SEO_REQUEST_SCHEMA)
    
    def test_response_schema(self):
        valid_response = {
            "id": "shopify:product:123",
            "status": "ok",
            "new_title": "Optimized Title",
            "apply_changes": True
        }
        validate(instance=valid_response, schema=SEO_RESPONSE_SCHEMA)
```

### 10.6 Load/Stress Tests

**Purpose:** Validate system behavior under production load

```python
# tests/load/test_batch_throughput.py
import asyncio
import time

class TestBatchThroughput:
    @pytest.mark.asyncio
    async def test_50_product_batch(self, mock_openai):
        """Verify 50-product batch completes within timeout"""
        products = [make_test_product(i) for i in range(50)]
        
        start = time.time()
        results = await seo_orchestrator.optimize_batch(products)
        elapsed = time.time() - start
        
        assert len(results) == 50
        assert elapsed < 300  # 5 minute timeout
    
    @pytest.mark.asyncio
    async def test_concurrent_batches(self, mock_openai):
        """Verify batch registry prevents overlap"""
        batch1 = asyncio.create_task(run_batch('strategy_a'))
        batch2 = asyncio.create_task(run_batch('strategy_a'))  # Same strategy
        
        results = await asyncio.gather(batch1, batch2, return_exceptions=True)
        
        # One should succeed, one should be blocked
        assert sum(1 for r in results if isinstance(r, Exception)) == 1
```

### 10.7 Critical Integration Tests (API-Specific)

**Purpose:** Test exact API behaviors that cause silent failures

#### 10.7.1 Shopify Bulk Upload Ordering Test

```python
# tests/integration/test_shopify_bulk_upload.py
class TestShopifyBulkUpload:
    """
    CRITICAL: Shopify staged upload requires exact multipart field ordering
    
    Reference: Shopify bulk import docs - parameters first, file last
    """
    
    @pytest.mark.asyncio
    async def test_multipart_field_order_success(self, mock_shopify):
        """Params first, file last = success"""
        # 1. Get staged upload params
        staged = await shopify.staged_uploads_create(
            input=[{"resource": "BULK_MUTATION_VARIABLES", "filename": "test.jsonl"}]
        )
        
        url = staged['data']['stagedUploadsCreate']['stagedTargets'][0]['url']
        params = staged['data']['stagedUploadsCreate']['stagedTargets'][0]['parameters']
        
        # 2. Build multipart in CORRECT order (params first, file last)
        form_data = []
        for param in params:
            form_data.append((param['name'], param['value']))
        form_data.append(('file', ('test.jsonl', b'{"input":{}}', 'text/jsonl')))
        
        # 3. Upload
        result = await upload_to_staged_target(url, form_data)
        
        assert result['status'] == 'success'
        assert 'key' in result  # S3 key returned
    
    @pytest.mark.asyncio
    async def test_multipart_field_order_failure(self, mock_shopify):
        """File first = failure (silent XML error)"""
        staged = await shopify.staged_uploads_create(...)
        
        # WRONG order: file first
        form_data = [('file', ('test.jsonl', b'{"input":{}}', 'text/jsonl'))]
        for param in params:
            form_data.append((param['name'], param['value']))
        
        result = await upload_to_staged_target(url, form_data)
        
        # Should fail or return XML error
        assert result['status'] == 'error' or 'xml' in result.get('body', '').lower()
```

#### 10.7.2 Shopify Bulk Result JSONL Parser Test

```python
# tests/integration/test_bulk_jsonl_parser.py
class TestBulkJSONLParser:
    """
    CRITICAL: COMPLETED status does NOT mean all rows succeeded
    
    Must parse per-line userErrors from result JSONL
    """
    
    def test_mixed_success_failure_parsing(self):
        """Parse JSONL with both success and userErrors rows"""
        jsonl_content = '''
{"data":{"productUpdate":{"product":{"id":"gid://shopify/Product/1"},"userErrors":[]}}}
{"data":{"productUpdate":{"product":null,"userErrors":[{"field":["title"],"message":"Title too long"}]}}}
{"data":{"productUpdate":{"product":{"id":"gid://shopify/Product/3"},"userErrors":[]}}}
'''
        results = parse_bulk_operation_results(jsonl_content)
        
        assert results['total_count'] == 3
        assert results['success_count'] == 2
        assert results['error_count'] == 1
        assert results['errors'][0]['message'] == "Title too long"
    
    def test_all_rows_failed_triggers_alert(self):
        """100% failure rate should trigger circuit breaker"""
        jsonl_content = '''
{"data":{"productUpdate":{"product":null,"userErrors":[{"message":"Error 1"}]}}}
{"data":{"productUpdate":{"product":null,"userErrors":[{"message":"Error 2"}]}}}
'''
        results = parse_bulk_operation_results(jsonl_content)
        
        assert results['error_count'] == results['total_count']
        assert results['failure_rate'] == 1.0
```

#### 10.7.3 Bulk Failure Rate Circuit Breaker Test

```python
# tests/integration/test_bulk_failure_breaker.py
class TestBulkFailureBreaker:
    """
    CRITICAL: Prevent "COMPLETED but 100% failed" from burning catalog
    
    Rule: failure_rate > 10% = open breaker, halt next batch
    """
    
    @pytest.mark.asyncio
    async def test_breaker_opens_on_high_failure_rate(self, test_db, mock_redis):
        """Failure rate > 10% opens breaker"""
        # Simulate bulk op with 50% failure
        results = {'total_count': 100, 'error_count': 50, 'failure_rate': 0.50}
        
        evaluation = await evaluate_bulk_op_failure_rate(
            'bulk_op_123', max_failure_rate=0.10
        )
        
        assert evaluation['safe'] == False
        assert evaluation['action'] == 'GLOBAL_PAUSE'
        
        # Verify global pause was set
        pause_status = await check_global_pause()
        assert pause_status['paused'] == True
    
    @pytest.mark.asyncio
    async def test_next_batch_blocked_after_breaker(self, mock_redis):
        """Subsequent batch submissions blocked until manual reset"""
        await set_global_pause(reason='Test', set_by='test')
        
        with pytest.raises(GlobalPauseError):
            await execute_bulk_update(mutation='...', products=[])
```

#### 10.7.4 Meta Async Request Set Partial Failure Test

```python
# tests/integration/test_meta_async_request.py
class TestMetaAsyncRequestSet:
    """
    CRITICAL: Parse partial failures from asyncadrequestsets endpoint
    
    Reference: /act_{ad_account_id}/asyncadrequestsets
    """
    
    @pytest.mark.asyncio
    async def test_partial_failure_parsing(self, mock_meta):
        """Some ads created, some failed"""
        mock_meta.get_async_request_set_result.return_value = {
            'result': [
                {'success': True, 'object_id': 'ad_001'},
                {'success': False, 'error': {'message': 'Invalid image dimensions'}},
                {'success': True, 'object_id': 'ad_003'},
                {'success': False, 'error': {'message': 'Policy violation', 'code': 368}}
            ]
        }
        
        result = await parse_async_request_set_result('request_set_123')
        
        assert result['created_ids'] == ['ad_001', 'ad_003']
        assert len(result['failures']) == 2
        assert result['failures'][1]['code'] == 368  # Policy = no retry
    
    @pytest.mark.asyncio
    async def test_retry_queue_excludes_policy_errors(self, mock_meta):
        """Policy errors should NOT be queued for retry"""
        failures = [
            {'error': {'code': 100, 'message': 'Transient error'}},  # Retryable
            {'error': {'code': 368, 'message': 'Action blocked'}}   # Not retryable
        ]
        
        retry_queue = build_retry_queue(failures)
        
        assert len(retry_queue) == 1
        assert retry_queue[0]['error']['code'] == 100
```

#### 10.7.5 Meta Policy Error Classification Test

```python
# tests/integration/test_meta_error_classifier.py
class TestMetaErrorClassifier:
    """
    CRITICAL: Policy errors = hard stop, not retry
    
    Reference: Meta Marketing API error codes
    """
    
    def test_rate_limit_is_retryable(self):
        """Code 80004 = rate limit = retry with backoff"""
        action = classify_meta_error(80004, "Too many calls")
        assert action == 'RETRY'
    
    def test_policy_flag_is_hard_stop(self):
        """Code 368 = action blocked = hard stop"""
        action = classify_meta_error(368, "Action blocked")
        assert action == 'HARD_STOP'
    
    def test_unknown_policy_signal_is_hard_stop(self):
        """Classify by message content when code unknown"""
        # Unknown code but message contains policy signal
        action = classify_meta_error(
            999999, 
            "Your account has been flagged for policy violations"
        )
        assert action == 'HARD_STOP'
    
    def test_transient_errors_are_retryable(self):
        """Codes 1, 2 = transient = retry"""
        assert classify_meta_error(1, "Unknown error") == 'RETRY'
        assert classify_meta_error(2, "Service unavailable") == 'RETRY'
```

#### 10.7.6 Data Integrity Gatekeeper Test

```python
# tests/integration/test_data_integrity_gate.py
class TestDataIntegrityGate:
    """
    CRITICAL: Feedback loop must NEVER run on unsettled metrics
    
    Rule: settled_pct < 95% = BLOCK feedback loop
    """
    
    @pytest.mark.asyncio
    async def test_blocks_on_insufficient_settlement(self, test_db):
        """<95% settled = feedback loop blocked"""
        # Seed: 10 campaigns × 3 days = 30 expected rows
        # Only 25 settled = 83%
        await seed_metrics(test_db, total=30, settled=25)
        
        result = await check_data_integrity_for_feedback_loop(
            last_n_days=3, min_settled_pct=0.95
        )
        
        assert result['allowed'] == False
        assert result['settled_pct'] < 0.95
    
    @pytest.mark.asyncio
    async def test_no_refinement_emitted_when_blocked(self, test_db):
        """Blocked state = no SEO refinement jobs created"""
        await seed_metrics(test_db, total=30, settled=20)
        
        # Run feedback loop
        await daily_feedback_loop_job()
        
        # Verify no refinements queued
        pending = await db.get_pending_refinements()
        assert len(pending) == 0
    
    @pytest.mark.asyncio
    async def test_allows_on_sufficient_settlement(self, test_db):
        """≥95% settled = feedback loop proceeds"""
        await seed_metrics(test_db, total=30, settled=29)
        
        result = await check_data_integrity_for_feedback_loop()
        
        assert result['allowed'] == True
        assert result['settled_pct'] >= 0.95
```

#### 10.7.7 Meta Sandbox Smoke Test

```python
# tests/smoke/test_meta_sandbox.py
class TestMetaSandbox:
    """
    Pre-production: Verify basic ops work in Meta sandbox before prod
    
    Reference: Meta Marketing API sandbox accounts
    """
    
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_sandbox_account_access(self):
        """Can read sandbox ad account"""
        account = await meta_client.get_ad_account(SANDBOX_AD_ACCOUNT_ID)
        assert account['id'] == SANDBOX_AD_ACCOUNT_ID
    
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_sandbox_campaign_create(self):
        """Can create campaign in sandbox"""
        campaign = await meta_client.create_campaign(
            ad_account_id=SANDBOX_AD_ACCOUNT_ID,
            name='Test Campaign',
            objective='OUTCOME_TRAFFIC',
            status='PAUSED'
        )
        assert campaign['id'] is not None
        
        # Cleanup
        await meta_client.delete_campaign(campaign['id'])
```

#### 10.7.8 Global Pause Propagation Test

```python
# tests/integration/test_global_pause.py
class TestGlobalPausePropagation:
    """
    CRITICAL: Global pause must stop all agents before new work units
    """
    
    @pytest.mark.asyncio
    async def test_seo_generation_blocked(self, mock_redis):
        """SEO batch blocked when paused"""
        await set_global_pause(reason='Test', set_by='test')
        
        with pytest.raises(GlobalPauseError):
            await run_seo_batch('strategy_a', products=[])
    
    @pytest.mark.asyncio
    async def test_ad_creation_blocked(self, mock_redis):
        """Ad creation blocked when paused"""
        await set_global_pause(reason='Test', set_by='test')
        
        with pytest.raises(GlobalPauseError):
            await create_ad_campaign({})
    
    @pytest.mark.asyncio
    async def test_bulk_update_blocked(self, mock_redis):
        """Bulk update blocked when paused"""
        await set_global_pause(reason='Test', set_by='test')
        
        with pytest.raises(GlobalPauseError):
            await execute_bulk_update(mutation='...', products=[])
    
    @pytest.mark.asyncio
    async def test_metrics_collection_continues(self, mock_redis):
        """Metrics collection (read-only) can optionally continue"""
        await set_global_pause(reason='Test', set_by='test')
        
        # Metrics collection is read-only, may continue
        # (Policy decision: set METRICS_IGNORE_PAUSE=True in config)
        result = await collect_campaign_metrics('2024-12-28', '2024-12-28')
        assert result is not None  # Or raises if policy is strict
    
    @pytest.mark.asyncio
    async def test_clear_resumes_operations(self, mock_redis):
        """Clearing pause allows operations to resume"""
        await set_global_pause(reason='Test', set_by='test')
        await clear_global_pause(cleared_by='admin')
        
        # Should succeed now
        result = await run_seo_batch('strategy_a', products=[make_test_product(1)])
        assert result is not None
```

### 10.8 Pre-Production Checklist

```yaml
# tests/pre_production_checklist.yaml
environment_validation:
  - name: "API credentials valid"
    check: "All .env keys present and non-empty"
    critical: true
  
  - name: "Database migrations applied"
    check: "All tables exist with correct schema"
    critical: true
  
  - name: "Redis connection"
    check: "Can read/write global_pause key"
    critical: true

integration_smoke:
  - name: "Shopify API access"
    check: "Can fetch 1 product via GraphQL"
    critical: true
  
  - name: "Meta API access"
    check: "Can read ad account info"
    critical: true
  
  - name: "OpenAI API access"
    check: "Can complete 1 chat request"
    critical: true

safety_checks:
  - name: "Global pause cleared"
    check: "system:global_pause is not set"
    critical: true
  
  - name: "Circuit breakers closed"
    check: "All breakers in CLOSED state"
    critical: false
  
  - name: "DLQ empty or reviewed"
    check: "No PENDING items older than 24h"
    critical: false

data_integrity:
  - name: "Metrics settlement"
    check: ">95% of last 3 days settled"
    critical: true
  
  - name: "No orphan experiments"
    check: "All ACTIVE experiments have valid version IDs"
    critical: false
```

### 10.8 Test Configuration

```python
class TestConfig:
    # Coverage
    UNIT_TEST_COVERAGE_TARGET: float = 0.70
    INTEGRATION_TEST_COVERAGE_TARGET: float = 0.50
    
    # Timeouts
    UNIT_TEST_TIMEOUT_SECONDS: int = 5
    INTEGRATION_TEST_TIMEOUT_SECONDS: int = 30
    E2E_TEST_TIMEOUT_SECONDS: int = 300
    
    # Mock defaults
    MOCK_OPENAI_LATENCY_MS: int = 100
    MOCK_SHOPIFY_LATENCY_MS: int = 50
    MOCK_META_LATENCY_MS: int = 50
    
    # Test database
    USE_IN_MEMORY_SQLITE: bool = True
    TEST_DB_SEED_PRODUCTS: int = 100
    TEST_DB_SEED_CAMPAIGNS: int = 10
```

---

**Summary of Testing Strategy:**
1. ✓ Testing pyramid (70% unit, 25% integration, 5% E2E)
2. ✓ Unit tests for core logic (SKU decoder, guards, config, routing)
3. ✓ Integration tests with mocked external APIs
4. ✓ E2E tests for full flows (SEO, feedback loop)
5. ✓ Contract tests (JSON schema validation)
6. ✓ Load tests (batch throughput, concurrency)
7. ✓ Pre-production checklist
8. ✓ Critical API-specific tests (8 new)

**Critical Integration Tests Added:**
- 10.7.1: Shopify bulk upload field ordering (params first, file last)
- 10.7.2: Bulk JSONL parser (per-line userErrors extraction)
- 10.7.3: Bulk failure rate circuit breaker (>10% = halt)
- 10.7.4: Meta async request set partial failure parsing
- 10.7.5: Meta policy error classification (368 = hard stop)
- 10.7.6: Data integrity gatekeeper (<95% settled = block)
- 10.7.7: Meta sandbox smoke test (pre-prod validation)
- 10.7.8: Global pause propagation (all agents stop)

**Mock Strategy:**
- Shopify: AsyncMock with canned GraphQL responses
- Meta: AsyncMock with campaign/insights fixtures
- OpenAI: MagicMock with JSON string responses
- Redis: AsyncMock for global pause

**API Version Notes:**
- Shopify: Apps can run one bulk query and one bulk mutation operation at a time per shop (verified)
- Meta: Error code 80004 = rate limit (verified); code 368 = policy block (verified)

**CI/CD Integration Points:**
- Unit tests: Every commit
- Integration tests: Every PR
- E2E tests: Pre-merge to main
- Smoke tests: Pre-deployment (sandbox)
- Pre-production checklist: Before production deployment

---

## Appendix A: Migration Checklist

### A.1 Phase 0: Prerequisites

```yaml
environment:
  - [ ] Python 3.11+ installed
  - [ ] Node.js 18+ installed (for n8n)
  - [ ] Redis running (for global pause)
  - [ ] SQLite3 available

credentials:
  - [ ] Shopify API token with write access
  - [ ] Shopify store URL configured
  - [ ] Meta Marketing API access token
  - [ ] Meta Ad Account ID (sandbox first)
  - [ ] OpenAI API key with GPT-4 access
  - [ ] Google Sheets API credentials (service account)

network:
  - [ ] n8n accessible (localhost:5678 or Tailscale)
  - [ ] EcomAgent API reachable (port 8001)
  - [ ] APEG service reachable (port 8000)
```

### A.2 Phase 1: EcomAgent Standalone

```yaml
setup:
  - [ ] Clone EcomAgent repo
  - [ ] Copy .env.example to .env
  - [ ] Fill Shopify + OpenAI credentials
  - [ ] Install dependencies: pip install -r requirements.txt
  - [ ] Create rules/seo_baseline.yaml
  - [ ] Create rules/run_overrides.yaml (status: inactive)

validation:
  - [ ] python test_shopify.py passes (connection test)
  - [ ] python test_seo_engine.py passes (SEO generation)
  - [ ] python seo_api.py starts on port 8001
  - [ ] curl localhost:8001/optimize returns JSON

data:
  - [ ] data/output/logs/ directory exists
  - [ ] data/output/csv/ directory exists
  - [ ] First JSONL log created after test run
```

### A.3 Phase 2: n8n Integration

```yaml
setup:
  - [ ] Import workflow JSON to n8n
  - [ ] Configure Shopify credentials in n8n
  - [ ] Configure HTTP Request node to point to EcomAgent
  - [ ] Configure Google Sheets credentials
  - [ ] Create staging spreadsheet, copy ID to workflow

validation:
  - [ ] Manual trigger processes 1 product
  - [ ] SEO result appears in Google Sheets
  - [ ] JSONL log shows request/response
  - [ ] No 406 errors from Shopify update

bulk_ops:
  - [ ] Test with 5 products (limit=5)
  - [ ] Verify bulk operation completes
  - [ ] Check for per-row userErrors in results
  - [ ] Confirm products updated in Shopify admin
```

### A.4 Phase 3: APEG Integration

```yaml
setup:
  - [ ] Clone APEG repo
  - [ ] Add EcomAgent as submodule or symlink
  - [ ] Configure asyncio.to_thread wrapper
  - [ ] Initialize batch_registry table
  - [ ] Configure Redis connection

validation:
  - [ ] APEG imports SEOEngine without errors
  - [ ] Async wrapper executes sync SEO calls
  - [ ] Batch registry prevents duplicate submissions
  - [ ] Global pause key readable/writable

database:
  - [ ] metrics.db created with schema
  - [ ] seo_versions table exists
  - [ ] experiments table exists
  - [ ] dead_letter_queue table exists
```

### A.5 Phase 4: Metrics Collection

```yaml
setup:
  - [ ] Configure Meta API credentials in APEG
  - [ ] Set AD_ACCOUNT_ID and timezone
  - [ ] Create metrics collection schedule
  - [ ] Configure Shopify order attribution query

validation:
  - [ ] Manual metrics fetch returns data
  - [ ] JSONL audit log created
  - [ ] SQLite metrics table populated
  - [ ] is_settled flag updates after 72h
  - [ ] UTM attribution extracts correctly

monitoring:
  - [ ] Settlement coverage > 95% after 3 days
  - [ ] No rate limit errors (check throttle header)
  - [ ] Backfill runs on Monday
```

### A.6 Phase 5: Feedback Loop

```yaml
setup:
  - [ ] Configure feedback loop thresholds
  - [ ] Set MIN_SPEND, MIN_IMPRESSIONS gates
  - [ ] Configure cooldown (7 days)
  - [ ] Set max iterations (3)
  - [ ] Configure approval queue (Google Sheets or DB)

validation:
  - [ ] Data integrity gate blocks on <95% settled
  - [ ] Candidate selection respects cooldown
  - [ ] Funnel stage routing correct (manual verification)
  - [ ] Challenger generation produces valid JSON
  - [ ] Approval workflow triggers correctly

safety:
  - [ ] Rollback function tested
  - [ ] Version history preserved
  - [ ] Ad refresh flags set on SEO change
```

### A.7 Phase 6: Advertising Agent

```yaml
setup:
  - [ ] Configure Meta sandbox account
  - [ ] Set campaign naming convention
  - [ ] Configure UTM template
  - [ ] Set budget defaults (fixed V1)
  - [ ] Configure targeting (V1 safe: no exclusions)

validation:
  - [ ] Sandbox campaign creates successfully
  - [ ] Ad set with V1 targeting passes validation
  - [ ] Creative uses Shopify images
  - [ ] UTM parameters in destination URL
  - [ ] Campaign ID stored in DB

production:
  - [ ] Switch to production ad account
  - [ ] Verify billing active
  - [ ] Create first campaign (PAUSED)
  - [ ] Manual review before ACTIVE
```

### A.8 Go-Live Checklist

```yaml
pre_launch:
  - [ ] All circuit breakers CLOSED
  - [ ] Global pause CLEARED
  - [ ] DLQ empty or reviewed
  - [ ] Data integrity > 95%
  - [ ] Slack webhook configured
  - [ ] Alert email verified

first_batch:
  - [ ] Run 10-product test batch
  - [ ] Review Google Sheets staging
  - [ ] Approve via webhook
  - [ ] Verify Shopify updates
  - [ ] Check JSONL logs

scale_up:
  - [ ] Run 50-product batch
  - [ ] Monitor bulk op status
  - [ ] Check failure rate < 10%
  - [ ] Verify no rate limits hit

monitoring:
  - [ ] Grafana/dashboard configured (optional)
  - [ ] Daily metrics collection running
  - [ ] Weekly backfill scheduled
  - [ ] Feedback loop scheduled (post-settlement)
```

---

## Appendix B: File Structure Reference

### B.1 Repository Layout

```
EcomAgent/
├── src/
│   └── seo_engine/
│       ├── __init__.py
│       ├── engine.py              # Main SEO optimization logic
│       ├── config.py              # ConfigLoader + SafetyViolationError
│       ├── parsers/
│       │   ├── __init__.py
│       │   └── sku_decoder.py     # SKU → attributes parser
│       ├── validators/
│       │   ├── __init__.py
│       │   └── guard.py           # ConstraintGuard (post-LLM enforcement)
│       └── exporters/
│           ├── __init__.py
│           └── backup_manager.py  # JSONL + CSV export
├── rules/
│   ├── seo_baseline.yaml          # Immutable safety defaults
│   └── run_overrides.yaml         # Ephemeral preferences (git-ignored)
├── data/
│   └── output/
│       ├── logs/                  # JSONL audit trail
│       └── csv/                   # Shopify import format
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── seo_api.py                     # Flask API entry point
├── requirements.txt
└── .env                           # Credentials (git-ignored)

APEG/
├── src/
│   └── apeg_core/
│       ├── __init__.py
│       ├── main.py                # FastAPI entry point
│       ├── agents/
│       │   ├── seo_orchestrator.py    # APEG → EcomAgent wrapper
│       │   └── advertising_agent.py   # Meta campaign management
│       ├── metrics/
│       │   ├── collector.py           # Meta + Shopify metrics fetch
│       │   ├── attribution.py         # UTM waterfall logic
│       │   └── settlement.py          # Settlement window tracking
│       ├── feedback_loop/
│       │   ├── action_router.py       # Funnel stage diagnosis
│       │   ├── candidate_selector.py  # Underperformer scoring
│       │   ├── challenger_generator.py # LLM refinement calls
│       │   └── version_control.py     # seo_versions management
│       ├── error_handling/
│       │   ├── circuit_breaker.py
│       │   ├── retry.py
│       │   ├── dead_letter.py
│       │   └── global_pause.py
│       └── db/
│           ├── schema.sql             # All table definitions
│           └── queries.py             # DB access layer
├── data/
│   ├── metrics.db                 # SQLite metrics store
│   └── metrics/                   # JSONL audit trail
├── tests/
├── requirements.txt
└── .env

n8n/
├── workflows/
│   └── seo_sweep_v1.json          # Main workflow export
└── credentials/                   # n8n credential backups
```

### B.2 Configuration Files

```yaml
# EcomAgent/rules/seo_baseline.yaml
safety:
  max_title_length: 70
  max_meta_description_length: 320
  banned_words: ["cheap", "guarantee", "cure", "best selling"]
  preserve_words: []

engine_defaults:
  tone: "friendly, professional"
  brand_voice: "authentic"
  tag_target: 13

hard_limits:
  max_title_length: 140
  max_meta_description_length: 500
```

```yaml
# EcomAgent/rules/run_overrides.yaml (example: holiday mode)
status: "active"  # or "inactive"
preferences:
  seasonal_tone: "Use festive Christmas language. Mention gift-giving."
  force_title_length: 80
  suppress_collections: ["Whispers"]
```

```ini
# EcomAgent/.env
SHOPIFY_STORE=your-store-name
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_xxxxx
OPENAI_API_KEY=sk-xxxxx
```

```ini
# APEG/.env
SHOPIFY_STORE=your-store-name
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_xxxxx
OPENAI_API_KEY=sk-xxxxx
META_ACCESS_TOKEN=EAAxxxxx
META_AD_ACCOUNT_ID=act_123456789
META_APP_ID=xxxxx
META_APP_SECRET=xxxxx
REDIS_URL=redis://localhost:6379
SLACK_WEBHOOK_URL=https://hooks.slack.com/xxxxx
ALERT_EMAIL=alerts@yourstore.com
```

### B.3 Database Schema Files

```sql
-- APEG/src/apeg_core/db/schema.sql

-- Metrics (Section 7)
CREATE TABLE metrics (
    account_id TEXT NOT NULL,
    level TEXT NOT NULL,
    object_id TEXT NOT NULL,
    date TEXT NOT NULL,
    campaign_id TEXT,
    adset_id TEXT,
    ad_id TEXT,
    creative_id TEXT,
    strategy_tag TEXT,
    run_id TEXT,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    spend REAL DEFAULT 0.0,
    ctr REAL DEFAULT 0.0,
    cpc REAL DEFAULT 0.0,
    reach INTEGER DEFAULT 0,
    frequency REAL DEFAULT 0.0,
    outbound_clicks INTEGER DEFAULT 0,
    outbound_clicks_ctr REAL DEFAULT 0.0,
    is_settled BOOLEAN DEFAULT FALSE,
    last_refreshed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, level, object_id, date)
);

-- SEO Versions (Section 8)
CREATE TABLE seo_versions (
    version_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    title TEXT,
    meta_title TEXT,
    meta_description TEXT,
    description_html TEXT,
    tags TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    reason TEXT,
    refinement_context TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    evaluation_start_date TEXT,
    evaluation_end_date TEXT
);

-- Experiments (Section 8)
CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    strategy_tag TEXT,
    champion_version_id TEXT NOT NULL,
    challenger_version_id TEXT,
    start_date TEXT NOT NULL,
    champion_window_start TEXT,
    champion_window_end TEXT,
    challenger_window_start TEXT,
    challenger_window_end TEXT,
    stable_window_used TEXT,
    status TEXT DEFAULT 'ACTIVE',
    decision TEXT,
    decision_reason TEXT,
    decided_at TEXT,
    decided_by TEXT,
    champion_metrics TEXT,
    challenger_metrics TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Dead Letter Queue (Section 9)
CREATE TABLE dead_letter_queue (
    dlq_id TEXT PRIMARY KEY,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    component TEXT NOT NULL,
    operation TEXT NOT NULL,
    entity_id TEXT,
    entity_type TEXT,
    error_code TEXT,
    error_message TEXT,
    error_context TEXT,
    request_payload TEXT,
    status TEXT DEFAULT 'PENDING',
    resolved_at TEXT,
    resolved_by TEXT,
    resolution_notes TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TEXT,
    next_retry_at TEXT
);

-- Batch Registry (Section 9)
CREATE TABLE batch_registry (
    batch_id TEXT PRIMARY KEY,
    strategy_tag TEXT NOT NULL,
    status TEXT DEFAULT 'in_progress',
    created_at TEXT,
    completed_at TEXT,
    error_message TEXT
);

-- Ad Creative Links (Section 8)
CREATE TABLE ad_creative_links (
    link_id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    ad_id TEXT NOT NULL,
    creative_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    seo_version_id TEXT,
    status TEXT DEFAULT 'ACTIVE',
    status_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_refreshed_at TEXT
);

-- Strategy Playbooks (Section 8)
CREATE TABLE strategy_playbooks (
    pattern_id TEXT PRIMARY KEY,
    strategy_tag TEXT NOT NULL,
    variable TEXT,
    pattern TEXT,
    impact TEXT,
    confidence REAL,
    sample_size INTEGER DEFAULT 1,
    example_change TEXT,
    metrics TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Advertising Campaigns (Section 6)
CREATE TABLE advertising_campaigns (
    campaign_id TEXT PRIMARY KEY,
    strategy_tag TEXT NOT NULL,
    run_id TEXT,
    name TEXT,
    objective TEXT,
    status TEXT,
    budget_type TEXT,
    daily_budget REAL,
    lifetime_budget REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    meta_campaign_id TEXT,
    meta_adset_id TEXT
);

-- Indexes
CREATE INDEX idx_metrics_date ON metrics(date);
CREATE INDEX idx_metrics_settled ON metrics(is_settled);
CREATE INDEX idx_metrics_strategy ON metrics(strategy_tag);
CREATE INDEX idx_seo_versions_product ON seo_versions(product_id);
CREATE INDEX idx_seo_versions_active ON seo_versions(is_active);
CREATE INDEX idx_experiments_product ON experiments(product_id);
CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_dlq_status ON dead_letter_queue(status);
CREATE INDEX idx_batch_strategy ON batch_registry(strategy_tag);
CREATE INDEX idx_ad_links_product ON ad_creative_links(product_id);
```

### B.4 Key API Endpoints

```yaml
# EcomAgent (Flask, port 8001)
POST /optimize:
  input: SEO_ENGINE_CONTRACT request
  output: SEO_ENGINE_CONTRACT response
  
# APEG (FastAPI, port 8000)
POST /seo/batch:
  input: {strategy_tag, product_ids[], constraints{}}
  output: {batch_id, status, results[]}

POST /ads/campaign:
  input: {strategy_tag, product_set_id, budget{}}
  output: {campaign_id, status}

GET /metrics/{strategy_tag}:
  output: {products[], aggregates{}}

POST /feedback/run:
  input: {strategy_tag, max_candidates}
  output: {candidates[], proposals[]}

POST /admin/pause:
  input: {reason, set_by}
  output: {paused: true}

DELETE /admin/pause:
  input: {cleared_by}
  output: {paused: false}
```

### B.5 n8n Workflow Nodes

```yaml
# Key nodes in SEO Sweep workflow
1_Trigger:
  type: Manual or Schedule
  
2_Fetch_Products:
  type: Shopify GraphQL
  query: products(first: 50, query: "...")
  
3_Build_SEO_Request:
  type: Code (JavaScript)
  extracts: SKU, title, description, tags
  
4_Call_EcomAgent:
  type: HTTP Request
  url: http://localhost:8001/optimize
  method: POST
  
5_Stage_To_Sheets:
  type: Google Sheets
  operation: Append
  
6_Wait_For_Approval:
  type: Webhook
  path: /approve
  
7_Build_Bulk_Mutation:
  type: Code (JavaScript)
  builds: productUpdate mutations
  
8_Execute_Bulk_Op:
  type: Shopify GraphQL
  mutation: bulkOperationRunMutation
  
9_Poll_Status:
  type: Loop + HTTP Request
  polls: node(id: bulk_op_gid)
```


---

## Appendix C: Risk Register + V2 Roadmap

### C.1 Risk Register (Implementation Challenges)

| Risk ID | Risk | Impacted Section | Detection | Mitigation |
|---------|------|------------------|-----------|------------|
| C1 | Shopify Bulk Op Query Drift | Section 5 | Poller returns null/empty | Poll by persisted GID, pin API version |
| C2 | Meta Targeting Validation (v22+) | Section 6 | AdSet create validation error | V1: No exclusions, broad/interest only |
| C3 | OpenAI Batch Overlap | SEO batch scheduling | Batch rejected, prior still in_progress | BatchRegistry per strategy_tag |
| C4 | Metrics Settlement Latency | Section 7 | Day-over-day drift in prior dates | Rolling 3-day UPSERT |
| C5 | Link Preview Metadata Override | Section 6, 8 | Ad preview ignores headline/description | Prefer non-link-preview formats, ensure OG tags |

**RISK-C1: Shopify Bulk Op Query Drift**
- `currentBulkOperation` deprecated in newer API versions
- Mitigation: Persist `bulk_operation_gid` at creation, poll by ID
- Pin API version in config; version-gate poller query

**RISK-C2: Meta Targeting Validation (v22+)**
- Detailed Targeting Exclusions removed/blocked
- Mitigation: V1 forbids exclusions entirely
- Restrict to Broad or Interest-only inclusion
- Do not set Advantage+ flags unless exact SDK fields verified

**RISK-C3: OpenAI Batch Overlap**
- Batch jobs can run 24h; daily schedules overlap
- Mitigation: BatchRegistry keyed by strategy_tag
- If active batch exists, skip or queue next run
- Monitor org-level enqueued limits

**RISK-C4: Metrics Settlement Latency**
- Meta reporting updates retroactively
- Mitigation: Rolling 3-day re-fetch (Day0, Day-1, Day-2)
- UPSERT by (date, entity_id, breakdown keys)

**RISK-C5: Link Preview Metadata Override**
- Some workflows cannot override link headline/description
- Mitigation: Prefer creatives without link-preview dependency
- Ensure destination pages have correct Open Graph metadata
- Treat "SEO fields become ad fields" as best-effort

### C.2 V2 Roadmap (Future Enhancements)

| ID | Feature | Description | Prerequisites |
|----|---------|-------------|---------------|
| V2-CB1 | Circuit Breaker Dashboard | UI for breaker states, reset controls, DLQ replay | Redis, web UI |
| V2-BD1 | ROAS-Driven Dynamic Budgeting | Auto-adjust budgets based on conversion data | Pixel/CAPI attribution |
| V2-CR1 | Automated Creative Refresh | LLM-generated copy + Ad Copies API for duplication | Meta generative features |
| V2-SOV1 | Competitor Share-of-Voice | Competitor price/keywords in refinement context | Compliance review |
| V2-GA1 | GA4 Site Metrics Integration | Bounce rate, sessions, add-to-cart in funnel diagnosis | GA4 API connector |
| V2-REV1 | Product Reviews Enrichment | Judge.me/Yotpo integration for review themes | Review app API |

**V2-BD1: ROAS-Driven Dynamic Budgeting**
- Requires accurate conversion attribution (Pixel/CAPI)
- Enforce caps/floors and gradual adjustment policy
- V1: Fixed budgets only

**V2-CR1: Automated Creative Refresh**
- NOT "Ad Copies API generates headlines"
- Use: (a) APEG/LLM generated copy OR (b) Meta generative features
- Use Ad Copies API only for duplication + swapping in new creative fields

**V2-SOV1: Competitor Share-of-Voice**
- Requires compliance review for scraping/proxy tooling
- Feed competitor price/keywords as optional enrichment
- V1: Not implemented

---

## Appendix D: Machine-Readable Artifacts

**Purpose:** Provide actionable stubs for agent integration artifacts. These files should be placed at the indicated repository paths and populated during implementation.

### D.1 OpenAPI Specification

**Repo Path:** `schemas/openapi.yaml`

**Purpose:** Define APEG internal API endpoints for agent tool discovery and autonomous operation.

```yaml
openapi: 3.1.0
info:
  title: APEG Internal API
  version: 0.1.0
servers:
  - url: http://localhost:8000
paths:
  /health:
    get:
      summary: Health check
      responses:
        "200":
          description: OK
  /jobs/shopify/bulk/run:
    post:
      summary: Submit a Shopify GraphQL Bulk Operation (JSONL staged upload + run)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ShopifyBulkRunRequest"
      responses:
        "200":
          description: Accepted
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ShopifyBulkRunResponse"
components:
  schemas:
    ShopifyBulkRunRequest:
      type: object
      required: [shop, api_version, mutation_name, jsonl_source]
      properties:
        shop: { type: string, description: "shop domain" }
        api_version: { type: string, description: "Pinned Admin API version" }
        mutation_name: { type: string }
        jsonl_source:
          type: object
          required: [type]
          properties:
            type: { type: string, enum: ["local_file","gcs_key","inline"] }
            value: { type: string }
    ShopifyBulkRunResponse:
      type: object
      required: [job_id, status]
      properties:
        job_id: { type: string }
        status: { type: string, enum: ["queued","running","completed","failed"] }
```

### D.2 Agent Codec Schema

**Repo Path:** `schemas/agent_codec.schema.json`

**Purpose:** Define the structure for agent tool definitions, enabling autonomous agents to discover and invoke APEG capabilities safely.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://apeg.local/schemas/agent_codec.schema.json",
  "title": "APEG Agent Codec",
  "type": "object",
  "required": ["tools"],
  "properties": {
    "tools": {
      "type": "array",
      "items": { "$ref": "#/$defs/tool" }
    }
  },
  "$defs": {
    "tool": {
      "type": "object",
      "required": ["name", "description", "input_schema", "output_schema", "side_effects"],
      "properties": {
        "name": { "type": "string" },
        "description": { "type": "string" },
        "input_schema": { "type": "object" },
        "output_schema": { "type": "object" },
        "side_effects": { "type": "string", "enum": ["none","read","write","external_spend"] }
      }
    }
  }
}
```

### D.3 Common Product Model Field Registry

**Repo Path:** `mappings/cpm_field_registry.yaml`

**Purpose:** Abstract Shopify vs Etsy field differences for cross-platform operations.

```yaml
version: 0.1.0
shopify_to_cpm:
  meta_title: "shopify.seo.title"
  meta_description: "shopify.seo.description"
  # REST API equivalent fields (for reference):
  # meta_title: "shopify.metafields_global_title_tag"
  # meta_description: "shopify.metafields_global_description_tag"
etsy_constraints:
  tags:
    max_count: 13
    normalization:
      - trim
      - dedupe_case_insensitive
      - stable_sort
    selection_strategy: "top_k_by_priority_rules"
```

### D.4 CI Workflow

**Repo Path:** `.github/workflows/ci.yml`

**Purpose:** Continuous integration pipeline with test coverage enforcement.

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest --cov=apeg --cov-fail-under=75
```

### D.5 License Scan Workflow

**Repo Path:** `.github/workflows/license-scan.yml`

**Purpose:** Block GPL dependencies from entering the MIT-licensed codebase.

```yaml
name: license-scan
on: [push, pull_request]
jobs:
  license-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies (required for accurate license scan)
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f pyproject.toml ]; then pip install .; fi
          pip install pip-licenses
      - name: Fail on GPL/LGPL/AGPL licenses
        run: |
          pip-licenses --format=plain-vertical --with-license-file --fail-on="GPL,LGPL,AGPL"
```

### D.6 LangGraph Checkpoint Setup

**Repo Path:** `schemas/langgraph_checkpoint_setup.md`

**Purpose:** Instructions for setting up LangGraph persistence with PostgreSQL (recommended for production durability).

```markdown
# LangGraph Checkpoint Setup

## Recommended: PostgresSaver (Production)

LangGraph provides a built-in PostgreSQL-backed checkpoint saver that manages its own schema.

### Setup Steps:

1. Install psycopg:
   ```bash
   pip install "psycopg[binary]"
   ```

2. Initialize the saver and let it create tables:
   ```python
   from langgraph.checkpoint.postgres import PostgresSaver
   
   # Connection string from environment
   DB_URI = "postgresql://user:pass@host:5432/apeg_checkpoints"
   
   # Create saver and run setup (creates tables if not exist)
   with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
       checkpointer.setup()  # Creates required tables
       
       # Use with your graph
       graph = workflow.compile(checkpointer=checkpointer)
   ```

### Why PostgresSaver over SQLite:
- Durability for long-running jobs (24h+ bulk operations)
- Concurrent access from multiple workers
- Production-grade reliability

### DO NOT:
- Manually create checkpoint tables (schema managed by LangGraph)
- Use SQLite for production checkpoints (development only)
```

---

## Appendix E: Change Resolution Log

**Document Version:** 1.4.1
**Last Updated:** 2025-12-29  
**Status:** UPDATED (Demo→Live Ready)

### Applied Changes (v1.3 → v1.4) — Demo→Live + Meta Config

| CHANGE_ID | Section | Status | Notes |
|-----------|---------|--------|-------|
| ENV-01 | NEW Section 1.8 | APPLIED | Config surface area (Shopify, Meta, n8n, Infra vars) |
| ENV-02 | NEW Appendix F | APPLIED | Demo→Live swap runbook with smoke tests |
| SHOP-01 | Section 5.6 | ALREADY DONE (ST2-01) | node(id:) polling already implemented |
| SHOP-02 | Section 5.10 | ALREADY DONE (ST2-02) | Shop-specific locks already implemented |
| SHOP-03 | Section 5.5 | APPLIED | Upload hard gate added; "JSONL file not found" prevention |
| META-01 | NEW Section 6.12 | APPLIED | Meta deployment config + smoke test code |
| N8N-01 | NEW Section 8.13 | APPLIED | n8n credential swap checklist |

### Applied Changes (v1.2 → v1.3) — Stage 2 Runtime Verification

| CHANGE_ID | Section | Status | Notes |
|-----------|---------|--------|-------|
| ST2-01 | Section 5.6 Polling | APPLIED | `bulkOperations(...)` does NOT exist in API 2025-10; replaced with `node(id:)` polling |
| ST2-02 | Section 5.10 Concurrency | APPLIED | Added shop-specific locks; evidence: "already in progress" error on concurrent starts |
| ST2-03 | Section 2.4.2 Tags | APPLIED | Tag MERGE marked VERIFIED (dev-store test passed) |
| ST2-04 | Section 7 Attribution | APPLIED | Added "do not gate build/deploy" to UNVERIFIED customerJourney note |
| ST2-05 | Section 5.5 Staged Upload | APPLIED | Added stagedUploadPath guardrail; local paths rejected |

**Stage 2 Evidence Notes:**
- `bulkOperations` error: "Field 'bulkOperations' doesn't exist on type 'QueryRoot'" (API 2025-10)
- Concurrency error: "A bulk query operation for this app and shop is already in progress: <id>"
- stagedUploadPath: bulkOperationRunMutation rejected /tmp path, expects Shopify bucket bulk/ path

### Applied Changes (v1.1 → v1.2)

| CHANGE_ID | Section | Status | Notes |
|-----------|---------|--------|-------|
| DOC-01 | Section 9.9 Config | APPLIED | Fixed SHOPIFY_API_VERSION from '2024-10' to '2025-10'; added version window policy |
| DOC-02 | Section 10 API Notes | APPLIED | Corrected bulk concurrency: "1 query + 1 mutation per shop" (not "5 in 2026-01") |
| DOC-03 | Section 5.6 Webhook | APPLIED | Fixed HMAC import bug (`from hmac import HMAC` → `import hmac`) |
| DOC-04 | Appendix D license-scan | APPLIED | Workflow now installs deps before scanning; catches GPL in actual requirements |
| DOC-05 | Appendix D checkpoint | APPLIED | Replaced SQLite DDL with PostgresSaver setup instructions |
| DOC-06 | Section 1.7 | APPLIED | Added 2026-01-01 custom app creation change note |
| DOC-07 | Section 5.6 Bulk Ops | SUPERSEDED by ST2-01 | bulkOperations query removed; node(id:) polling used instead |
| DOC-08 | Section 7 Attribution | APPLIED | Clarified customerJourney attribution window semantics |
| DOC-09 | Section 9.9 Meta Config | APPLIED | Added citations for Meta error codes 80004 and 368 |
| DOC-10 | Appendix D openapi.yaml | DEFERRED | Stub expansion is DESIGN WORK; marked TEST REQUIRED |

### Applied Changes (v1.0 → v1.1)

| CHANGE_ID | Section | Status | Notes |
|-----------|---------|--------|-------|
| INC-001 | Section 3.3 (Bulk Ops) | ALREADY SATISFIED | Spec already uses `bulkOperation(id:)`. Added `bulkOperations` query guidance. |
| INC-002 | Section 2 (Licensing) | APPLIED | Added Section 1.7 with GPL/etsyv3 licensing blocker |
| INC-003 | Section 1.2 (SEO Fields) | ALREADY SATISFIED | Code correctly uses `seo.title`. Added clarification note in Section 1.7 |
| INC-004 | Section 2.1 (Agent Artifacts) | APPLIED | Added Appendix D with openapi.yaml, agent_codec, CPM registry stubs |
| INC-005 | Section 4.3 (Guardrails) | APPLIED | Added Section 2.4.2 with explicit tag merge policy and banned words reference |
| INC-006 | Additional (Changelog) | APPLIED | Added Developer Changelog monitoring note in Section 1.7 |
| INC-007 | Additional (MCP) | APPLIED | Added MCP clarification in Section 1.7 |

### Verified Items (Stage 2)

| Item | Section | Result |
|------|---------|--------|
| Tag Merge Behavior | Section 2.4.2 | ✓ VERIFIED - pre-existing tags preserved |
| node(id:) Polling | Section 5.6 | ✓ VERIFIED - works on API 2025-10 |
| Concurrency Constraint | Section 5.10 | ✓ VERIFIED - 1 query + 1 mutation per shop |

### Still Unverified

| Item | Section | Action |
|------|---------|--------|
| CustomerJourney Attribution Window | Section 7 | Non-build-gating unless attribution correctness is required |
| OpenAPI Stub Expansion | Appendix D | Design work; expand when APEG interface finalized |

### Deferred Items

| Item | Reason | Resolution Path |
|------|--------|-----------------|
| Etsy Integration | GPL licensing blocker | Resolve via microservice isolation or custom REST implementation before Phase 5 |
| OpenAPI Expansion (DOC-10) | Design work required | Expand stub with auth, error schemas, idempotency headers when APEG interface finalized |

---

## Appendix F: Demo → Live Swap Runbook

**Purpose:** Deterministic procedure for cutover from demo to production environment.

### F.1 Shopify Live App Install

```yaml
checklist:
  - [ ] Live custom app exists (post-2026 path: Partner Dashboard or CLI)
  - [ ] Scopes match demo:
    - write_products, read_products
    - write_inventory, read_inventory (if used)
    - write_metaobjects, read_metaobjects (if used)
  - [ ] Admin API token generated
  - [ ] Token stored in secret store (NOT repo)
  - [ ] Webhook secret generated and stored
```

### F.2 Update APEG Runtime Config

```bash
# Switch environment
export ENVIRONMENT=LIVE

# Shopify credentials
export SHOPIFY_STORE_DOMAIN="your-live-store.myshopify.com"
export SHOPIFY_ADMIN_ACCESS_TOKEN="<from-secret-store>"
export SHOPIFY_WEBHOOK_SHARED_SECRET="<from-secret-store>"
export SHOPIFY_API_VERSION="2025-10"  # Keep pinned during cutover
```

### F.3 Update n8n Credentials (CRITICAL)

```yaml
workflow_credential_swap:
  - [ ] Open each workflow in n8n editor
  - [ ] Replace Shopify credential: demo token → live token
  - [ ] Replace Meta credential: demo ad account → live ad account
  - [ ] Verify all nodes point to LIVE credential IDs
  - [ ] Save all workflows
  - [ ] Re-deploy webhooks to production endpoint
  - [ ] Verify execution log shows LIVE credential
```

### F.4 Smoke Tests (Must PASS)

**Shopify Auth:**
```graphql
query { shop { name } }
# Expected: Returns live store name
```

**Bulk Query:**
```
1. Execute bulkOperationRunQuery
2. Poll via node(id:) until COMPLETED
3. Verify result URL accessible
```

**Bulk Mutation:**
```
1. stagedUploadsCreate → get upload URL
2. Multipart upload test JSONL
3. bulkOperationRunMutation with stagedUploadPath
4. Poll via node(id:) until COMPLETED
```

**Tag Merge:**
```
1. Fetch product with existing tags
2. Add new tags via productUpdate
3. Verify ALL original tags preserved
```

**Webhook HMAC:**
```
1. Trigger test webhook from Shopify
2. Verify HMAC signature validation passes
3. Confirm payload processed correctly
```

### F.5 Meta Ads Smoke (If Immediate)

```yaml
meta_smoke_tests:
  - [ ] Debug token valid with required scopes
  - [ ] Read ad account basic fields
  - [ ] Create PAUSED campaign (then delete)
  - [ ] Interest ID lookup returns results
```

### F.6 Go/No-Go Checklist

| Test | Result | Blocker? |
|------|--------|----------|
| Shopify auth | [ ] PASS / [ ] FAIL | YES |
| Bulk query | [ ] PASS / [ ] FAIL | YES |
| Bulk mutation | [ ] PASS / [ ] FAIL | YES |
| Tag merge | [ ] PASS / [ ] FAIL | YES |
| Webhook HMAC | [ ] PASS / [ ] FAIL | YES |
| Meta token | [ ] PASS / [ ] FAIL | If Meta immediate |
| n8n credential swap | [ ] PASS / [ ] FAIL | YES |

**Proceed to live only when ALL blockers PASS.**
