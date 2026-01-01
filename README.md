# APEG: Autonomous Product Extraction & Generation

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Project Status](https://img.shields.io/badge/status-active%20development-green.svg)]()

> A unified, async-first orchestrator that autonomously manages Shopify and Etsy stores through intelligent SEO optimization, bulk operations, and metrics-driven feedback loops.

## 🎯 Overview

APEG (Autonomous Product Extraction & Generation) is the **Master Agent** combining two legacy systems:

1. **PEG (Inventory Logic):** Deterministic inventory management and synchronization
2. **EcomAgent (SEO/Content):** Probabilistic content generation and optimization

The system provides a unified FastAPI-based orchestrator that wraps these legacy capabilities to create an intelligent, metrics-driven e-commerce automation platform.

## ✨ Key Features

- **🚀 Async-First Architecture**: Built on FastAPI for high-performance concurrent operations
- **📦 Shopify Bulk Operations**: Efficient batch processing using GraphQL bulk queries and mutations
- **🎨 SEO Content Generation**: AI-powered product title and description optimization
- **📊 Metrics Intelligence**: Meta Ads integration with performance tracking and attribution
- **🔄 Feedback Loop**: Automated A/B testing and refinement based on real metrics (CTR, ROAS)
- **🔒 Safe Write Operations**: Tag merge algorithms and staged uploads with rollback capability
- **🎯 Multi-Platform**: Support for Shopify and Etsy (draft mode)
- **🔐 Security First**: Environment-based configuration, distributed locks, and audit logging

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         APEG (Master)                            │
│              Async Orchestrator (FastAPI)                        │
└───────────┬─────────────────────────────────────┬───────────────┘
            │                                     │
            ▼                                     ▼
┌───────────────────────┐              ┌─────────────────────────┐
│   EcomAgent (SEO)     │              │   Advertising Agent     │
│   Content Generation  │              │   (Meta API Client)     │
└───────┬───────────────┘              └──────────┬──────────────┘
        │                                         │
        ▼                                         ▼
┌───────────────────────┐              ┌─────────────────────────┐
│   N8N Workflow        │              │   Meta Marketing API    │
│   (Orchestration)     │              │   (Ads Platform)        │
└───────┬───────────────┘              └──────────┬──────────────┘
        │                                         │
        ▼                                         ▼
┌───────────────────────┐              ┌─────────────────────────┐
│   Shopify Store       │◄─────────────┤   Metrics Database      │
│   (Product Catalog)   │              │   (JSONL + SQLite)      │
└───────────────────────┘              └─────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Redis server (for distributed locks)
- Shopify store with Admin API access
- (Optional) Meta Ads account for advertising features
- (Optional) n8n instance for workflow automation

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Matthewtgordon/APEG.git
   cd APEG
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your credentials
   ```

4. **Start Redis (if not already running):**
   ```bash
   docker run -d -p 6379:6379 redis:latest
   ```

5. **Run the API server:**
   ```bash
   set -a; source .env; set +a
   PYTHONPATH=. uvicorn src.apeg_core.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Verify installation:**
   ```bash
   curl http://localhost:8000/docs
   ```

## 📚 Documentation

### Core Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Documentation index and repository structure |
| [docs/PROJECT_PLAN_ACTIVE.md](docs/PROJECT_PLAN_ACTIVE.md) | Current development roadmap and phase status |
| [docs/integration-architecture-spec-v1.4.1.md](docs/integration-architecture-spec-v1.4.1.md) | Complete architecture specification |
| [docs/API_USAGE.md](docs/API_USAGE.md) | API endpoints and usage examples |
| [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | Environment configuration guide |
| [docs/ACCEPTANCE_TESTS.md](docs/ACCEPTANCE_TESTS.md) | Test specifications and verification |

### Operational Guides

- **Configuration**: See [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)
- **API Reference**: See [docs/API_USAGE.md](docs/API_USAGE.md)
- **n8n Integration**: See [docs/N8N_WORKFLOW_CONFIG.md](docs/N8N_WORKFLOW_CONFIG.md)
- **Testing**: See [tests/integration/README.md](tests/integration/README.md)

## 🔑 Key Concepts

### Environment Profiles

APEG supports two environment profiles:

- **DEMO**: Development and testing against development stores
- **LIVE**: Production operations against live stores

Set via `ENVIRONMENT=DEMO` or `ENVIRONMENT=LIVE` in your `.env` file.

### Safe Write Operations

All Shopify updates use safe-write patterns:

- **Tag Merging**: `final_tags = (current_tags ∪ tags_add) - tags_remove`
- **Staged Uploads**: Multi-step verification before bulk mutations
- **Rollback Capability**: Champion/Challenger version control
- **Distributed Locks**: Prevent concurrent operations on the same store

### Phase-Based Development

The project follows a structured phase approach:

- **Phase 0**: Configuration and preconditions
- **Phase 1**: Deterministic Shopify backbone
- **Phase 2**: Bulk mutations and safe writes ✅
- **Phase 3**: n8n orchestration bindings ✅
- **Phase 4**: Data collection and metrics intelligence ✅
- **Phase 5**: Feedback loop and refinement engine ✅
- **Phase 6**: Hardening and CI/CD (in progress)

## 🧪 Testing

### Run Unit Tests

```bash
PYTHONPATH=. pytest tests/unit/ -v
```

### Run Integration Tests

```bash
# Configure test environment
cp .env.example .env.integration
# Edit .env.integration with DEMO credentials

# Load environment
set -a; source .env.integration; set +a

# Run integration tests
PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py
```

See [tests/integration/README.md](tests/integration/README.md) for detailed testing documentation.

## 🔒 Security

- **No Secrets in Code**: All credentials via environment variables
- **API Key Authentication**: Required for all API endpoints
- **Environment Isolation**: Strict separation of DEMO and LIVE
- **Safe Write Gates**: Multiple validation checks before mutations
- **Audit Logging**: Complete tracking of all write operations

## 📊 Current Status

**Version**: 1.4.1  
**Status**: Active Development  
**Current Phase**: Phase 5 (Feedback Loop) - In Progress

### Completed Features

- ✅ Shopify Bulk Client (async, with Redis locks)
- ✅ Bulk Mutations with Safe Tag Merge
- ✅ FastAPI REST API with authentication
- ✅ n8n workflow integration
- ✅ Meta Ads data collection
- ✅ Shopify order attribution
- ✅ Feedback loop analysis engine

### In Progress

- 🚧 LLM-powered SEO challenger generation
- 🚧 Automated A/B test execution
- 🚧 CI/CD pipeline setup

## 🤝 Contributing

This is a private project under active development. Please coordinate with the project team before making changes.

### Development Guidelines

1. **Never commit directly to `main`**
2. **Always create feature branches** (e.g., `feat/phase3-api-endpoint`)
3. **Use semantic commit messages** (e.g., `feat:`, `fix:`, `docs:`)
4. **Update documentation** for all user-facing changes
5. **Run tests** before submitting changes

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For questions or issues:

1. Check the [documentation](docs/)
2. Review [ACCEPTANCE_TESTS.md](docs/ACCEPTANCE_TESTS.md) for verification procedures
3. Contact the development team

## 🔗 Related Projects

- **PEG (Legacy)**: Original inventory management system
- **EcomAgent (Legacy)**: Original SEO generation engine

---

**Built with**: FastAPI • Python • Redis • Shopify GraphQL • Meta Marketing API • n8n
