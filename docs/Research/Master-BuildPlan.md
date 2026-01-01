# **ARCHITECTURAL CONVERGENCE REPORT: AUTOMATED PRODUCT EXTRACTION & GENERATION (APEG) AND ECOMAGENT UNIFICATION PROTOCOLS**

## **1\. Executive Strategic Overview**

The integration of the legacy Automated Product Extraction & Generation (APEG) system with the modern EcomAgent artificial intelligence framework constitutes a paradigmatic shift in e-commerce automation. This initiative is not merely a consolidation of codebases but a fundamental reconciliation of two distinct technological philosophies: the "deterministic rigidity" of legacy rule-based automation and the "probabilistic autonomy" of modern Large Language Model (LLM) orchestration.

The urgency of this unification is driven by external platform evolution and internal scalability requirements. Shopify’s deprecation of REST-based inventory endpoints significantly threatens the operational viability of the legacy APEG system, which relies on a "leaky bucket" rate-limiting model insufficient for high-volume catalog management.1 Concurrently, the strategic necessity to deploy autonomous agents capable of navigating Etsy’s complex V3 API and Meta’s advertising ecosystem demands a robust, event-driven architecture that the current synchronous APEG codebase cannot support.1

This report serves as the definitive technical blueprint for the merger. It validates the architectural specifications against the harsh realities of the current codebase, identifies critical "missing artifacts"—ranging from canonical data models to infrastructure-as-code definitions—and prescribes a rigorous, multi-phase build plan. The analysis synthesizes data from internal feasibility reports, project alignment summaries, and external API documentation to ensure that the resulting "Guardrailed Autonomy" architecture is resilient, scalable, and auditable.

The central thesis of this convergence is the resolution of the "Synchronous-Asynchronous Impedance Mismatch." APEG’s reliance on blocking I/O operations, specifically through the requests library and ShopifyAPI wrapper, presents a catastrophic risk to EcomAgent’s FastAPI event loop. Without the precise hybrid concurrency patterns detailed herein, the integration risks deadlocking the entire agentic mesh, rendering the system unresponsive to real-time market signals. Furthermore, the adoption of a "Dual-Agent" development strategy—leveraging OpenAI Codex for local, sandboxed refactoring and Gemini Code Assist for enterprise-aware context—provides the methodology required to execute this complex migration securely.2

## ---

**2\. Legacy Architecture Audit: The APEG Foundation**

To successfully bridge the gap between APEG and EcomAgent, one must first dissect the anatomy of the legacy system. The analysis reveals a codebase optimized for a previous era of e-commerce API interaction, characterized by synchronous execution and rigid procedural logic.

### **2.1 The Synchronous Concurrency Model and I/O Bottlenecks**

The APEG backend operates on a synchronous, blocking I/O model, characteristic of traditional Python web frameworks such as Flask or Django utilizing a WSGI server interface. In this architecture, each incoming HTTP request is assigned a dedicated operating system thread. The execution flow is linear: the thread processes the request, makes external API calls, waits for the response, and then proceeds.

The critical vulnerability in this model lies in the handling of I/O-bound operations. When APEG initiates a request to Shopify or Etsy using the standard requests library, the thread executing that call is blocked entirely. It sits idle, consuming memory resources, until the external server responds. In high-latency environments—such as those involving complex GraphQL mutations or LLM inference—this blocking behavior leads to thread pool exhaustion. If the system attempts to scale to thousands of concurrent inventory updates, the server simply runs out of threads, causing new requests to queue or timeout.1

This stands in stark contrast to the target architecture of EcomAgent, which employs FastAPI and the Uvicorn ASGI server. EcomAgent utilizes a single-threaded event loop based on asyncio. This loop handles thousands of concurrent connections by yielding control during I/O waits, allowing other tasks to progress. The "Impedance Mismatch" occurs if legacy APEG functions are imported directly into this loop. A single call to time.sleep() or requests.get() within an async def endpoint will block the *entire* event loop, halting the heartbeat of the application and causing all concurrent agents to freeze.1

### **2.2 The ShopifyAPI Wrapper and Dependency Constraints**

A significant portion of APEG’s technical debt is encapsulated in its dependency on the ShopifyAPI Python library. This wrapper is built upon pyactiveresource, an older library designed to mimic the Active Record pattern found in Ruby on Rails. While efficient for simple CRUD operations, pyactiveresource is fundamentally synchronous. It abstracts HTTP calls into object methods (e.g., product.save()), hiding the underlying network interactions.

Rewriting this library to support asynchronous execution (e.g., swapping urllib3 for httpx internals) is assessed as "unrealistic" due to the depth of the dependency tree and the stability risks involved. Consequently, the integration strategy cannot rely on modernizing the library itself but must instead wrap its execution. The report identifies this as a "legacy synchronous component" that requires a specific "concurrency bridge" to function within the new system without degrading performance.1

### **2.3 Deterministic Rigidity vs. Stochastic Flexibility**

The APEG system is described as having "deterministic rigidity." Its logic flows are hard-coded sequences of conditional checks: "If inventory \< 5, update stock." This rigidity provided stability when APIs were simple and predictable. However, it lacks the resilience required for "agentic workflows."

EcomAgent, by contrast, operates stochastically. An agent might decide to search for a product, analyze its performance, and then *choose* to update the listing or flag it for review based on a probabilistic assessment of the data. The legacy code lacks the "Agent-as-a-Tool" abstractions necessary for this. It exposes monolithic scripts rather than granular, callable functions. For example, a script might "sync all inventory," whereas an agent requires a tool to "update inventory for SKU X at Location Y." The lack of these granular entry points is a primary friction point identified in the Project Alignment Summary.3

## ---

**3\. Target Architecture Specification: The EcomAgent Framework**

The destination for this migration is the EcomAgent framework, a sophisticated, event-driven system designed to orchestrate autonomous AI agents. Understanding its components is prerequisite to defining the integration path.

### **3.1 The Asynchronous Event Loop and FastAPI Backbone**

At the core of EcomAgent lies FastAPI, a modern web framework that leverages Python's type hints and asynchronous capabilities. Unlike the legacy system, EcomAgent treats I/O operations as non-blocking awaitables. This allows the system to maintain high throughput even when orchestrating hundreds of parallel LLM calls or waiting for slow e-commerce APIs.1

This architecture necessitates a shift in library selection. The standard requests library is incompatible with this model because it lacks await support. The target architecture mandates the use of **httpx** for all new internal HTTP interactions. httpx provides an interface compatible with requests but supports native async execution and HTTP/2, which reduces latency by multiplexing requests over a single TCP connection—critical for high-volume API interactions with Shopify and Meta.4

### **3.2 The Dual-Agent Development Strategy**

To manage the complexity of this merger, the organization is adopting a "Dual-Agent" strategy, leveraging AI to build AI. This approach assigns distinct roles to different coding assistants, mitigating the risks of human error during the massive refactoring effort.

* **Codex as the "Local Power Tool":** OpenAI Codex, accessed via CLI, serves as the engine for bulk refactoring and scaffolding. Its strength lies in its local execution environment, which can be sandboxed using OS-level controls (e.g., Linux Landlock). This allows developers to run complex "transform" scripts across the legacy APEG codebase—such as converting SQL queries to Pydantic models—without exposing proprietary code to the cloud during the draft phase.2  
* **Gemini Code Assist as the "Enterprise Integrator":** Once code is drafted, Gemini serves as the context-aware reviewer. With its massive 1-million-token context window, Gemini can ingest the entire legacy codebase and the new EcomAgent specs simultaneously. It validates that new modules adhere to enterprise security policies and data governance standards, ensuring that no legacy "hard-coded secrets" are carried over into the new repository.2

This strategy is codified in Agents.md files—"constitutions" placed in repository roots that explicitly instruct these AI agents on the project's coding standards, architectural principles (e.g., "Always use httpx for networking"), and security mandates.5

### **3.3 The Configuration and Knowledge Layer**

The EcomAgent framework relies on a structured configuration system that APEG currently lacks. The Project Alignment Summary identifies specific artifacts:

* **SessionConfig.json:** Defines runtime settings like loop guard parameters (to prevent agents from getting stuck in repetitive loops) and scoring criteria for agent performance.  
* **WorkflowGraph.json:** A definition file that maps the nodes and edges of the agent's decision process (e.g., "Intake" \-\> "Research" \-\> "Draft" \-\> "Review").  
* **PromptModules.json:** Contains the system prompts and tool definitions that drive the LLMs.  
* **Knowledge.json:** A repository of facts and rules that ground the agents, preventing hallucination.6

The legacy APEG system lacks these explicit configuration artifacts, relying instead on hard-coded logic or scattered environment variables. The integration must involve extracting implicit business logic from APEG code and serializing it into these JSON standards.

## ---

**4\. Integration Core: The Concurrency Bridge**

The "Impedance Mismatch" identified in the Spec Verification phase is the single greatest technical hurdle. This section details the engineering solution: a **Hybrid Concurrency Bridge**.

### **4.1 The asyncio.to\_thread Pattern**

Since we cannot rewrite ShopifyAPI, we must contain it. The solution leverages asyncio.to\_thread(), a feature introduced in Python 3.9 that allows blocking functions to run in a separate thread pool executor, leaving the main event loop free.

The protocol for wrapping legacy functions is as follows:

1. **Identification:** Identify all "boundary functions" in APEG—entry points where the system reaches out to an external API or database.  
2. **Encapsulation:** Create a wrapper service, LegacyBridge, which imports the synchronous APEG modules.  
3. **Offloading:** For every synchronous method APEG.sync\_method(), define an asynchronous counterpart LegacyBridge.async\_method():

Python

async def async\_method(self, \*args, \*\*kwargs):  
    \# Offload the blocking call to a separate thread  
    return await asyncio.to\_thread(self.legacy\_instance.sync\_method, \*args, \*\*kwargs)

This pattern ensures that while the specific thread executing sync\_method is blocked, the FastAPI loop remains responsive, accepting new requests and managing other agents.1

### **4.2 Handling the Global Interpreter Lock (GIL)**

While asyncio.to\_thread moves execution to a separate thread, Python’s Global Interpreter Lock (GIL) ensures that only one thread executes Python bytecode at a time. This means CPU-bound operations in APEG (e.g., heavy image processing or complex data transformation) will still contend for resources with the main loop.

**Mitigation Strategy:**

* **I/O Bound is Safe:** Most APEG operations are network I/O bound (waiting for Shopify). In these cases, the GIL is released, allowing true parallelism.  
* **CPU Bound requires Multiprocessing:** If specific legacy modules perform heavy computation (e.g., resizing thousands of images), asyncio.to\_thread is insufficient. These tasks must be offloaded to a separate **ProcessPoolExecutor** or a dedicated worker queue (like Celery or Redis Queue) to bypass the GIL entirely. The Build Plan prioritizes identifying these CPU-intensive nodes during Phase 1\.

### **4.3 HTTP Client Migration: From Requests to HTTPX**

For all *new* development and for legacy components that *can* be easily refactored, the mandate is to replace requests with httpx.

* **Syntax Compatibility:** httpx offers a mostly compatible API to requests, minimizing refactoring friction.  
* **Async Native:** httpx.AsyncClient allows for true non-blocking networking.  
* **HTTP/2 Support:** httpx supports HTTP/2, which allows for multiplexing. This is critical for the "Advertising Agent" which may need to send hundreds of ad creative variations to Meta. Multiplexing reduces the overhead of establishing TCP handshakes for each request, significantly lowering latency.1

## ---

**5\. Data Ingestion & Normalization: The Canonical Product Model (CPM)**

A fundamental challenge in this merger is the "Schema Gap." Shopify’s data model is flexible (loose tags, HTML bodies), while Etsy’s V3 API is rigid (strict taxonomy IDs, character limits). APEG currently passes raw data; EcomAgent needs structured, validated inputs. The solution is the **Canonical Product Model (CPM)**.

### **5.1 Pydantic as the Validation Engine**

The CPM will be implemented using **Pydantic** models. Pydantic provides runtime data validation, ensuring that data flowing between systems conforms to strict type definitions. This is crucial for preventing "garbage in, garbage out" scenarios with LLMs.8

Strict Mode Enforcement:  
To prevent subtle data corruption, the CPM will utilize Pydantic's strict=True mode in ConfigDict. This prevents automatic type coercion (e.g., turning the float 19.99 into the string "19.99"). In financial contexts like inventory pricing, explicit typing is required to avoid precision errors.

Python

from pydantic import BaseModel, ConfigDict, Field

class CanonicalProduct(BaseModel):  
    model\_config \= ConfigDict(strict=True)  
      
    sku: str \= Field(..., min\_length=1)  
    price\_cents: int \= Field(..., gt=0) \# Store currency as integers to avoid float math  
    title: str \= Field(..., max\_length=140) \# Etsy limit

### **5.2 Bridging the Schema Gap**

The CPM acts as the translation layer:

* **Ingestion (Shopify \-\> CPM):** When data is pulled from Shopify, it is parsed into the CPM. Custom validators cleanse HTML from descriptions and normalize tags.  
* **Enrichment (AI \-\> CPM):** The AI Agent receives the CPM and is tasked with filling missing fields required by Etsy (e.g., material\_composition, when\_made). The Pydantic schema serves as the "tool definition" for the LLM, guiding it to produce valid JSON outputs.9  
* **Egress (CPM \-\> Etsy):** The CPM exports data specifically formatted for Etsy’s endpoints, ensuring that lists are comma-separated where required and that enums (like who\_made) match valid values.10

### **5.3 Handling "Dirty" JSON**

LLMs are probabilistic; they often output "dirty" JSON—valid objects wrapped in Markdown code blocks (json... ) or containing trailing commas. The CPM ingestion pipeline must include a sanitization step (implemented in the N8N middleware) that strips these artifacts before attempting Pydantic validation. Failure to do so will cause the validation layer to reject valid AI reasoning.1

## ---

**6\. Shopify Bulk Operations Protocol: The New Egress Standard**

The most technically demanding aspect of the merger is the forced migration from Shopify REST to GraphQL Bulk Operations. This is not a simple endpoint swap; it is a fundamental change in the data transaction protocol.

### **6.1 The "Leaky Bucket" vs. Asynchronous Bulk**

The legacy REST API uses a "leaky bucket" algorithm, capped at roughly 40 requests per second. For a catalog of 50,000 SKUs, a full update could take hours, risking timeouts. The GraphQL Bulk Operations API (bulkOperationRunMutation) bypasses this by processing mutations asynchronously on Shopify’s infrastructure.11

### **6.2 The Four-Stage Transaction Lifecycle**

Implementing this requires a distributed transaction state machine:

1. **Handshake (stagedUploadsCreate):** The system must request a storage slot. Crucially, the resource parameter must be set to BULK\_MUTATION\_VARIABLES. A common pitfall is using PRODUCT or IMAGE, which leads to invalid resource errors.12 The mimeType must be explicitly text/jsonl.  
2. **Payload Construction (JSONL):** Data must be serialized into **JSONL (JSON Lines)**. Each line is a distinct JSON object representing mutation variables. Standard JSON arrays will be rejected.13  
   * *Constraint:* GraphQL is strongly typed. Legacy APEG code often treats IDs as integers. Shopify GraphQL requires global ID strings (e.g., gid://shopify/Product/12345). The CPM must handle this conversion.  
3. **Multipart Upload (The Order Constraint):** Uploading the JSONL to Google Cloud Storage (GCS) requires a multipart/form-data POST. The GCS protocol is strictly order-sensitive. The authentication parameters—policy, x-goog-signature, GoogleAccessId—**must** appear in the form data *before* the file field. If the file is sent first, GCS cannot validate the policy against the content length, and the upload fails. The Python aiohttp.FormData library is required here to enforce field order, as standard dictionaries are unordered.1  
4. **Execution & Polling:** Once uploaded, the key (not the full URL) is passed to bulkOperationRunMutation. The system must then poll currentBulkOperation or listen for the bulk\_operations/finish webhook.

### **6.3 Concurrency Management**

Shopify enforces a strict limit of **five concurrent bulk operations** per shop (as of API 2026-01).14 The system cannot simply "fire and forget." It requires a **Redis-backed queue** (Semaphore pattern) to track active jobs. If five jobs are running, the scheduler must pause submission until a completion webhook decrements the counter. A "Safety Poller" is required to check job status every 5 minutes to detect "zombie jobs" (failures that didn't fire a webhook) and release the semaphore.1

## ---

**7\. Etsy V3 API Integration: The State Machine & Taxonomy**

Etsy’s V3 API introduces complexity that APEG’s legacy logic cannot handle: a rigid taxonomy structure and a cost-driven listing lifecycle.

### **7.1 The "Draft-First" Lifecycle**

Etsy charges a listing fee ($0.20 USD) upon publication. To prevent run-away AI costs, the API prevents direct creation of active listings in many contexts. The system must implement a state machine:

1. **Draft Creation:** The AI creates a listing with state=draft via createDraftListing.  
2. **Human Review:** The draft sits in a review queue (managed via N8N/Google Sheets).  
3. **Publication:** A human approval triggers an updateListing call to change state to active, incurring the fee.10

### **7.2 Taxonomy ID and Property Mapping**

Legacy APEG likely used free-text categories. Etsy V3 requires a numeric taxonomy\_id (e.g., 123 \= "Jewelry").

* **Gap:** The AI doesn't inherently know these IDs.  
* **Solution:** A **Taxonomy Mapper** module. This service caches the taxonomy tree (fetched via getSellerTaxonomyNodes). When the AI processes a product, it uses a semantic search against this cache to select the most appropriate ID.  
* **Property Injection:** Once an ID is selected, Etsy requires specific properties (e.g., "Chain Length" for jewelry). The system must fetch these requirements (getPropertiesByTaxonomyId) and dynamically inject them into the AI’s context window so it knows which attributes to generate.15

### **7.3 The Image Upload Sequence**

Image uploading in Etsy V3 is decoupled from listing creation. You cannot send image bytes in the createDraftListing payload.

* **Sequence:**  
  1. Create Draft Listing \-\> Receive listing\_id.  
  2. Upload Image \-\> POST to /shops/{shop\_id}/listings/{listing\_id}/images using multipart/form-data.  
* **Constraint:** This implies a synchronous dependency. The workflow cannot parallelize these steps. The image upload must wait for the listing ID confirmation.16

### **7.4 OAuth2 PKCE Flow**

Etsy V3 mandates OAuth2 with PKCE (Proof Key for Code Exchange). The legacy system likely used API keys or OAuth1. The new system requires a "Token Refresher" service that manages the refresh\_token lifecycle, ensuring the background agents always have valid credentials without human intervention.17

## ---

**8\. Orchestration Middleware: N8N and Infrastructure-as-Code**

N8N serves as the "nervous system" connecting the legacy backend, the AI agents, and the human reviewers. To ensure stability and auditability, this layer must be treated as critical infrastructure.

### **8.1 Deployment Architecture**

To maintain data sovereignty (a key merger requirement), N8N is self-hosted. The recommended deployment target is a cluster of **Raspberry Pi 5** (ARM64) or equivalent edge devices, running Docker. This ensures local data processing for sensitive inventory files. The N8N instance is configured with postgres as the backend database to handle the high volume of execution logs, replacing the default SQLite which locks under load.18

### **8.2 Infrastructure as Code (IaC) with Terraform**

Manual configuration of N8N workflows ("ClickOps") is a significant risk. Workflows should be defined as code. The build plan leverages the **kodflow/terraform-provider-n8n**. This provider allows for the definition of workflows, credentials, and variables in HCL (HashiCorp Configuration Language).

* **Benefit:** Version control for agent logic. If a workflow breaks, it can be rolled back to a previous commit.  
* **Implementation:** Critical workflows (like the "Budget Approval" flow) are defined as Terraform resources, ensuring that security settings (like HMAC verification) cannot be accidentally disabled in the UI.19

### **8.3 The "Edge Trigger" Pattern**

To manage the Google Sheets control plane, the system uses an "Edge Trigger" logic. A simple "On Update" trigger is too noisy—it fires on every typo correction. The workflow logic is configured to compare Row\_New.Status vs Row\_Old.Status. The pipeline executes *only* when the status changes specifically from PENDING to APPROVED, preventing duplicate processing.1

### **8.4 Security: HMAC and Action Tokens**

* **Ingestion:** The N8N webhook verifies the x-agent-signature header (HMAC-SHA256) against the raw payload.  
* **Escalation:** For sensitive actions (e.g., ad budget \> $10k), N8N generates a time-limited **Action Token**. This token is a signed JWT or HMAC hash containing the request ID and expiry. It is sent via Slack/Email. The approval webhook validates this token before proceeding, ensuring that only authorized personnel can trigger high-value transactions.1

## ---

**9\. Meta Marketing API & Agent Abstraction**

The EcomAgent framework includes a specialized "Advertising Agent" that requires distinct handling.

### **9.1 "Pixel-Less" Tracking Strategy**

With the degradation of cookie-based tracking, the agent must implement robust server-side tracking (CAPI). However, specifically for "pixel-less" campaigns (e.g., on platforms where pixel injection is impossible), the agent utilizes **Offline Event Sets**. The system uploads conversion data (hashed emails/phones) directly to Meta, allowing attribution without browser-side tracking.20

### **9.2 Async Request Sets**

Meta’s Graph API has strict rate limits. When the agent generates hundreds of ad variations (copy \+ image combinations), sending them sequentially is too slow. The system utilizes **Async Request Sets** (batch requests). The agent bundles multiple creation mutations into a single HTTP POST. Meta processes these asynchronously and returns a batch status.

### **9.3 The "Paused" Default**

To ensure safety, all agent-created campaigns default to status: "PAUSED". This is a hard-coded constraint in the create\_campaign tool definition. It forces a human review step within the Meta Ads Manager before any spend occurs.21

## ---

**10\. State Persistence & Memory: The LangGraph Backend**

Autonomous agents require memory. They need to know what they did five minutes ago and what the user prefers. APEG has no such memory. EcomAgent uses **LangGraph** for state management.

### **10.1 Migration to Postgres Checkpointer**

While SQLite is sufficient for testing, it cannot handle the concurrency of the target production system. The build plan mandates the use of **PostgresSaver**.

* **Schema Requirement:** The PostgresSaver requires specific tables (checkpoints, writes) to exist. A critical step often missed is calling the .setup() method on the checkpointer during application startup. If this is skipped, the first agent execution will fail with "relation does not exist" errors.22  
* **Async Implementation:** The system utilizes AsyncPostgresSaver to ensure that saving the agent's state (which happens at every step of the graph) does not block the main event loop.23

### **10.2 Checkpoint Structure**

The Postgres schema stores state as a series of checkpoints, keyed by thread\_id. This allows for "Time Travel"—developers can debug a failed agent by loading a previous checkpoint and replaying the execution step-by-step. This is essential for diagnosing why an agent might have hallucinated or chosen a wrong tool.24

## ---

**11\. Testing & Validation Framework**

Deploying autonomous agents requires a new paradigm of testing.

### **11.1 Adversarial Testing**

Standard unit tests are insufficient for probabilistic agents. The system undergoes "Adversarial Testing" where "dirty" or malicious inputs are injected.

* **Scenario:** Injecting prompt injection attacks into product descriptions to see if the agent executes them.  
* **Validation:** Ensuring the Pydantic validators and N8N sanitization nodes strip these inputs before they reach the LLM or the e-commerce platform.25

### **11.2 Deterministic Replay with VCR.py**

To test the integration code without incurring API costs or hitting rate limits, the team uses **VCR.py**. This tool records the HTTP interactions (request/response) of the first test run into a "cassette" (YAML file). Subsequent test runs play back this cassette. This makes the tests deterministic and fast, even for the complex Shopify Bulk Operations flow.26

### **11.3 Load Testing with Locust**

To verify the system's resilience under load (e.g., receiving 10,000 webhooks from Shopify simultaneously), the team uses **Locust**. A Locust swarm is configured to simulate the "Thundering Herd" scenario, verifying that the Redis queue correctly buffers the load and that the system respects the 5-concurrent-job limit.27

## ---

**12\. Build Plan: The Protocol for Convergence**

This build plan is structured into four distinct phases, prioritizing the stabilization of the legacy system before enabling high-risk autonomous features.

### **Phase 1: The Asynchronous Foundation (Weeks 1-4)**

**Objective:** Establish the hybrid runtime environment and the Canonical Product Model.

1. **Dependency Modernization:** Freeze ShopifyAPI versions. Introduce httpx and aiohttp.  
2. **Concurrency Bridge:** Implement the LegacyBridge service with asyncio.to\_thread wrappers for all critical APEG functions.  
3. **CPM Implementation:** Define the CanonicalProduct Pydantic model with strict=True and custom validators for Shopify/Etsy constraints.

### **Phase 2: The Orchestration Layer (Weeks 5-8)**

**Objective:** Deploy N8N and the Shopify GraphQL pipeline.

1. **N8N Deployment:** Deploy self-hosted N8N on Docker/Raspberry Pi. Provision workflows using Terraform (kodflow/n8n). Implement HMAC verification and JSON sanitization.  
2. **Shopify Bulk Pipeline:** Develop the BulkOperationService implementing the 4-stage transaction (Stage \-\> Upload \-\> Execute \-\> Poll) with strict JSONL formatting and multipart ordering.

### **Phase 3: Intelligence & Agent Implementation (Weeks 9-12)**

**Objective:** Activate EcomAgent and integrate Etsy V3.

1. **LangGraph Persistence:** Implement AsyncPostgresSaver with proper schema setup (.setup()).  
2. **Etsy Agent:** Develop the EtsyTaxonomyAgent with tools for taxonomy mapping (getSellerTaxonomyNodes) and draft creation (createDraftListing). Implement the image upload sequencer.  
3. **Agents.md Constitution:** Author the Agents.md files for Codex and Gemini to guide future development.

### **Phase 4: Validation & Hardening (Weeks 13-14)**

**Objective:** Ensure reliability and auditability.

1. **Regression Testing:** Implement VCR.py for all API clients.  
2. **Load Testing:** Execute Locust swarms to tune Redis queue parameters.  
3. **Adversarial Audit:** Run the adversarial dataset against the agents to verify guardrails.

## ---

**13\. Conclusion and Risk Register**

The unification of APEG and EcomAgent is a complex but technically viable initiative. Success hinges on strict adherence to the protocols defined in this report. The transition from "deterministic rigidity" to "guardrailed autonomy" is enabled by the robust implementation of the **Canonical Product Model**, the **Hybrid Concurrency Bridge**, and the **N8N Orchestration Layer**.

**Primary Risks:**

1. **Schema Drift:** If the CPM is not strictly maintained, the "Schema Gap" will widen, causing agent failures.  
2. **Concurrency Deadlock:** Failure to properly wrap legacy code in to\_thread will freeze the application.  
3. **API Rate Limiting:** Ignoring the 5-concurrent-job limit on Shopify will result in critical failures.

**Recommendation:** Initiate Phase 1 immediately. The creation of the CPM and the Concurrency Bridge are the critical path dependencies for all subsequent innovation. Ensure that the "Dual-Agent" workflow (Codex/Gemini) is adopted by the engineering team to accelerate the refactoring process while maintaining code quality.

#### **Works cited**

1. Autonomous E-Commerce on Raspberry Pi: Architecture and Agents  
2. Codex, Gemini, DSL Integration Plan, [https://drive.google.com/open?id=15nEo1w0tH6yvJEKeAz4EUhCHVlccesuyqlM1kUOqNWs](https://drive.google.com/open?id=15nEo1w0tH6yvJEKeAz4EUhCHVlccesuyqlM1kUOqNWs)  
3. Project Alignment Summary.docx, [https://drive.google.com/open?id=15lAEE3ssslR4IVFgX\_VZi2O5Jc2heG-l](https://drive.google.com/open?id=15lAEE3ssslR4IVFgX_VZi2O5Jc2heG-l)  
4. Clients \- HTTPX, accessed December 29, 2025, [https://www.python-httpx.org/advanced/clients/](https://www.python-httpx.org/advanced/clients/)  
5. Codex, Gemini, DSL Integration Plan \- Google Docs.pdf, [https://drive.google.com/open?id=17\_KzlZgsLPBKUODGWof7eoC84X4I2rSm](https://drive.google.com/open?id=17_KzlZgsLPBKUODGWof7eoC84X4I2rSm)  
6. Project Alignment Summary.pdf, [https://drive.google.com/open?id=1rfosULNkeUJovSN5koFbnX2nqNC2RX1m](https://drive.google.com/open?id=1rfosULNkeUJovSN5koFbnX2nqNC2RX1m)  
7. Project Alignment Summary.pdf, [https://drive.google.com/open?id=14LXhTuH5Ye1ucHOQVlBHXV6boU4X8WJt](https://drive.google.com/open?id=14LXhTuH5Ye1ucHOQVlBHXV6boU4X8WJt)  
8. Models \- Pydantic Validation, accessed December 29, 2025, [https://docs.pydantic.dev/latest/concepts/models/](https://docs.pydantic.dev/latest/concepts/models/)  
9. How to Use Pydantic for LLMs: Schema, Validation & Prompts description, accessed December 29, 2025, [https://pydantic.dev/articles/llm-intro](https://pydantic.dev/articles/llm-intro)  
10. Listings Tutorial | Etsy Open API v3, accessed December 29, 2025, [https://developer.etsy.com/documentation/tutorials/listings](https://developer.etsy.com/documentation/tutorials/listings)  
11. Perform bulk operations with the GraphQL Admin API \- Shopify Dev Docs, accessed December 29, 2025, [https://shopify.dev/docs/api/usage/bulk-operations/queries](https://shopify.dev/docs/api/usage/bulk-operations/queries)  
12. Staged Uploads Create Error \- Shopify Community, accessed December 29, 2025, [https://community.shopify.com/t/staged-uploads-create-error/70653](https://community.shopify.com/t/staged-uploads-create-error/70653)  
13. Bulk import data with the GraphQL Admin API \- Shopify Dev Docs, accessed December 29, 2025, [https://shopify.dev/docs/api/usage/bulk-operations/imports](https://shopify.dev/docs/api/usage/bulk-operations/imports)  
14. Shopify API limits, accessed December 29, 2025, [https://shopify.dev/docs/api/usage/limits](https://shopify.dev/docs/api/usage/limits)  
15. Reference | Etsy Open API v3, accessed December 29, 2025, [https://developers.etsy.com/documentation/reference](https://developers.etsy.com/documentation/reference)  
16. Uploading Product Images VIA API and Primary Image Wanted Not Showing as Primary · etsy open-api · Discussion \#1228 \- GitHub, accessed December 29, 2025, [https://github.com/etsy/open-api/discussions/1228](https://github.com/etsy/open-api/discussions/1228)  
17. Authentication | Etsy Open API v3, accessed December 29, 2025, [https://developer.etsy.com/documentation/essentials/authentication](https://developer.etsy.com/documentation/essentials/authentication)  
18. Hosting n8n on a Raspberry Pi 5 | by Sean Spaniel | Medium, accessed December 29, 2025, [https://medium.com/@sean.spaniel/hosting-n8n-on-a-raspberry-pi-5-d1f5da8cca82](https://medium.com/@sean.spaniel/hosting-n8n-on-a-raspberry-pi-5-d1f5da8cca82)  
19. Docs overview | kodflow/n8n \- Terraform Registry, accessed December 29, 2025, [https://registry.terraform.io/providers/kodflow/n8n/latest/docs](https://registry.terraform.io/providers/kodflow/n8n/latest/docs)  
20. The Secret to Running Facebook Ad Campaigns Without Pixel Data \- LeadEnforce, accessed December 29, 2025, [https://leadenforce.com/blog/the-secret-to-running-facebook-ad-campaigns-without-pixel-data](https://leadenforce.com/blog/the-secret-to-running-facebook-ad-campaigns-without-pixel-data)  
21. Create an Ad Campaign \- Marketing API \- Meta for Developers, accessed December 29, 2025, [https://developers.facebook.com/docs/marketing-api/get-started/basic-ad-creation/create-an-ad-campaign/](https://developers.facebook.com/docs/marketing-api/get-started/basic-ad-creation/create-an-ad-campaign/)  
22. PostgresSaver | langchain.js, accessed December 29, 2025, [https://reference.langchain.com/javascript/classes/\_langchain\_langgraph-checkpoint-postgres.index.PostgresSaver.html](https://reference.langchain.com/javascript/classes/_langchain_langgraph-checkpoint-postgres.index.PostgresSaver.html)  
23. Persistence \- Docs by LangChain, accessed December 29, 2025, [https://docs.langchain.com/oss/python/langgraph/persistence](https://docs.langchain.com/oss/python/langgraph/persistence)  
24. Memory \- Docs by LangChain, accessed December 29, 2025, [https://docs.langchain.com/oss/python/langgraph/add-memory](https://docs.langchain.com/oss/python/langgraph/add-memory)  
25. Dissecting Adversarial Robustness of Multimodal LM Agents \- arXiv, accessed December 29, 2025, [https://arxiv.org/html/2406.12814v2](https://arxiv.org/html/2406.12814v2)  
26. VCR.py — vcrpy 8.0.0 documentation, accessed December 29, 2025, [https://vcrpy.readthedocs.io/](https://vcrpy.readthedocs.io/)  
27. Writing a locustfile — Locust 2.42.6 documentation, accessed December 29, 2025, [https://docs.locust.io/en/stable/writing-a-locustfile.html](https://docs.locust.io/en/stable/writing-a-locustfile.html)