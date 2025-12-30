# APEG: Autonomous Product Extraction & Generation (Unified Engine)

## 1. Project Overview
This repository hosts the **Master Agent** combining two legacy systems:
1.  **PEG (Inventory Logic):** Deterministic inventory management and synchronization.
2.  **EcomAgent (SEO/Content):** Probabilistic content generation and optimization.

**Goal:** Build a unified, async-first orchestrator (`APEG Core`) that wraps these legacy capabilities to manage Shopify and Etsy stores autonomously.

---

## 2. Repository Structure & Context
The root workspace contains three distinct directories. **Agents must understand the role of each:**

### 📂 `APEG/` (Target Repository)
* **Role:** The **Active Build Directory**. All new code, refactoring, and integration work happens here.
* **Status:** Active Development.
* **Constraint:** This is the *only* directory where write operations should occur for the new system.

### 📂 `PEG (Merge)/` (Reference Only)
* **Role:** Legacy Codebase 1. Contains the original inventory logic and sku matching.
* **Status:** Read-Only Reference.
* **Action:** Copy logic/patterns from here; do not modify in place.

### 📂 `EcomAgent (Merge)/` (Reference Only)
* **Role:** Legacy Codebase 2. Contains the SEO generation engine and validatiors.
* **Status:** Read-Only Reference.
* **Action:** This logic is being wrapped (not rewritten). Refer to it for import structures.

---

## 3. Documentation & "Source of Truth"
All critical context is located in `APEG/docs/`.

| File | Purpose | Agent Instruction |
| :--- | :--- | :--- |
| **`PROJECT_PLAN_ACTIVE.md`** | **Active Work Queue** | **READ FIRST.** Contains the immediate "ToDo" list and current phase status. |
| `integration-architecture-spec-v1.4.md` | **Architecture Ref** | **The Law.** Defines the topology, constraints, and data models. |
| `ENVIRONMENT.md` | **Config Guide** | Defines required env vars for Demo vs. Live modes. |
| `ACCEPTANCE_TESTS.md` | **Verification** | Log verification evidence here before closing tasks. |

---

## 4. Development Protocols (Strict)

### Git & Branching
* **NEVER** commit directly to `main`.
* **ALWAYS** create a feature branch for every Work Package (e.g., `feat/phase1-bulk-client`).
* **Commit Messages:** Must be semantic (e.g., `feat: ...`, `fix: ...`, `docs: ...`).

### Execution Constraints
1.  **Async First:** The Master Agent is Async (FastAPI). Synchronous legacy code must be wrapped in `asyncio.to_thread`.
2.  **No Hallucinations:** Do not invent APIs. Check `EcomAgent (Merge)` and `PEG (Merge)` for existing implementation details.
3.  **Safety Locks:** Never overwrite `.env` files. Update `.env.example` only.
