The Automated Zero-Trust Support Agent Architecture (v2.0) is designed to provide a secure and efficient support system using a Hexagonal (Ports & Adapters) / Clean Architecture pattern. The system will be built using Python 3.11+ and the LangGraph framework.

### 1. Global System Topology

The architecture consists of three main agents: Advisor, Ticket Router, and SOP Generator. The system is designed to decouple runtime execution from authorization controls across two completely independent agent lifecycles, structured via an out-of-band automated continuous learning data pipeline.

#### User Support Request
The system starts with a user support request, which can be in JSON or Markdown format.

#### Agent 1: Advisor (LLM)
- **Functionality**: The Advisor uses a Large Language Model (LLM) to match user symptoms with technical documentation indexed from the system's vector database.
- **Inputs**: User support request (JSON or Markdown).
- **Outputs**: Action ID / Confidence Score.

#### Async Backend Validation
- **Functionality**: Validates the user's request and checks their RBAC permissions via the MCP Layer.
- **Inputs**: Action ID / Confidence Score.
- **Outputs**: Verifies user permissions.

#### UI: Render Secure Action
- **Functionality**: Renders a secure action based on the validated request.
- **Inputs**: Action ID / Confidence Score.
- **Outputs**: Secure action rendered to the user.

#### User clicks 'Create Ticket'
- **Functionality**: Initiates the creation of a support ticket.
- **Inputs**: User input.
- **Outputs**: Ticket creation initiated.

#### Agent 2: Ticket Router
- **Functionality**: Assigns ticket payloads to the correct engineering queue using pure zero-shot classification.
- **Inputs**: User messages and structured footprint metadata.
- **Outputs**: Ticket assigned to the correct queue.

#### L2 Operations
- **Functionality**: Engineers resolve and complete RCA.
- **Inputs**: Ticket details.
- **Outputs**: Ticket resolved.

#### L3 Core Devs
- **Functionality**: Engineers resolve and complete RCA.
- **Inputs**: Ticket details.
- **Outputs**: Ticket resolved.

#### Jira / SNOW Webhook
- **Functionality**: Sends ticket details to Jira or ServiceNow.
- **Inputs**: Ticket details.
- **Outputs**: Ticket created in Jira/SNOW.

#### Agent 3: SOP Generator
- **Functionality**: Generates Standard Operating Procedures (SOPs) based on resolved support tickets.
- **Inputs**: Raw customer conversation logs and human engineer's RCA notes.
- **Outputs**: SOPs in Markdown format.

### 2. Architectural Layer Matrix & Tooling Stack

#### Architecture Layer	Core Component / Tool	Free-Tier / Sandbox Access Strategy
- **Inbound Driving Adapter**: Microsoft Teams Chatbot - Microsoft 365 Developer Program: Free renewable 90-day E5 developer tenant. Built using the VS Code Teams Toolkit.
- **Inbound Development Adapter**: Local CLI Test Harness - Native Standard I/O (Terminal Loop). Requires zero accounts or tokens.
- **Agentic Framework**: LangGraph / LangChain - Open-source Python package (pip install langgraph).
- **Inference Compute**: Groq Developer Cloud / Google AI Studio - Free Developer API keys for high-throughput execution (llama-3.1-70b or Gemini 1.5 Flash).
- **Knowledge Base Retrieval**: ChromaDB (Local / In-Memory) - Open-source Vector Database running natively inside process memory.
- **Outbound Driven Adapter**: Jira Cloud API - Atlassian Developer Cloud: Free instance up to 3 users with native REST API/token access.
- **Security Layer**: Model Context Protocol (MCP) - Open-source SDK by Anthropic used to isolate role-based access authorization boundaries.
- **Persistence Layer**: Supabase (PostgreSQL) - Managed Free Cloud Tier providing permanent storage for Outlier Records and Audit Logs.
- **Observability Sinks**: LangSmith - Free Developer Tier for trace profiling, latency calculation, and Golden Dataset generation.

### 3. Step-by-Step Implementation & Configuration Steps

#### Phase 1: Local In-Memory Validation Engine
1. Create the directory tree structure matching the Section 3 specification precisely on your local file system.
2. Initialize a local virtual environment: `python -m venv venv && source venv/bin/activate`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy the code blocks from Section 4 into their matching file locations.
5. Run `python main.py` to verify the application bootstraps and routes execution to the mock ticket system without dependencies online.

#### Phase 2: Open External Ticketing Sandbox (Jira)
1. Sign up for a free sandbox instance via the Atlassian Developer Portal.
2. Create an empty service project using the standard template (Jira Service Management).
3. Generate an API Auth Token under your Atlassian Profile Security settings.
4. Replace `adapters/outbound/mock_ticket_adapter.py` with a live JiraAdapter utilizing the requests library targeting `https://atlassian.net`.

#### Phase 3: Connect User Interaction Endpoint (Teams)
1. Register for the Microsoft 365 Developer Program to get a free Office 365 Tenant license.
2. Install the Teams Toolkit extension within VS Code.
3. Scaffold a new automated custom bot application wrapper. Connect the incoming message router execution functions directly to your ports/inbound/chat_usecase.py boundary hooks.

### 4. System Prompt Manifests

#### Agent 1: Advisor Prompt Template
```text
SYSTEM: You are a Zero-Trust System Optimization Advisor. Your core responsibility is to match user symptoms with technical documentation indexed from the system's vector database.
CRITICAL CONSTRAINT: You cannot execute scripts or modify resources. You are strictly advisory.
INSTRUCTIONS:
1. Examine the retrieved context blocks for specific "Action Script IDs".
2. If a highly confident match is established, output the corresponding Action Script ID and raw parameters.
3. If no clear documentation exists or context is ambiguous, output an explicit null action field and set the confidence marker to 0.0.
Use code with caution.
```

#### Agent 2: Ticket Router Prompt Template
```text
SYSTEM: You are an isolated IT Escalation Router. Your sole responsibility is to assign ticket payloads to the correct engineering queue.
INPUT DATA BOUNDARIES: You will be passed a text string containing raw user messages and a structured footprint metadata bundle generated by an upstream advisor agent.
CLASSIFICATION MATRIX RULES:
- Target 'L2_OPERATIONS' if: The issue involves user configurations, account resets, infrastructure reboots, data synchronization runs, or access credential adjustments.
- Target 'L3_BUG_FIX' if: The user messages contain core application crashes, unhandled code exceptions, 5xx server HTTP errors, database table corruption patterns, or if the upstream advisor metadata confirms an automated fix was attempted but failed to clear the error.
Use code with caution.
```

#### Agent 3: Continuous Learning SOP Generator Prompt Template
```text
SYSTEM: You are an automated Technical Documentation Synthesis Engine. Your job is to process resolved support tickets and format them into searchable Standard Operating Procedures (SOPs).
INPUT PAYLOAD STRUCTURE: You will receive the raw customer conversation logs along with a human engineer's confirmed Root Cause Analysis (RCA) notes.
OUTPUT SYNTAX RULES: Transform raw engineering logs into clean, structural markdown documents. Standardize sections explicitly to match:
# TITLE: SOP-X [Descriptive Issue Name]
## SYMPTOMS: [Bullet points mapping user-facing error indicators]
## ROOT CAUSE: [Technical breakdown explaining why the error triggers]
## RESOLUTION ACTIONS: [Sequential operational steps required to remediate the systemic state]
Use code with caution.
```

### 5. Additional Notes

- The "Mock Ticket System" in Phase 1 will perform basic validation.
- The "Central Observability & Audit Data Lake" will be integrated with the existing system.
- The "Golden Dataset & Automated Evaluation Simulator" will be updated manually.
- The "Security Layer" can be tested by manually trying with accounts of different access levels.
- The "User Support Request" can be in JSON or Markdown format.
- The "Agent 2: Ticket Router" will default to "L2 Operations" if the issue cannot be classified into either category.
- The "Agent 3: SOP Generator" will handle cases where the raw customer conversation logs do not contain enough information by generating a generic SOP template.