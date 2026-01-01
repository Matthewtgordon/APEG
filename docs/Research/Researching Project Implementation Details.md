# **APEG & EcomAgent Merger Integration Protocol: Technical Implementation Guide for Autonomous Commerce Architectures**

## **1\. Introduction: The Architectural Imperative of the Merger**

The merger between APEG and EcomAgent represents a pivotal shift in the digital commerce landscape, necessitating the consolidation of high-throughput inventory systems with probabilistic, non-deterministic artificial intelligence agents. This integration is not merely a data migration exercise but a fundamental re-architecture of the commerce stack to support "Autonomous Operations." The objective is to transition from static, rule-based automation to dynamic, agentic workflows capable of managing inventory, optimizing advertising spend, and generating creative content with minimal human intervention.

However, the introduction of autonomous agents into critical business paths introduces significant risk. Unlike deterministic code, Large Language Models (LLMs) can hallucinate, deviate from instructions, or fail to produce structured outputs. Therefore, the proposed architecture prioritizes "Guardrailed Autonomy." We introduce a Human-in-the-Loop (HITL) staging layer for critical approvals, robust observability pipelines to visualize "chain of thought" reasoning, and rigorous testing frameworks designed for non-deterministic software.

This comprehensive technical report outlines the implementation strategy for six core integration components. It serves as the definitive standard for engineering teams, detailing the exact protocols, libraries, and architectural patterns required to deploy a resilient, scalable, and observable autonomous commerce system. The analysis moves beyond high-level abstraction to address specific implementation hurdles—such as the multipart upload order in Shopify’s GraphQL API, the asynchronous batching patterns required for Meta’s Marketing API, and the cryptographic security required for N8N approval webhooks. By strictly adhering to these protocols, the merged entity will achieve a system that balances the speed of AI with the reliability of enterprise software.

## ---

**2\. Component I: N8N & Google Sheets as a Human-in-the-Loop Staging Layer**

In the ecosystem of autonomous agents, the "Staging Layer" is the architectural equivalent of a safety valve. While the ultimate goal is fully autonomous operation, the current state of Generative AI necessitates a verification step for high-stakes actions—such as publishing product descriptions to a live storefront or committing significant ad spend. We utilize N8N as an orchestration middleware and Google Sheets as a low-friction, widely accessible interface for this human review process. This combination allows operational teams to interact with complex agent outputs without needing access to production databases or command-line interfaces.

### **2.1 Architectural Role and Data Flow**

The architecture positions Google Sheets not as a database of record, but as a mutable control plane. The data flow is unidirectional for ingestion but bidirectional for state management. The lifecycle of a data packet—for example, a batch of AI-generated product descriptions—follows a strict sequence: Ingestion, Sanitization, Staging, Review, and Execution.

The choice of N8N over other automation platforms (like Zapier or Make) is driven by its ability to handle complex, branching logic and its self-hostable nature, which aligns with the data sovereignty requirements of the merger. N8N allows for the execution of custom JavaScript within workflows, essential for the data cleaning and cryptographic verification steps required in this protocol.1

### **2.2 Ingestion Phase: Webhooks and Payload Sanitization**

The entry point for the staging layer is an N8N **Webhook Node**, configured to accept HTTP POST requests from the upstream AI Agent. Polling architectures are rejected here due to the latency they introduce; a push-based model ensures that as soon as the Agent completes its generation task, the data is available for review.

#### **2.2.1 Secure Webhook Configuration**

The webhook endpoint acts as a public gateway, making security paramount. Relying solely on the obscurity of the URL is insufficient for enterprise architecture. We implement Header-Based Authentication. The sending Agent must include a custom header, x-agent-signature, containing an HMAC-SHA256 hash of the payload signed with a shared secret.

Inside N8N, a **Code Node** immediately follows the webhook. This node performs two critical functions:

1. **Signature Verification:** It re-computes the hash of the incoming body and compares it against the header. If they do not match, the workflow terminates immediately with a 403 Forbidden response.  
2. **Payload Sanitization:** AI Agents often output "dirty" JSON—containing trailing commas, inconsistent date formats, or markdown code blocks (e.g., \`\`\`json... \`\`\`). The JavaScript within the Code Node strips these artifacts, ensuring the downstream nodes receive strictly formatted JSON objects.1

#### **2.2.2 Batching and Rate Limiting**

A common failure mode in Google Sheets integrations is the "Thundering Herd" problem. If the Agent generates 5,000 descriptions and pushes them simultaneously, the Google Sheets API will reject requests with 429 Too Many Requests. To mitigate this, we employ the **Split In Batches** node within N8N.

The workflow accepts the full array of data but processes it in chunks of 10-20 rows. Between each write operation, a **Wait Node** introduces a configurable delay (e.g., 2 seconds). This throttling ensures that the workflow respects Google’s write quotas (typically 60 requests per minute per user) while maintaining continuous throughput. This pattern transforms a bursty, high-velocity input into a linear, rate-limited stream compatible with the constraints of the spreadsheet API.1

### **2.3 Staging Phase: The Google Sheets Structure**

The Google Sheet itself must be structured rigidly to support machine interaction. We utilize a "Status" column methodology. Every new row appended by N8N defaults to a status of PENDING. This column serves as the state variable for the Finite State Machine (FSM) governing the workflow.

Mapped Fields:  
The N8N Google Sheets node is configured to map incoming JSON keys to specific columns. Critical metadata, such as the submitted\_date and agent\_id, are appended alongside the business data (e.g., product\_title, ad\_copy). The submitted\_date is generated at the point of ingestion using N8N's $now variable, formatted to ISO-8601 standards, providing an immutable audit trail of when the content was generated.1

### **2.4 Trigger Phase: Detecting Human Approval**

The transition from Staging to Execution is triggered by a human changing the status from PENDING to APPROVED. Detecting this state change reliably requires careful configuration of the **Google Sheets Trigger** node.

#### **2.4.1 Row Update Logic and Versioning**

We configure the trigger to listen specifically for the Row Updated event. However, a simple update trigger is noisy; it fires if a user corrects a typo, resizes a column, or accidentally modifies a cell. To filter for valid approval events, we leverage the specific capability of the N8N trigger to output "Both Versions" of the row—the data *before* the edit and the data *after* the edit.2

The workflow logic involves a conditional check (IF Node) immediately following the trigger. The condition explicitly checks:  
{{$json\["new"\]\["status"\]}} \== "APPROVED" AND {{$json\["old"\]\["status"\]}}\!= "APPROVED".  
This logic ensures distinct event processing:

* **True Positive:** The manager changes status from PENDING to APPROVED. The workflow proceeds to execution.  
* **False Positive:** The manager corrects a typo in the Description column, but leaves status as APPROVED (or PENDING). The condition fails, and the workflow terminates.  
* **Reversion:** The manager changes status from APPROVED back to PENDING (perhaps to hold a release). The condition fails, preventing accidental re-execution.

This "Edge Trigger" pattern—reacting only to the *crossing of a threshold* rather than the state itself—is a best practice in event-driven architectures to prevent duplicate processing.3

### **2.5 Execution Phase: Closing the Loop**

Once approved, the data must be routed to the appropriate destination. N8N serves as a switchboard here. Based on a task\_type field in the row, the workflow branches to either a Shopify update sequence (via HTTP Request to the Shopify Agent) or an Ad Campaign creation sequence (via HTTP Request to the Advertising Agent).

Crucially, the workflow performs a final "Cleanup" step. After successful downstream execution, N8N updates the Google Sheet row again, changing the status to PROCESSED and adding a processed\_at timestamp. This provides visual feedback to the human manager that the system has successfully acted on their approval, closing the feedback loop and preventing confusion about which items have been synced.

### **2.6 Advanced Security: HMAC-Signed Webhooks for Remote Approval**

For highly sensitive operations—such as approving budget increases exceeding $10,000—a simple spreadsheet edit is insufficient due to the lack of access controls on individual cells. In these scenarios, the system bypasses the direct Sheet trigger in favor of a secure, link-based approval flow.

**Cryptographic Workflow:**

1. **Notification:** Instead of waiting for a Sheet update, N8N sends a notification (via Slack or Email) to a designated Approver.4  
2. **Token Generation:** The workflow generates a time-limited Action Token. This token contains the request\_id, the action (approve/reject), and an expiry timestamp.  
3. **HMAC Signing:** The payload is signed using a secret key known only to the N8N instance.  
   * *Mechanism:* signature \= HMAC\_SHA256(payload \+ secret)  
4. **Link Construction:** The notification contains a URL: https://n8n.apeg.com/webhook/decision?token=...\&sig=....  
5. **Verification:** When the manager clicks the link, the receiving workflow verifies the signature and checks if current\_time \< expiry.

This method ensures that even if the link is shared or accessed later, it is valid only for a specific window and cannot be tampered with (e.g., changing the ID in the URL) without invalidating the signature. This cryptographic approach brings enterprise-grade security to the low-code environment.4

## ---

**3\. Component II: Shopify GraphQL Bulk Operations Implementation**

For the merged entity, inventory updates will involve tens of thousands of SKUs simultaneously. The traditional REST API, with its "leaky bucket" rate limit of 40 requests per second, is mathematically incapable of supporting this volume without significant latency and complexity (e.g., handling 429 retries for hours). The architectural solution is the **Shopify Admin GraphQL API Bulk Operations**, specifically the bulkOperationRunMutation. This allows for asynchronous, high-throughput updates but introduces significant implementation complexity regarding file handling and state management.

### **3.1 The Bulk Mutation Lifecycle**

The Bulk Mutation pattern differs fundamentally from standard API interactions. It is a distributed transaction distributed across four stages: **Preparation**, **Staging**, **Execution**, and **Confirmation**. The most critical and error-prone phase is the "Staged Upload," where data is moved from the Agent's memory to a cloud storage bucket accessible by Shopify.5

### **3.2 Step 1: Preparation of JSONL Payloads**

The unit of data for a bulk operation is not a JSON object, but a JSONL (JSON Lines) file. Each line in the file represents a single, independent mutation variable set. This distinction is vital; the mutation string sent to the API is generic (e.g., productUpdate($input: ProductInput\!)), while the file provides the specific $input for each of the 50,000 executions.

Python Implementation Detail:  
The Agent must serialize its internal object representation into a strict JSONL format.

Python

import json

def generate\_jsonl(products):  
    buffer \=  
    for product in products:  
        \# Construct the input variable for productUpdate  
        mutation\_vars \= {  
            "input": {  
                "id": f"gid://shopify/Product/{product\['id'\]}",  
                "title": product\['title'\],  
                "price": str(product\['price'\]) \# GraphQL expects Strings for money/decimal  
            }  
        }  
        buffer.append(json.dumps(mutation\_vars))  
    return "\\n".join(buffer)

This generation process must handle type strictness—Shopify's GraphQL schema is strongly typed. Sending a float where a String is expected (e.g., for price) will cause the entire bulk operation to fail or report errors in the result file.

### **3.3 Step 2: The stagedUploadsCreate Protocol**

Before uploading the file, the system must perform a handshake with Shopify to reserve a storage slot. This is done via the stagedUploadsCreate mutation.

Query Structure:  
We must explicitly request a resource type of BULK\_MUTATION\_VARIABLES. The input must also specify the mimeType as text/jsonl and the httpMethod as POST.

GraphQL

mutation stagedUploadsCreate($input:\!) {  
  stagedUploadsCreate(input: $input) {  
    stagedTargets {  
      url  
      resourceUrl  
      parameters {  
        name  
        value  
      }  
    }  
  }  
}

The response contains three critical pieces of information:

1. url: The actual Google Cloud Storage (GCS) bucket URL.  
2. resourceUrl: The identifier the Agent will pass back to Shopify later to reference this file.  
3. parameters: A list of key-value pairs (auth tokens, policies, signatures) required by GCS to accept the upload.6

### **3.4 Step 3: The Multipart Upload (Technical Deep Dive)**

This step represents the most common point of failure in Shopify integrations. The upload to GCS requires a strictly formatted multipart/form-data POST request. Crucially, the order of the form fields matters. The authentication parameters (Policy, Signature, Google Access ID) **must** appear in the payload *before* the file content itself. If the file is sent first, GCS cannot validate the policy against the content length or type and will reject the request with a generic XML error, often misidentified as a Shopify error.8

Robust Python Implementation using aiohttp:  
We utilize aiohttp for its non-blocking capabilities, essential for high-concurrency agents. The FormData helper is used to construct the payload, ensuring strict ordering.

Python

import aiohttp

async def upload\_staged\_file(target, file\_content):  
    url \= target\['url'\]  
    params \= {p\['name'\]: p\['value'\] for p in target\['parameters'\]}  
      
    \# Initialize FormData  
    form \= aiohttp.FormData()  
      
    \# 1\. Add all auth parameters FIRST  
    for key, value in params.items():  
        form.add\_field(key, value)  
      
    \# 2\. Add the file content LAST  
    \# The field name 'file' is mandatory.   
    \# The filename and content\_type must match the reservation.  
    form.add\_field('file',   
                   file\_content,   
                   filename='bulk\_op.jsonl',   
                   content\_type='text/jsonl')  
      
    async with aiohttp.ClientSession() as session:  
        async with session.post(url, data=form) as response:  
            if response.status not in :  
                text \= await response.text()  
                raise UploadError(f"GCS Upload Failed: {text}")

*Insight:* Many developers attempt to use standard dict for the data argument. This fails because dictionaries are unordered (in older Python versions) or because the HTTP library does not guarantee field order in the wire protocol. Using FormData enforces the sequence.10

### **3.5 Step 4: Execution and State Monitoring**

Once the file is uploaded, the bulkOperationRunMutation is triggered referencing the stagedUploadPath (which corresponds to the resourceUrl from Step 2).5

Concurrency Limits:  
Shopify enforces a strict limit on concurrent bulk operations. As of API version 2026-01, this limit is five concurrent operations per shop. Prior versions allowed only one. The Agent must implement a queueing mechanism (using Redis) to track active operations. If the limit is reached, the Agent must wait for a bulk\_operations/finish webhook before submitting the next job. Failure to respect this will result in a 429 Throttled error that blocks the operation entirely.7  
Webhook vs. Polling:  
The Agent should subscribe to the bulk\_operations/finish webhook topic. This provides an event-driven notification upon completion. However, given the non-deterministic nature of webhook delivery (potential delays or drops), a "Safety Poller" should be implemented. This poller checks the currentBulkOperation status every 5 minutes to detect "zombie" jobs that may have finished without triggering a webhook delivery, ensuring the system never deadlocks waiting for a signal that was lost.11

## ---

**4\. Component III: Architecture for a Specialized Advertising Agent**

The Advertising Agent is a complex orchestration engine responsible for translating high-level business goals (e.g., "Increase ROAS to 4.0") into low-level API calls across disparate platforms. The architecture must unify the REST-centric, graph-based model of Meta (Facebook/Instagram) with the service-oriented, gRPC-based model of Google Ads. This requires an abstraction layer that normalizes concepts like "Campaigns," "Ad Sets/Groups," and "Creatives/Assets."

### **4.1 Meta Marketing API Architecture**

Meta's API operates on the Social Graph. The primary challenge is handling the sheer volume of entities (hundreds of ad variations) and the strict compliance requirements for ad categories.

#### **4.1.1 Asynchronous Request Sets**

Creating hundreds of ads via synchronous HTTP POST requests is inefficient and prone to timeouts. The Agent utilizes **Async Request Sets**. This pattern bundles multiple requests (e.g., creating 50 ads) into a single batch job submitted to Meta's servers.

**Workflow:**

1. **Submission:** The Agent POSTs to /\<ad\_account\_id\>/asyncadrequestsets. The payload contains an array of individual requests (Method, Relative URL, Body).  
2. **Processing:** Meta processes these in the background. The API returns a request\_set\_id.  
3. **Polling:** The Agent polls /\<request\_set\_id\>?fields=is\_completed,success\_count,error\_count.12  
4. **Retrieval:** Once is\_completed=true, the Agent retrieves the results.

This approach decouples the Agent's runtime from Meta's processing time, significantly increasing resilience against network instability.12

#### **4.1.2 Compliance and Special Ad Categories**

A frequent failure point in automated ad creation is the special\_ad\_categories field. Since the merger involves diverse e-commerce products, some may fall under "Credit," "Employment," or "Housing" (e.g., store credit offers). The Agent must explicitly categorize every campaign.

* **Default:** NONE or \`\`.  
* **Requirement:** If the Agent fails to set this field, the API will reject the campaign creation with a policy error. The Agent's internal validation logic must check product metadata against a keyword list to predictively tag campaigns before submission.13

### **4.2 Google Ads API Architecture**

The Google Ads API is fundamentally different, relying on a strict hierarchy of resources managed via "Mutate" services.

#### **4.2.1 The Atomic Mutate Pattern with Temporary IDs**

Unlike Meta, where you create a Campaign, get its ID, then create an Ad Set using that ID, Google allows (and encourages) atomic creation of the entire tree in a single request. This is achieved using **Temporary IDs**.

**Mechanism:**

1. **Budget Operation:** Create a CampaignBudget object. Assign it a resource name using a temporary ID, e.g., customers/123/campaignBudgets/-1.  
2. **Campaign Operation:** Create a Campaign object. Set its budget field to customers/123/campaignBudgets/-1. Assign the campaign a temporary ID, e.g., customers/123/campaigns/-2.  
3. **Ad Group Operation:** Create an AdGroup. Set its campaign field to customers/123/campaigns/-2.  
4. **Execution:** Submit all three operations in a single mutate call to the GoogleAdsService.

**Implication:** This guarantees transactional atomicity. If the Ad Group is invalid, the Campaign and Budget are not created. This prevents the accumulation of "orphaned" budgets or empty campaigns that clutter the account and confuse human managers.15

#### **4.2.2 Asynchronous gRPC and the Python Client**

The official google-ads Python client is synchronous. For a high-concurrency Agent, blocking on a network call is unacceptable. We have two architectural choices:

1. **ThreadPoolExecutor:** Wrap the blocking client calls in loop.run\_in\_executor. This is the recommended approach as it preserves the type safety and helper methods of the official library (Protobuf handling) while preventing the blocking of the main event loop.16  
2. **Direct REST/JSON:** Construct raw JSON payloads and send them via aiohttp to the REST endpoint (https://googleads.googleapis.com/v17/...). This offers true async I/O but sacrifices the robust error handling and type checking of the client library. Given the complexity of Google's API, the Executor approach is preferred for maintainability.17

## ---

**5\. Component IV: Metrics Collection for AI Agents (OpenTelemetry)**

Observing autonomous agents requires a paradigm shift from monitoring "Service Health" (CPU, RAM, Latency) to monitoring "Cognitive Health" (Reasoning steps, Token consumption, Hallucination rates). We utilize **OpenTelemetry (OTel)** to standardize this data collection, exporting to a Prometheus/Grafana stack.

### **5.1 Manual Instrumentation and Span Hierarchy**

Auto-instrumentation (e.g., opentelemetry-instrumentation-fastapi) captures the outer HTTP shell of the Agent but treats the internal reasoning as a black box. We must implement **Manual Instrumentation** to visualize the "Chain of Thought."

**Span Hierarchy Strategy:**

* **Root Span:** agent\_request (The incoming user query).  
  * **Child Span:** retrieve\_context (RAG lookup).  
    * **Attribute:** db.vector.score (Relevance score of retrieved docs).  
  * **Child Span:** llm\_generation (The call to OpenAI/Anthropic).  
    * **Attribute:** llm.token\_count\_prompt, llm.token\_count\_completion.  
    * **Attribute:** llm.model\_name.  
  * **Child Span:** tool\_execution (e.g., shopify\_lookup).  
    * **Attribute:** tool.name, tool.success.

This granularity allows engineers to pinpoint *where* latency is introduced. Is the RAG lookup slow? Is the LLM generating too many tokens? Without manual spans, these questions are unanswerable.18

### **5.2 Custom Metrics for Agent Economics**

We define specific Prometheus Counters and Histograms to track the economic and qualitative performance of the agent.

1. **Token Cost Counter:** llm\_cost\_estimated\_usd\_total.  
   * *Calculation:* Every time an LLM span completes, the application calculates the cost based on the model (e.g., $10/1M tokens for GPT-4 input) and increments this counter. This enables real-time dashboards of "Burn Rate."  
2. **Hallucination/Refusal Rate:** agent\_semantic\_errors\_total.  
   * *Trigger:* Incremented when the Agent output fails validation or contains refusal phrases (e.g., "I cannot do that").  
3. **Tool Usage Distribution:** agent\_tool\_calls\_total (Label: tool\_name).  
   * *Insight:* A sudden drop in the usage of a specific tool (e.g., create\_ad) often indicates a prompt regression where the model "forgot" how to use the tool effectively.

### **5.3 PII Redaction via Span Processors**

The payloads sent to LLMs often contain sensitive customer data. Logging these payloads to an observability backend is a security violation. We implement a custom **SpanProcessor** in Python.

Mechanism:  
Before a span is exported, the processor intercepts it. It iterates through all attributes (specifically llm.prompt and llm.response). It applies a series of Regex patterns (Email, Credit Card, SSN) and replaces matches with \`\`. This ensures that while we retain the structure of the interaction for debugging, the data remains secure.20

## ---

**6\. Component V: Robust Error Handling Matrix**

In deterministic systems, errors are binary (Success/Fail). In agentic systems, errors are spectral. A "failure" could be a timeout (Transient), a 401 Unauthorized (Configuration), or an output that is syntactically correct but factually wrong (Semantic). We implement a tiered Error Handling Matrix.

### **6.1 The Error Taxonomy**

| Error Category | Description | Strategy | Mechanism |
| :---- | :---- | :---- | :---- |
| **Transient** | Network timeouts, 503 Service Unavailable. | **Retry w/ Exponential Backoff** | Use tenacity library. Max 3 retries. |
| **Throttling** | 429 Too Many Requests. | **Circuit Breaker \+ Wait** | Use aiobreaker to stop requests globally. |
| **Semantic** | LLM outputs invalid JSON or "hallucinates". | **Self-Correction Loop** | Feed error back to LLM ("You output text, I need JSON"). |
| **Fatal** | 401 Unauthorized, 400 Bad Request (Logic). | **Fail Fast & Alert** | Terminate flow, PagerDuty alert. |

### **6.2 The Circuit Breaker Pattern (Python Implementation)**

To prevent the Agent from DDoSing Shopify during an outage, or to handle strict rate limits gracefully, we wrap external API clients in a **Circuit Breaker**.

Library: We use aiobreaker which integrates natively with asyncio.  
Storage: The state of the breaker (Open/Closed) is stored in Redis. This is crucial for a distributed agent fleet. If Agent Instance A trips the breaker because Shopify is down, Agent Instance B (running on a different pod) sees the open state in Redis and immediately stops sending requests, preventing a "thundering herd" when the service recovers.21  
**Configuration:**

* fail\_max: 5 (Number of errors to trip the breaker).  
* reset\_timeout: 60s (Time to wait before attempting a "Half-Open" test request).  
* exclude: \[semantic\_errors\] (Do not trip the breaker for LLM hallucinations; only for network/API failures).22

### **6.3 Semantic Recovery: The "Self-Healing" Loop**

When an Agent fails to produce valid JSON (a common issue with weaker models), throwing an exception is wasteful. We implement a **Self-Correction Loop**.

**Logic:**

1. Agent generates output.  
2. System attempts json.loads(output).  
3. **Catch JSONDecodeError:**  
   * Do not fail.  
   * Construct a new user message: *"Error: Your previous output was not valid JSON. Please correct it. Error details: {e}"*.  
   * Send this back to the LLM (Max 3 retries).  
4. This technique resolves over 80% of formatting errors without human intervention, significantly increasing the "Success Rate" metric.23

## ---

**7\. Component VI: Testing Strategy for Non-Deterministic Systems**

Testing AI agents is uniquely challenging because Input A does not always equal Output B. The system is probabilistic. Our testing strategy moves from "Exact Matching" to "Semantic Evaluation" and "Deterministic Replay."

### **7.1 Deterministic Integration Tests with vcrpy**

To test the integration code (Shopify/Ads logic) without incurring LLM costs or hitting live APIs, we use **Record-Replay Testing**.

Tooling: pytest \+ pytest-recording (wrapper for vcrpy).  
Mechanism:

1. **Record Mode:** The first test run hits the real API (OpenAI/Shopify). The interaction (Request/Response) is saved to a YAML "cassette."  
2. **Replay Mode:** Subsequent runs intercept the HTTP request. If it matches the cassette, the recorded response is returned instantly.

The Non-Determinism Problem:  
LLMs include dynamic fields in their responses (system\_fingerprint, completion\_tokens). Standard vcrpy matching will fail because the "body" of the request/response changes slightly every time.  
Solution: We implement a Custom Matcher for vcrpy. This matcher parses the JSON body of the request and response. It compares the semantic fields (e.g., the generated text) while explicitly ignoring the dynamic fields (timestamp, id, usage). This allows us to "freeze" the interaction for regression testing of the surrounding code.24

### **7.2 Semantic Evaluation: "LLM-as-a-Judge"**

To test the *quality* of the Agent's output (e.g., "Is this ad copy compliant?"), we cannot use simple assertions. We use a stronger LLM (GPT-4) as a Judge.

**Workflow:**

1. **Test:** Agent generates ad copy.  
2. **Evaluation:** The output is passed to the Judge LLM with a Rubric.  
   * *Rubric Prompt:* "Analyze the following ad copy. Score it 0-1 on: Professionalism, Compliance (No false claims), and Brevity."  
3. **Assertion:** The test passes if score \> 0.8.

This "Soft Assertion" allows us to build a CI/CD pipeline that fails if the model quality degrades (e.g., after a prompt change), ensuring that the Agent maintains a high standard of performance.23

### **7.3 User Simulation for End-to-End Testing**

Unit tests isolate components; they don't test the conversation flow. We implement **User Simulators**. A secondary Agent is configured with a persona (e.g., "An indecisive marketing manager") and a goal ("Update the budget, then change it back").

* The Simulator interacts with the System Agent.  
* The framework checks if the System Agent successfully navigated the ambiguity and achieved the correct final state (e.g., Budget \= $500).  
* This "Adversarial Testing" uncovers edge cases in state management that static scripts would miss.26

## ---

**8\. Conclusion**

The integration architecture for the APEG & EcomAgent merger represents a significant advancement in autonomous commerce systems. By rigorously defining the boundaries between human control (N8N/Sheets) and machine execution (Shopify/Ads Agents), we ensure operational safety. By adopting distributed transaction patterns (Bulk Ops, Async Request Sets) and robust observability (OpenTelemetry), we ensure technical scalability. Finally, by acknowledging the probabilistic nature of AI and adapting our testing strategies accordingly, we ensure the long-term reliability of the system. This guide provides the blueprint for a successful, future-proof integration.

#### **Works cited**

1. Automated Web Form Data Collection and Storage to Google Sheets | n8n workflow template, accessed December 28, 2025, [https://n8n.io/workflows/8574-automated-web-form-data-collection-and-storage-to-google-sheets/](https://n8n.io/workflows/8574-automated-web-form-data-collection-and-storage-to-google-sheets/)  
2. How to Access Old and New Versions in Google Sheets Trigger (Row Updated), accessed December 28, 2025, [https://community.n8n.io/t/how-to-access-old-and-new-versions-in-google-sheets-trigger-row-updated/131298](https://community.n8n.io/t/how-to-access-old-and-new-versions-in-google-sheets-trigger-row-updated/131298)  
3. Google Sheets Trigger integrations | Workflow automation with n8n, accessed December 28, 2025, [https://n8n.io/integrations/google-sheets-trigger/](https://n8n.io/integrations/google-sheets-trigger/)  
4. Create Secure Human-in-the-Loop Approval Flows with Postgres and Telegram \- N8N, accessed December 28, 2025, [https://n8n.io/workflows/9039-create-secure-human-in-the-loop-approval-flows-with-postgres-and-telegram/](https://n8n.io/workflows/9039-create-secure-human-in-the-loop-approval-flows-with-postgres-and-telegram/)  
5. bulkOperationRunMutation \- GraphQL Admin \- Shopify Dev Docs, accessed December 28, 2025, [https://shopify.dev/docs/api/admin-graphql/latest/mutations/bulkoperationrunmutation](https://shopify.dev/docs/api/admin-graphql/latest/mutations/bulkoperationrunmutation)  
6. stagedUploadsCreate \- GraphQL Admin \- Shopify Dev Docs, accessed December 28, 2025, [https://shopify.dev/docs/api/admin-graphql/latest/mutations/stageduploadscreate](https://shopify.dev/docs/api/admin-graphql/latest/mutations/stageduploadscreate)  
7. Bulk import data with the GraphQL Admin API \- Shopify Dev Docs, accessed December 28, 2025, [https://shopify.dev/docs/api/usage/bulk-operations/imports](https://shopify.dev/docs/api/usage/bulk-operations/imports)  
8. using bulkOperationRunMutation for productUpdate \- Shopify Community, accessed December 28, 2025, [https://community.shopify.com/t/using-bulkoperationrunmutation-for-productupdate/205533](https://community.shopify.com/t/using-bulkoperationrunmutation-for-productupdate/205533)  
9. Error uploading file after stagedUploadsCreate \- Shopify Community, accessed December 28, 2025, [https://community.shopify.com/t/error-uploading-file-after-stageduploadscreate/147406](https://community.shopify.com/t/error-uploading-file-after-stageduploadscreate/147406)  
10. How to post form data with aiohttp ? \- Apidog, accessed December 28, 2025, [https://apidog.com/blog/aiohtttp-post-from-data/](https://apidog.com/blog/aiohtttp-post-from-data/)  
11. Perform bulk operations with the GraphQL Admin API \- Shopify Dev Docs, accessed December 28, 2025, [https://shopify.dev/docs/api/usage/bulk-operations/queries](https://shopify.dev/docs/api/usage/bulk-operations/queries)  
12. Async and Batch Requests \- Marketing API \- Meta for Developers, accessed December 28, 2025, [https://developers.facebook.com/docs/marketing-api/asyncrequests/](https://developers.facebook.com/docs/marketing-api/asyncrequests/)  
13. Ad Campaign \- Meta for Developers \- Facebook, accessed December 28, 2025, [https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/](https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/)  
14. Shops Ads Marketing API Guidebook \- Meta for Developers, accessed December 28, 2025, [https://developers.facebook.com/docs/fmp-tmp-guides/shop-ads-guidebook/](https://developers.facebook.com/docs/fmp-tmp-guides/shop-ads-guidebook/)  
15. Mutate Best Practices | Google Ads API, accessed December 28, 2025, [https://developers.google.com/google-ads/api/docs/mutating/best-practices](https://developers.google.com/google-ads/api/docs/mutating/best-practices)  
16. how to iterate api loop concurrently with asyncio python \- Stack Overflow, accessed December 28, 2025, [https://stackoverflow.com/questions/79237781/how-to-iterate-api-loop-concurrently-with-asyncio-python](https://stackoverflow.com/questions/79237781/how-to-iterate-api-loop-concurrently-with-asyncio-python)  
17. The REST interface overview | Google Ads API, accessed December 28, 2025, [https://developers.google.com/google-ads/api/rest/overview](https://developers.google.com/google-ads/api/rest/overview)  
18. Instrumentation | OpenTelemetry, accessed December 28, 2025, [https://opentelemetry.io/docs/languages/python/instrumentation/](https://opentelemetry.io/docs/languages/python/instrumentation/)  
19. Manual vs. auto instrumentation OpenTelemetry: Choose what's right \- Cribl, accessed December 28, 2025, [https://cribl.io/blog/manual-vs-auto-instrumentation-opentelemetry-choose-whats-right/](https://cribl.io/blog/manual-vs-auto-instrumentation-opentelemetry-choose-whats-right/)  
20. LLM Observability: Tutorial & Best Practices, accessed December 28, 2025, [https://www.patronus.ai/llm-testing/llm-observability](https://www.patronus.ai/llm-testing/llm-observability)  
21. mardiros/purgatory: A circuit breaker implementation for asyncio \- GitHub, accessed December 28, 2025, [https://github.com/mardiros/purgatory](https://github.com/mardiros/purgatory)  
22. arlyon/aiobreaker: Python implementation of the Circuit Breaker pattern. \- GitHub, accessed December 28, 2025, [https://github.com/arlyon/aiobreaker](https://github.com/arlyon/aiobreaker)  
23. How We Are Testing Our Agents in Dev | Towards Data Science, accessed December 28, 2025, [https://towardsdatascience.com/how-we-are-testing-our-agents-in-dev/](https://towardsdatascience.com/how-we-are-testing-our-agents-in-dev/)  
24. vcrpy \- PyPI, accessed December 28, 2025, [https://pypi.org/project/vcrpy/1.7.3/](https://pypi.org/project/vcrpy/1.7.3/)  
25. Custom VCR matchers for dealing with mutable HTTP-requests | Railsware Blog, accessed December 28, 2025, [https://railsware.com/blog/custom-vcr-matchers-for-dealing-with-mutable-http-requests/](https://railsware.com/blog/custom-vcr-matchers-for-dealing-with-mutable-http-requests/)  
26. 4 Testing Frameworks for AI Agents When Traditional QA Fails | Datagrid, accessed December 28, 2025, [https://datagrid.com/blog/4-frameworks-test-non-deterministic-ai-agents](https://datagrid.com/blog/4-frameworks-test-non-deterministic-ai-agents)  
27. From Scenario to Finished: How to Test AI Agents with Domain-Driven TDD \- LangWatch, accessed December 28, 2025, [https://langwatch.ai/blog/from-scenario-to-finished-how-to-test-ai-agents-with-domain-driven-tdd](https://langwatch.ai/blog/from-scenario-to-finished-how-to-test-ai-agents-with-domain-driven-tdd)