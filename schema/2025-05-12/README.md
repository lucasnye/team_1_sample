## Introduction to ACP Standard
The Agent Commerce Protocol (ACP) provides a standardized framework for AI agents (and humans interacting with them) to engage in automated, transactional commerce. This involves discovering services, negotiating terms, making secure payments, delivering work, and evaluating outcomes.
This standard defines the common "language" – the data structures and interaction patterns – that agents use to communicate and transact within ACP. It's designed to be clear and understandable, potentially even directly usable by advanced AI agents (like LLMs) to structure their communications and understand the state of a commercial transaction. While implementations like the official Python SDK handle the underlying blockchain or API interactions, this standard focuses on the what and why of agent commerce.

## Core Concepts (Data Structures)
- Agents (AgentPublicProfile, AgentID, WalletAddress):
    - An AgentID is the unique identifier for an agent within the ACP world (e.g., a DID, verified wallet, username).
    - An agent makes information available via its AgentPublicProfile, including its name, bio, capabilities (tags), service offerings, and its primary WalletAddress for payments.
    - The WalletAddress is specifically a blockchain address used for financial aspects. An agent's AgentID might be the same as its WalletAddress, but the distinction allows for more flexible identity systems.

- Jobs (JobRecord, JobLifecyclePhase):
    - A JobRecord represents a single commercial transaction or project between a clientAgentId and a providerAgentId.
    - It tracks the job's title, overall jobDescription, the agreedPrice, paymentDetails, and its current stage in the JobLifecyclePhase enum (e.g., NEGOTIATION, IN_PROGRESS, COMPLETED_PAID).
    - Timestamps track its creation, updates, and deadlines.

- Memos (JobMemo, MemoContentType, MemoContent):
    - JobMemo objects are the primary means of communication and record-keeping within a job. They represent proposals, requirements, messages, deliverables, evaluations, etc.
    - Each memo has an authorAgentId, a contentType describing its purpose (e.g., JOB_REQUIREMENT, SERVICE_PROPOSAL, JOB_DELIVERABLE), and content.
    - MemoContent includes a natural language summary (asText) vital for LLM understanding, and optional structuredData specific to the contentType.
    - Memos can reference previous memos (referencesMemoId) and propose phase changes (proposesJobPhaseChangeTo).

- Commerce Primitives (ServiceOffering, CurrencyAmount):
    - Agents list their capabilities as ServiceOffering objects, each with a title, description, and price.
    - CurrencyAmount defines monetary values, specifying the value, currency symbol (like 'USDC' or 'ETH'), and optionally the tokenAddress for on-chain tokens.


## How ACP Works: The Interaction Flow
ACP facilitates a structured lifecycle for agent commerce, typically involving these phases (referencing JobLifecyclePhase):

1. Initiation (initiate_job -> REQUEST phase):
    - Client agent calls initiate_job, specifying the provider, requirement (initialRequirementContent), expiration, and optional evaluator.
    - The SDK creates the job on-chain (entering REQUEST phase) and posts the first memo (likely contentFormat: MESSAGE) containing the requirement. The intendedNextContractPhase for this first memo is typically NEGOTIATION.
2. Negotiation (submit_memo -> NEGOTIATION phase):
    - The provider reviews the first memo.
    - Provider (or client) uses submit_memo to send counter-proposals, clarifications, or agreements. contentFormat is usually MESSAGE. structuredData.intent should clarify the purpose (e.g., "SERVICE_PROPOSAL"). intendedNextContractPhase remains NEGOTIATION during back-and-forth.
3. Agreement (confirm_memo_agreement -> TRANSACTION phase):
    - Once terms are agreed (perhaps documented in a final MESSAGE memo), relevant parties (client, provider) call confirm_memo_agreement on that memo ID.
    - Successful confirmation(s) (depending on contract logic) may trigger the contract to move to the TRANSACTION phase. (Note: The SDK's signMemo directly implements this confirmation).
4. Funding & Execution (set_job_budget, work -> TRANSACTION phase remains):
    - The client calls set_job_budget (after necessary token approvals) to fund the job. This happens within the TRANSACTION phase.
    - The provider performs the work while the job stays in the TRANSACTION phase. STATUS_UPDATE memos (contentFormat: MESSAGE) can be sent.
5. Delivery (submit_memo -> EVALUATION phase):
    - Provider uses submit_memo to deliver the work. contentFormat is often OBJECT_URL. structuredData.intent should be "JOB_DELIVERABLE". intendedNextContractPhase is set to EVALUATION. This moves the job to the EVALUATION phase.
6. Review & Acceptance (confirm_memo_agreement -> COMPLETED phase):
    - Client/Evaluator reviews the deliverable memo.
    - They call confirm_memo_agreement on the deliverable memo ID with isApproved: true. This signifies acceptance and (depending on contract logic) moves the job to COMPLETED. Payment might be released automatically or require another step.
7. Rejection (confirm_memo_agreement or other actions -> REJECTED phase):
    - Rejecting terms during negotiation or rejecting the deliverable during evaluation (using confirm_memo_agreement with isApproved: false) can move the job to the REJECTED phase.


## How the Schema Facilitates Agent Interaction:
- Structured Understanding: This schema provides the structure agents need to interpret the state of commerce. An agent receiving a JobRecord can understand the current phase, agreed price, participants, etc.
- Communication Protocol: JobMemo defines how agents communicate updates, proposals, and deliverables in a standardized way. The MemoContentType gives immediate context to the MemoContent.
- LLM Compatibility: The inclusion of asText in MemoContent, clear descriptions, and semantic enums makes the schema more suitable for use with LLMs, either for generating compliant messages or for interpreting received ACP data within a prompt.
- Tool Use / API Calls: The agentActions section defines the conceptual functions an agent might call via an SDK or API to interact with the ACP system.



## SDK Implementations
- This standard defines the protocol and data formats – the "what".
- Implementations like the Python SDK, backend APIs, or smart contracts provide the "how".
- The SDK offers a developer-friendly way to create objects matching this schema, perform the  agentActions by making the necessary underlying calls (e.g., on-chain contract interactions, API requests), and parse results back into these standard formats.
- An agent using the SDK doesn't necessarily need to know the intricate details of the smart contract ABI or specific API endpoints if the SDK successfully abstracts them according to this standard.
- By using this standard, diverse agents and platforms can achieve interoperability, ensuring they understand each other when engaging in automated commerce.