PROJECT_PLAN_SETUP.md
APEG Repository Bootstrap and Phase Plan
Repository Scaffolding and Setup

To initiate the new APEG repository (merging APEG core with EcomAgent functionality), we will scaffold the project in a logical order:

Initialize Project Structure: Begin with a modern Python package layout. Create a pyproject.toml with PEP 621 metadata (using APEG’s existing MIT license and dependencies). Establish the core package directory, e.g. src/apeg_core/, mirroring the structure from the PEG project
GitHub
. Include subpackages for critical domains:

apeg_core/orchestrator.py (workflow engine entry point)

apeg_core/agents/ (specialized agents for Shopify, Etsy, etc.)

apeg_core/connectors/ (for external API clients or tool interfaces)

apeg_core/logging/, decision/, memory/, scoring/ (as in PEG for consistency)
This provides a skeleton to start adding code. Commit this scaffold as the first step.

Port Core Components: Bring over the non-domain-specific core from PEG. This includes the orchestrator logic, loop detection, bandit decision module, base agent classes, and any generic connectors (OpenAI connector, filesystem, etc.)
GitHub
GitHub
. By doing this early, we get the “deterministic backbone” of APEG in place (the engine that will run workflows). Verify basic operations with existing tests (adapt PEG’s tests to the new package structure) to ensure the core is intact.

Integrate Domain Modules: Next, incorporate the EcomAgent-specific pieces:

SEO Engine Module: Add the seo_engine components from EcomAgent (e.g. engine.py, guard.py, backup_manager.py, etc.) into apeg_core/agents or a dedicated apeg_core/domain/seo/ directory. These provide the deterministic logic for SEO optimization that was proven in Phase 1 (Shopify SEO sweep).

Shopify Connector: Include the official Shopify Python API library (ShopifyAPI) as a dependency and create a connector class to wrap it (for example, a ShopifyConnector in apeg_core/connectors/). This class can manage Shopify sessions and calls (fetch products, update products) and enforce the API version.

Data Models: Define lightweight data classes or Pydantic models for common entities (Product, Variant, etc.) consistent with the SEO_ENGINE_CONTRACT schema. This will help translating between Shopify data and the agent’s expected input.

Configuration and Constants: Add configuration files and constants early:

A config/ directory for things like API keys (.env file) and any static mappings. Copy over the rules/seo_baseline.yaml (SEO safety rules) from EcomAgent
GitHub
 into the new repo under config/ or similar. This ensures guardrails (max lengths, banned words, etc.) are available.

Prepare a placeholder for CPM_mapping.json (Common Product Model mapping) – see below for details – under config/ or data/.

With this scaffolding complete, the repository should build and import successfully. Validate by running pip install -e . and a simple import apeg_core test. At this point, we have an empty shell ready for the phased build-out.

Phase-by-Phase Build Sequence

We will implement the system in incremental phases, each building a working subset of functionality. Each phase’s goal is to have a stable, testable “Definition of Done” before moving on.

Phase 0: Environment and CI Setup (Bootstrap)

Goal: Set up development infrastructure to ensure smooth building and quality control.
Tasks:

Configure Shopify API access: Load credentials from environment or .env (Shop URL, Admin API token) and instantiate the Shopify API session in the connector. Pin the API version explicitly – for example, use the latest stable (2025-10 initially, and plan for 2026-01 when it’s out) to avoid breaking changes. In code, call shopify.Session.setup(api_version="2025-10") or the equivalent in the Python API to lock this version.

Continuous Integration: Add a GitHub Actions workflow (.github/workflows/ci.yml) that installs the package, runs tests, and lints the code on each push. Include steps for Static Code Analysis (SCA) – e.g. run a linter (flake8/pylint) and security scans. Also configure license scanning if possible (to catch any GPL dependencies creeping in).

Testing Framework: Verify that the PEG unit tests ported over still pass. Adjust paths in tests if needed for the new package name. Establish a pattern for writing new tests as we add features (e.g., under tests/ directory).

Definition of Done (Phase 0): Repository builds, basic tests run in CI, and environment variables for Shopify are loaded without errors. No functional features yet, but the pipeline is green.

Phase 1: Deterministic Shopify SEO Backbone

Goal: Implement the end-to-end Shopify SEO Sweep using deterministic code (no AI decisions yet beyond what’s already coded) – essentially replicating EcomAgent’s Flow A within APEG’s structure.
Tasks:

Product Data Fetch: Use the ShopifyConnector to retrieve a batch of products based on criteria. For now, implement collection or tag filtering using the Shopify REST API (since batch size is small, REST is acceptable). Ensure we respect the selection_strategy (collection, tag, or list of IDs) and batch_size limits as per spec.

Mapping to SEO Contract: Implement the mapping function that transforms a Shopify product into the SEO_ENGINE_CONTRACT request format. This should follow the Flow A – SEO_MAPPING spec precisely (e.g., populate id, channel="shopify", title, description, etc. including assembling variant attributes and images). This can be a pure function or a method in a ShopifyAgent class. Write unit tests with a sample product JSON to ensure the mapping output matches expected contract fields.

SEO Engine Deterministic Call: Integrate the seo_engine.engine (from EcomAgent) as a black-box function for now. In Phase 1, we can call SEOEngine.generate_seo(product_contract) which returns the new SEO fields (this might internally call OpenAI API, but with fixed prompts – effectively it’s deterministic from our orchestrator’s view). Alternatively, if we want to avoid any external calls in this phase, stub the SEO generation with a rule-based placeholder (for testing). The key is that we exercise the pipeline: input product -> transformed contract -> (dummy) SEO output.

Apply Changes to Shopify: Implement the logic to update Shopify with the new fields in test mode. This means we prepare the payload but do not execute the write if mode=test. We log the intended changes instead. For example, if apply_changes comes back true, format the update via shopify.Product object updates (title, body_html, tags, metafields) but skip the save() when in dry-run. (In live mode, we will call save() or the GraphQL mutation – that will be Phase 2 when we’re confident).

Logging: For each processed product, record an entry (maybe to a JSONL file or console for now) that includes product ID, old vs new title/description/tags, status, and whether changes were applied. This replicates EcomAgent’s logging and will help verify correctness.

Definition of Done (Phase 1): We can run an end-to-end test on a small set of products (e.g., 1–3 products) in test mode and see in logs that: the product data was fetched, the SEO engine returned new fields, and the system prepared the correct updates without applying them. All transformations should match the spec (e.g., tags normalized, no fields missing). No AI autonomy yet – this is a controlled execution.

Phase 2: Introduce SEO Agent (OpenAI Agents SDK)

Goal: Evolve the SEO Engine from a deterministic function into an AI agent tool, while still keeping the system deterministic at the orchestration level. This phase integrates the OpenAI Agent SDK for the SEO generation step, using the rules and contract we’ve established.
Tasks:

Tool Definition for SEO Engine: Define the SEO optimization as an agent tool. For the OpenAI Agents SDK, this might mean describing a function optimize_seo_record(input: SEOContract) -> SEOContractResponse. We will expose this to the agent either via the SDK’s function interface or a local API. Here is where the openapi.yaml comes into play: create a minimal OpenAPI spec that defines an endpoint or function for SEO optimization (and possibly a stub for Shopify updates if we ever let the agent call that directly). This spec will be used by the agent to know how to call the tool.

OpenAPI Stub: Example: Define a path /optimize_seo that accepts a POST with a JSON body matching the SEO_ENGINE_CONTRACT request and returns the response. Mark this in openapi.yaml so the agent can see the input/output schema. (The agent might actually use the function directly if we integrate via SDK, but having a spec is useful for clarity and testing.)

Agent Codec and Parsing: Develop the agent_codec.json which maps the agent’s outputs to our internal structures. For instance, if using function calling, the agent will return a JSON adhering to the response schema – the codec can be a simple identity mapping for now (the JSON already matches our Pydantic model). However, if the agent might output text that needs parsing (not recommended here), the codec would parse it. For safety, we implement validators (or use the existing validators/guard.py) to verify the agent’s response respects length limits, etc., before accepting it.

Transition Logic: Initially, run the agent in a controlled manner. Perhaps use APEG_TEST_MODE=true (as seen in PEG’s usage
GitHub
) which could instruct the system to use stubbed AI responses. Gradually toggle to real OpenAI calls once the integration is stable. We will also incorporate the brand voice and rules into the agent’s prompt (e.g., provide the contents of seo_baseline.yaml – tone, banned_words – as system instructions to the agent).

Apply Changes (Live Mode): In this phase, enable the ability to actually perform updates in Shopify in a guarded way. Implement a check such that if mode=live and apply_changes=true from the agent, the connector will perform the product.save() (or GraphQL mutation) to update SEO fields on Shopify. Use try/except around this call; log any API errors with detail. Keep the batch size low and perhaps introduce a slight delay between updates to respect rate limits.

Testing: Use a development shop to test the agent integration. Start with mode=test runs to see that the agent receives correct input and produces reasonable output. Then try a mode=live run on a very small batch (1 product) to ensure the update goes through to Shopify. All the while, verify that the changes respect constraints (e.g., titles truncated at 70, no banned words – the guard should catch any violation before saving).

Definition of Done (Phase 2): The system can autonomously optimize a product’s SEO text and apply it on Shopify, with all safety nets in place. The OpenAI agent is successfully integrated: it uses the contract as input, follows the rules, and output changes get applied. Importantly, CI tests should cover a simulated agent response (perhaps via a fixture) to exercise the parsing and guard logic without calling the real API each time.

Phase 3: Multi-Agent Orchestration & Multi-Channel Extension

Goal: Expand APEG from a single-agent workflow to a multi-agent, multi-step orchestration, and introduce Etsy (or other channels) using the common model. This phase moves closer to the full “APEG orchestrator” vision with multiple specialized agents and a durable graph execution (LangGraph integration for long runs).
Tasks:

Workflow Graph Definition: Design a WorkflowGraph.json (or similar structure) for the end-to-end process. This could include nodes like: FetchData (ShopifyAgent) -> SEOOptimize (SEO Agent) -> Validate (Validator Agent) -> ApplyChanges (Apply Agent) -> LogResults (Logger). We formalize this so that APEG’s orchestrator can execute it. If using LangGraph or a similar library, compile this workflow with a checkpointer to allow pause/retry. For now, the graph is simple and linear, but this prepares for future complexity.

Domain Agents for Shopify and Etsy: Implement a Shopify Agent and Etsy Agent within apeg_core/agents/. These would be lightweight wrappers that know how to perform domain-specific tasks. For Shopify Agent, tasks include “get product by ID”, “update product SEO fields”, etc. For Etsy Agent, tasks would parallel (listings instead of products). Equip these agents with the ability to interpret the Common Product Model (CPM). This means if the orchestrator hands a “Product” object from Shopify or Etsy, the agent can map it to the common schema and back. Use the CPM_mapping.json stub to drive this mapping.

CPM Mapping: Flesh out CPM_mapping.json such that it defines fields like title, description, tags, etc., and maps where Shopify gets them vs. Etsy. Example structure:

{
  "title": {
    "shopify": "product.title",
    "etsy": "listing.title"
  },
  "description": {
    "shopify": "product.body_html",
    "etsy": "listing.description"
  },
  "tags": {
    "shopify": "product.tags",
    "etsy": "listing.tags"
  }
  // ... etc.
}


This file ensures the agents and orchestrator speak a unified language. When the Shopify Agent fetches data, it converts it to a CPM-compliant dict before passing to the SEO Agent. Conversely, when the SEO Agent returns new fields, the Shopify Agent knows how to apply them on the Shopify API, and the Etsy Agent would know the Etsy API calls/fields.

Persistence (LangGraph Checkpoint): Integrate a checkpointing mechanism for long workflows. This is forward-looking for large catalogs. For now, setting up a simple SQLite DB or file to save state after each product processed is sufficient. Create a langgraph_checkpoint.sql schema (or use LangChain’s checkpoint interface
docs.langchain.com
) to store progress. For example, a table checkpoint(run_id, last_product_index) or full JSON of workflow state. This ensures that if the process stops or needs to pause (especially when hundreds of products or multiple agents are involved), it can resume without starting over.

Etsy Integration Test (if scope allows): Once the common model and Etsy Agent are in place, do a dry-run integration for Etsy. Possibly do not apply changes (because we may not have a non-GPL solution ready yet), but simulate pulling an Etsy listing (using a personal API key in test) and running it through the SEO agent to see the output. This will flush out any mismatches in CPM mapping and ensure the architecture supports a second channel. Keep this behind a feature flag if needed (so Etsy path is not active until licensing is sorted).

Definition of Done (Phase 3): The orchestrator can handle a flow with multiple agents in sequence, and the design supports both Shopify and Etsy inputs. We should demonstrate a full run in Shopify (multiple products sequentially, automatically handled by the workflow loop) and show that the system could extend to Etsy by mapping an Etsy listing to the same SEO contract (even if not applying changes on Etsy yet). The system is now a generalized, AI-driven workflow orchestrator.

Phase 4: Hardening and Safety Expansion

Goal: Before considering the project ready for production use, enforce additional guardrails, testing, and monitoring as per the original plan’s Phase 4.
Tasks:

Error Handling & Notifications: Implement robust exception handling around each agent call and API operation. If an error occurs (Shopify API error, OpenAI error, etc.), the system should catch it, log it, and possibly notify (e.g., prepare an email or Slack message via a webhook). Since this is an open-source personal project, a simpler approach is fine: e.g., log to a file error.log and ensure the run continues to the next item or stops gracefully.

Performance Monitoring: Add timing logs or counters to measure how long each product takes to process. On a Raspberry Pi, this is crucial to avoid overload. Potentially introduce a cooldown or batching mechanism if too many products are processed in one go.

Quality Assurance Gates: Use the scoring mechanism from PEG if applicable – e.g., incorporate the Scorer agent to rate the quality of the SEO output. For instance, after SEO Agent returns results, have a lightweight rule-based scorer (or even an LLM-based one if not too costly) that scores clarity or checks that the output isn’t identical to input. If below threshold, flag it for review rather than applying. This “adoption gate”
GitHub
 ensures only meaningful improvements go live.

User Approval Mode: Given this is an automation for your own store, implementing a manual checkpoint could be valuable. For example, after generating changes but before applying, output a summary to a Google Sheet or dashboard for a quick eyeball. This wasn’t in original scope for v1, but as a safety measure in production it’s wise. You could make this an optional step (apply_changes = false for all, and require a manual flip to true via the log for each product). Document how an operator could use this if needed.

Definition of Done (Phase 4): The system has run in a prolonged test and possibly live mode without incident. All known error cases (Shopify timeouts, API quota hits, OpenAI errors, ill-formed agent output) have been simulated or tested, and the system handled them gracefully (no crashes, informative logs). Non-functional requirements like performance on Pi and memory usage are within acceptable bounds.

Phase 5: Future Enhancements (Post-Merger)

(This phase is more of a roadmap for beyond the immediate merger. It can be documented but not implemented yet.)

Etsy Full Integration: Once the licensing path is decided, fully enable Etsy updates analogous to Shopify’s. This could mean using Etsy’s OpenAPI (if available) to generate a small internal client, or wrapping the GPL library calls in a separate process. The groundwork from Phase 3 will make this straightforward – essentially just plugging in the actual update mechanism in the EtsyAgent.

Sidekick/MCP Integration: Optionally, explore using the Shopify Dev MCP server for development automation. For example, incorporate a script or mode where the dev MCP is used to auto-generate GraphQL queries or to validate our GraphQL mutations against the latest schema. This can ensure our openapi and CPM remain up-to-date with Shopify’s evolving API (the dev MCP can act as a real-time schema reference
shopify.dev
).

AI Storefront Assistant: The architecture could be extended to a storefront-facing agent (Shopify Sidekick-like) using Storefront MCP, but that’s a separate application. We note it as a possibility (utilizing APEG’s multi-agent core for a chatbot that can answer product questions using the same data).

Each phase above should be merged into main only after meeting its Definition of Done, ensuring we always have a working baseline. This phased approach aligns with the original plan’s idea of “small, testable increments” and provides clear checkpoints.

Shopify API Version Pinning

We will pin the Shopify Admin API version in the integration to avoid surprises. The Shopify Python API allows specifying a version – we’ll set it to the latest stable supported. For example, start with '2025-10'. When 2026-01 is released and tested, update the pin to '2026-01'. All GraphQL queries or REST endpoints will thus target a known version. Additionally, monitor the [Shopify developer changelog] for any required upgrades
shopify.dev
. The codebase should include this version in a single config place (to ease future upgrades).

Rationale: Pinning protects us from unannounced breaking changes. We’ll plan routine upgrades each quarter when Shopify releases a new version, using the changelog to catch deprecations (like the bulk operation changes).

Utilizing Shopify Dev MCP for Schema Alignment

While not required for normal operation, the Shopify Dev MCP server is a useful tool during development. We can use the Dev MCP to fetch the latest GraphQL Admin schema and compare it against our openapi.yaml or internal models. For instance, before finalizing the openapi spec for Shopify calls, use dev-mcp to query the Admin API schema (introspection) to ensure all fields (like metafields, SEO fields) are correctly represented. This is especially helpful when adding new capabilities – it’s like having an always-up-to-date reference. We might document a script or step (non-production) to run the dev MCP and update our schema files. In summary, MCP is a development aid: it does not affect runtime, but keeps our integration aligned with Shopify’s latest data model
shopify.dev
. (For the Etsy side, we’ll rely on their OpenAPI v3 documentation similarly.)

Continuous Integration, SCA, and Testing Strategy

From the start, we enable CI to catch issues early:

The ci.yml GitHub Actions workflow will run on every push/PR. It installs the package, then runs:

Unit Tests: Using pytest, covering mapping logic, agent output validation, and any utility functions. We will include sample payloads (perhaps saved under tests/data/) for Shopify product, SEO contract request, etc., to test transformations in isolation. As we add agents, we’ll add tests for agent behaviors with stubbed outputs (e.g., simulate the OpenAI response JSON to test our parsing and guard logic in a deterministic way).

Linting/Formatting: Enforce PEP8 via flake8 and maybe black (in check mode). This keeps code quality high.

Static Code Analysis (SCA): Run a security scanner (like bandit) to catch common security issues or a license checker. We will configure sca_config.json to define allowed license types for dependencies (e.g., MIT, BSD, Apache are OK, but flag GPL). For example:

{
  "allowed_licenses": ["MIT", "BSD", "Apache-2.0", "ISC", "Unlicense"],
  "forbidden_licenses": ["GPL-3.0", "AGPL-3.0"]
}


This config can be used in a CI step with a license scanning script to ensure we don’t inadvertently add a forbidden dependency.

Coverage: Optionally, measure test coverage and fail the build if it drops below a threshold (say 80%). This encourages us to write tests as we implement each phase.

Integration Testing: For phases that involve actual API calls (Shopify or OpenAI), we won’t run those in every CI (to avoid external dependencies and costs). Instead, we can have a separate workflow or manual trigger for integration tests. E.g., a nightly build that runs a full flow in test mode against a dev store and verifies no errors. This could be as simple as invoking the main pipeline with a dry-run and checking the exit code.

By Phase 4, our CI should also run any style or quality tools (like mypy for type checking if we adopt it). The goal is to catch regression early, especially as we integrate multiple components (AI, web APIs, etc.).

Definition of Done & Safety Gates per Phase

We establish an agent-safe Definition of Done for each build phase to ensure we don’t progress with hidden issues:

Phase 1 DoD: The core flow runs deterministically. Safety check: In test mode, ensure no real writes happen to Shopify. Confirm logs are capturing all changes (this doubles as a safety net – by manually reviewing logs, we verify the system would have done the right thing).

Phase 2 DoD: The AI agent produces outputs that pass our validators. Safety check: All outputs from OpenAI are validated by guard.py (lengths, banned words) before any attempt to apply to Shopify. The system should automatically set apply_changes=false or adjust outputs if constraints are violated, and log a note. We also ensure that even in live mode, a final check requires apply_changes == true to execute an update. Essentially, the agent cannot cause an update unless it explicitly indicates and all rules are satisfied.

Phase 3 DoD: The multi-agent workflow functions as intended. Safety check: Introduction of multiple agents (e.g., a Validator agent after SEO agent) means we don’t blindly trust a single agent’s output. By design, the Validator (or our guard logic) must approve the SEO suggestions. The Definition of Done here includes that a simulated “bad” SEO output (e.g., one containing a banned word or nonsense) is caught and not applied. We should test this scenario.

Phase 4 DoD: The system is robust and “safe to run unattended.” Safety check: At this stage, an operator could let the workflow run overnight on a schedule. The criteria for done would be:

It handles network/API failures by skipping or retrying without stalling the whole run.

There is an audit trail (logs or backup file) for every change, enabling manual rollback if needed.

Any “edge” decisions (like apply vs skip minor improvements) are clearly logged, so no silent logic is happening without visibility.

The maintainer (you) has confidence that the agent won’t go rogue – this confidence comes from the layered checks: schema enforcement (agent can only output allowed fields), validation agent/logic, dry-run mode availability, and small batch sizes.

Phase 5 (Post-merge readiness): Although not an immediate phase, before declaring the merged project fully complete, consider a final checklist:

Documentation updated (README explains how to use the new system, how to configure API keys, etc.).

Example config files provided (like openapi.yaml, agent_codec.json, etc., all filled with at least minimal working content).

Community standards met (if open-sourced, no sensitive info in code, clear contribution guidelines).

Each phase’s completion should be reviewed (ideally by actually running the system in a safe environment) to ensure the above conditions are met. Only proceed to the next phase when the system’s behavior is deterministic or properly controlled at the current level. This stepwise tightening of trust boundaries ensures that by the time we allow fully autonomous operation, the system has proven itself in constrained scenarios.

Key Artifacts – YAML/JSON Stub Specifications

As part of the setup, we prepare stub files that will be fleshed out during implementation. These act as both configuration templates and reminders to implement certain integration pieces:

openapi.yaml – Shopify/Etsy API Tool Spec: A stub OpenAPI 3.0 file listing the endpoints or functions the agent can call. For example:

openapi: "3.0.3"
info:
  title: "APEG E-commerce Tools API"
  version: "0.1.0"
paths:
  /optimize_seo:
    post:
      summary: "Optimize product SEO text"
      requestBody:
        content:
          application/json:
            schema: 
              $ref: "#/components/schemas/SEORequest"
      responses:
        "200":
          description: "SEO optimization result"
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SEOResponse"
components:
  schemas:
    SEORequest:
      type: object
      properties:
        id: { type: string }
        channel: { type: string, example: "shopify" }
        product_id: { type: string }
        title: { type: string }
        description: { type: string }
        tags: { type: array, items: {type: string} }
        # ... (other fields like current_seo, attributes, etc.)
    SEOResponse:
      type: object
      properties:
        status: { type: string }
        new_title: { type: string }
        new_description: { type: string }
        new_tags: { type: array, items: {type: string} }
        apply_changes: { type: boolean }
        # ... (other fields like new_meta_title, notes, etc.)


Stub content: Basic schema definitions for SEO request/response as per SEO_ENGINE_CONTRACT. This will be expanded with any additional endpoints (e.g., perhaps a /update_shopify_product if we let the agent trigger an update via API, though initially we may not allow direct agent calls to update). This file ensures we have a formal contract for agent-tool interactions.

agent_codec.json – Agent Tool Codec: A stub JSON defining how to encode/decode agent actions. For instance:

{
  "tools": [
    {
      "name": "optimize_seo",
      "input_schema": "SEORequest",
      "output_schema": "SEOResponse",
      "call": {
        "type": "function", 
        "endpoint": "/optimize_seo",
        "method": "POST"
      }
    },
    {
      "name": "update_product",
      "input_schema": "ShopifyUpdate",
      "output_schema": "UpdateResult",
      "call": {
        "type": "api",
        "client": "shopify",
        "method": "Product.save"
      }
    }
  ]
}


Stub content: An array of tool definitions the agent might use. The above example shows an optimize_seo tool that corresponds to the openapi endpoint, and an update_product tool that is more pseudocode (since updating via the SDK isn’t an HTTP call, we might not expose it directly to the agent in early phases). This codec file will be used by the orchestrator to interpret an agent’s plan – e.g., if the agent says “call optimize_seo with X”, the orchestrator knows to package X as per SEORequest schema and send it to the SEO engine (or call the function). Filling this out will come as we decide which actions the agent is allowed to perform autonomously.

CPM_mapping.json – Common Product Model Mapping: Initial stub to map fields between platforms. For example:

{
  "title": { "shopify": "product.title", "etsy": "listing.title" },
  "description": { "shopify": "product.body_html", "etsy": "listing.description" },
  "tags": { "shopify": "product.tags", "etsy": "listing.tags" },
  "images": { "shopify": "product.images", "etsy": "listing.images" },
  "seo_title": { "shopify": "product.metafields_global_title_tag", "etsy": "listing.title" },
  "seo_description": { "shopify": "product.metafields_global_description_tag", "etsy": "listing.description" }
}


Stub content: Key product attributes and where to get them for each platform. This serves as documentation and lookup for the code. We will refine it (for instance, Etsy might have no direct “SEO title” field separate from listing title, so it might just mirror title). The stub includes at least the fields we know we care about. Later, we might extend it with field transformations (e.g., Shopify HTML description vs Etsy plain text – the agent might need to strip HTML for Etsy, etc. – those rules can be noted here or in code).

CI workflow (ci.yml) – Continuous Integration Pipeline: A YAML stub for GitHub Actions. For example:

name: APEG CI
on: [push, pull_request]
jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run lint
        run: flake8 .
      - name: Run tests
        run: pytest


Stub content: Basic steps for installing and testing. We will expand this with the SCA steps (e.g., after lint, add a step to run a license check script using sca_config.json). Also possibly add a matrix to run on multiple Python versions if needed (3.11 and 3.12). Initially, the stub ensures at least the tests and linter run.

sca_config.json – Static Analysis Configuration: As noted, this might contain license allow/deny lists or security check settings. Our stub (from above) lists allowed vs forbidden licenses. We might also include known false-positives for bandit to ignore. For instance:

{
  "allowed_licenses": ["MIT", "BSD", "Apache-2.0", "ISC", "Python-2.0"],
  "forbidden_licenses": ["GPL-3.0", "AGPL-3.0", "LGPL-3.0"],
  "bandit": {
    "skips": ["B101"]  // example: skip assert usage check if not relevant
  }
}


This file will be read by custom CI scripts or tools.

langgraph_checkpoint.sql – LangGraph Checkpoint Schema: A SQL file stub to setup a checkpoint DB. For example:

-- SQLite schema for LangGraph checkpoints
CREATE TABLE IF NOT EXISTS checkpoint (
    id TEXT PRIMARY KEY,
    workflow_name TEXT,
    node_index INTEGER,
    state BLOB,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_checkpoint_workflow ON checkpoint(workflow_name);


Stub content: This defines a table to store the state of an ongoing workflow, keyed by a run ID or workflow instance ID. The state could be a blob of serialized data (perhaps JSON text of all agent states). In practice, LangGraph’s own checkpoint system might manage this, but having our own table gives us flexibility to query or clean up old runs. We include this stub mainly to signal the need for persistence. This file can be executed against a SQLite database on startup if persistence is enabled.

By preparing these stubs, we set the stage for implementing each piece in the appropriate phase. They will be gradually populated:

In Phase 1, we might not touch openapi.yaml yet (since we’re not agent-driving the API in Phase 1), but we will work on CPM_mapping.json if even in stub form to guide design.

Phase 2 will see a concrete openapi.yaml and agent_codec.json as we integrate the agent.

Phase 3 will refine CPM_mapping.json and might not need to change openapi.yaml unless we allow agent-initiated Shopify calls by then.

ci.yml and sca_config.json will be in use from Phase 0 onward, evolving as needed.

Finally, we will keep all these artifacts under version control in the APEG repo. This ensures transparency for any future contributors (or for yourself) to understand the system’s configuration and integration points.

Each stub will have documentation comments inside it (as exemplified above) to explain its purpose and how to use it, fulfilling a well-documented setup for the merged project.