Agent Development Lifecycle

1. The Process Framework: Agent Development Lifecycle (ADLC)
--
Phase 1: Ideation & Scoping (Defining the "Job to be Done")
Phase 2: Agent Design (Tools, memory, and logic flow)
Phase 3: Environment Setup (n8n credentials, API keys, schemas)
Phase 4: Evaluation & Simulation (Testing deterministic success vs. hallucination)
Phase 5: Observability (Logging token usage, error rates in n8n) 
--
2. The Master Document: Agent Design Specification (ADS)
You should create a master document (often in Markdown/Notion) with the following standard sections. This serves as the "Source of Truth" for both human and AI developers.

Section A: Identity & Role
Agent Name: (e.g., "EcomSync_Orchestrator")
Primary Objective: One sentence defining success (e.g., "Monitor Etsy orders every 15 minutes and sync new line items to Shopify inventory without duplication.")
Tone/Persona: (e.g., "Precise, JSON-oriented, purely functional.")

Section B: Tools & Capabilities (The "Action Layer")
For your specific stack, you must document the Schema Definitions the agent will use.

Tool 1: Shopify API:
Capability: write_inventory, read_orders
Constraint: "Must verify SKU existence before attempting update."

Tool 2: Etsy V3 API:
Capability: get_receipts
Constraint: "Rate limit is 10 requests/second; implementation must include error handling for 429 statuses."

Tool 3: n8n Webhooks:
Trigger: On New Order (Polling vs. Webhook)

Section C: Memory & State
Short-term: "Pass order JSON payload from trigger node to AI node."
Long-term: "Use a Redis or n8n binary data store to log processed_order_ids to prevent duplicate syncing."

Section D: Guardrails & Constraints
Budget: "Max 3 OpenAI calls per order execution."
Safety: "Never delete inventory; only archive."
Human-in-the-Loop: "If AI confidence score < 0.8 (e.g., fuzzy SKU matching), route to Slack for manual approval."
--
3. Supporting File Structure (Best Practice)
Organize your repository (or n8n project folder) using this emerging standard structure to keep context clear for AI coding assistants:
--
project-root/
├── agent.md                # (CRITICAL) The "Prompt Instruction for the AI Developer"
├── specs/
│   ├── prd.md              # Product Requirements Document (The "Why")
│   ├── technical-spec.md   # API Schemas, n8n Node Logic (The "How")
│   └── memory-structure.md # Database schema or State definition
├── context/
│   ├── etsy-api-docs.md    # Scraped/pasted relevant API docs
│   └── shopify-schema.json # Your shop's specific data structure
├── workflows/              # Exported n8n JSON workflows
│   ├── main_sync.json
│   └── subflow_error_handler.json
└── .env.example            # Template for required keys (NO REAL KEYS)
--
4. The "Instruction for the AI Developer": agent.md 
You asked for a standard for "prompt instruction for the AI developer." The standard practice is to create a file named agent.md in the root of your project.
This file tells the AI (Cursor, Windsurf, or a custom coding agent) how to behave specifically for this project. 
Example agent.md Content:
--
Role: You are a Senior Automation Engineer specializing in n8n and TypeScript.
Project Goal: Build a bi-directional sync between Etsy and Shopify using OpenAI for fuzzy data mapping.
--
Tech Stack Constraints:
Platform: n8n (Self-hosted v1.0+)
Language: JavaScript/TypeScript (inside Code Nodes)
AI Model: gpt-4o (via OpenAI node)
Coding Rules:
ALWAYS use n8n's built-in expression syntax {{ $json.field }} where possible.
When writing Code Nodes, always return an array of objects [{ json: { ... } }].
Never hardcode API keys; assume process.env or n8n Credentials.
Before suggesting a complex regex, prefer using the OpenAI node to parse unstructured text.
Context:
Refer to context/shopify-schema.json for exact field names.
Etsy API uses snake_case; Shopify uses camelCase. You must handle this conversion.