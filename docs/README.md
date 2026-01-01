# APEG Documentation Index

> **📍 You are here:** `/docs/README.md` - Documentation navigation guide  
> **🏠 Main README:** See [../README.md](../README.md) for project overview and quick start

---

## 📖 Table of Contents

- [Quick Links](#quick-links)
- [Core Documentation](#core-documentation)
- [Operational Guides](#operational-guides)
- [Development Resources](#development-resources)
- [Research & Planning](#research--planning)

---

## 🔗 Quick Links

| What do you want to do? | Document to read |
|--------------------------|------------------|
| **Get started with APEG** | [../README.md](../README.md) - Project overview & installation |
| **Configure environment** | [ENVIRONMENT.md](ENVIRONMENT.md) - Environment variables guide |
| **Use the API** | [API_USAGE.md](API_USAGE.md) - API endpoints & examples |
| **Check current progress** | [PROJECT_PLAN_ACTIVE.md](PROJECT_PLAN_ACTIVE.md) - Active work queue |
| **Understand architecture** | [integration-architecture-spec-v1.4.1.md](integration-architecture-spec-v1.4.1.md) - Complete spec |
| **Set up n8n workflows** | [N8N_WORKFLOW_CONFIG.md](N8N_WORKFLOW_CONFIG.md) - Workflow configuration |
| **Run tests** | [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md) - Test specifications |

---

## 📚 Core Documentation

### Essential Reading

1. **[PROJECT_PLAN_ACTIVE.md](PROJECT_PLAN_ACTIVE.md)** - Active Work Queue  
   ⭐ **READ FIRST.** Current phase status, immediate ToDo list, and phase completion criteria.

2. **[integration-architecture-spec-v1.4.1.md](integration-architecture-spec-v1.4.1.md)** - Architecture Reference  
   📐 **The Law.** Complete system topology, constraints, data models, and specifications.

3. **[ENVIRONMENT.md](ENVIRONMENT.md)** - Configuration Guide  
   🔧 Required environment variables for DEMO vs. LIVE modes, security rules, and swap procedures.

4. **[ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md)** - Test Specifications  
   ✅ Test-to-spec mapping, verification procedures, and evidence logging.

5. **[CHANGELOG.md](CHANGELOG.md)** - Change History  
   📝 Spec fixes, feature additions, and test evidence log.

---

## 🛠️ Operational Guides

### API & Integration

- **[API_USAGE.md](API_USAGE.md)** - REST API Documentation  
  HTTP endpoints, authentication, request/response formats, and curl examples.

- **[N8N_WORKFLOW_CONFIG.md](N8N_WORKFLOW_CONFIG.md)** - n8n Integration Guide  
  Workflow setup, credential configuration, and troubleshooting.

### Testing & Verification

- **[PHASE2_INTEGRATION_VERIFICATION.md](PHASE2_INTEGRATION_VERIFICATION.md)** - Phase 2 Test Report  
  Safe write verification and integration test results.

- **[PHASE2_INTEGRATION_TEST_PLAN.md](PHASE2_INTEGRATION_TEST_PLAN.md)** - Phase 2 Test Plan  
  Test scenarios and execution procedures.

- **[../tests/integration/README.md](../tests/integration/README.md)** - Integration Test Guide  
  Environment setup, safety gates, and test execution instructions.

---

## 👨‍💻 Development Resources

### Repository Structure

```
APEG/
├── README.md                  # Project overview & quick start
├── .env.example              # Environment template (committed)
├── .gitignore                # Ignored files
├── requirements.txt          # Python dependencies
├── pytest.ini                # Test configuration
├── docs/                     # 📁 Documentation (you are here)
│   ├── README.md            # This file
│   ├── PROJECT_PLAN_ACTIVE.md
│   ├── integration-architecture-spec-v1.4.1.md
│   ├── ENVIRONMENT.md
│   ├── API_USAGE.md
│   ├── N8N_WORKFLOW_CONFIG.md
│   ├── ACCEPTANCE_TESTS.md
│   ├── CHANGELOG.md
│   └── Research/            # Planning & research documents
├── src/                      # 📁 Source code
│   └── apeg_core/           # Main application
│       ├── main.py          # FastAPI entry point
│       ├── api/             # REST API routes
│       ├── shopify/         # Shopify clients
│       ├── metrics/         # Metrics collection
│       └── feedback/        # Feedback loop engine
├── tests/                    # 📁 Test suite
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── scripts/                  # 📁 Utility scripts
└── data/                     # 📁 Data storage (gitignored)
```

### Development Protocols

**Git & Branching**
- ❌ **NEVER** commit directly to `main`
- ✅ **ALWAYS** create feature branches (e.g., `feat/phase3-api-endpoint`)
- ✅ Use semantic commit messages: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`

**Code Standards**
- ✅ **Async First:** APEG Core is async (FastAPI). Wrap sync code in `asyncio.to_thread`.
- ✅ **No Hallucinations:** Don't invent APIs. Reference legacy systems for implementation details.
- ✅ **Safety Locks:** Never overwrite `.env` files. Update `.env.example` only.

**Testing Requirements**
- ✅ Run unit tests: `PYTHONPATH=. pytest tests/unit/ -v`
- ✅ Run integration tests with DEMO credentials
- ✅ Log test evidence in [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md)

---

## 🔬 Research & Planning

Historical planning documents and research notes:

- **[Research/Master-BuildPlan.md](Research/Master-BuildPlan.md)** - Original master plan
- **[Research/Agent Development Lifecycle.md](Research/Agent Development Lifecycle.md)** - Agent development process
- **[Research/Researching Project Implementation Details.md](Research/Researching Project Implementation Details.md)** - Implementation research
- **[Research/APEG EcomAgent Merger Feasibility Report.md](Research/APEG EcomAgent Merger Feasibility Report.md)** - Merger analysis
- **[Project_Plan_Draft1.md](Project_Plan_Draft1.md)** - Original project plan (superseded by PROJECT_PLAN_ACTIVE.md)

---

## 📌 Important Notes

### Legacy Systems Context

The APEG workspace may reference two legacy codebases:

1. **📂 `PEG (Merge)/`** - Legacy inventory logic (Read-Only Reference)
2. **📂 `EcomAgent (Merge)/`** - Legacy SEO engine (Read-Only Reference)

These directories are external references. **All new development happens in the APEG repository.**

### Environment Profiles

APEG supports two environment profiles:

- **DEMO**: Development/testing against development stores
- **LIVE**: Production against live stores

See [ENVIRONMENT.md](ENVIRONMENT.md) for configuration details and swap procedures.

---

## 🆘 Need Help?

1. **Configuration issues?** → [ENVIRONMENT.md](ENVIRONMENT.md)
2. **API questions?** → [API_USAGE.md](API_USAGE.md)
3. **Test failures?** → [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md) + [../tests/integration/README.md](../tests/integration/README.md)
4. **Architecture questions?** → [integration-architecture-spec-v1.4.1.md](integration-architecture-spec-v1.4.1.md)
5. **Current status?** → [PROJECT_PLAN_ACTIVE.md](PROJECT_PLAN_ACTIVE.md)

---

**Last Updated:** 2026-01-01  
**Spec Version:** 1.4.1  
**Status:** Active Development
