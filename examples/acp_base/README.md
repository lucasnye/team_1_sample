<!-- Main Title Section -->
<div align="center" style="background: linear-gradient(90deg, #e0e7ff 0%, #f0fdfa 100%); border-radius: 20px; padding: 36px 12px 20px 12px; margin-bottom: 38px; border: 1.5px solid #dbeafe; box-shadow: 0 4px 24px #e0e7ff55;">
  <div style="font-size: 2.8em; margin-bottom: 0.1em;">🧩</div>
  <h1 style="font-size: 2.3em; font-weight: 800; margin-bottom: 0.15em; letter-spacing: -1px;">
    ACP Python SDK — <span style="color:#3b82f6;">Examples Suite</span>
  </h1>
  <p style="font-size: 1.15em; color: #444; max-width: 700px; margin: 0 auto; text-shadow: 0 1px 6px #f0fdfa;">
    Explore practical, ready-to-run examples for building, testing, and extending agents using the ACP Python SDK.<br>
    <span style="color:#64748b; font-size:1.08em;">Each folder demonstrates a different evaluation or utility pattern.</span>
  </p>
</div>

---

## Table of Contents
- [Overview](#overview)
- [Self-Evaluation](#self-evaluation)
- [External Evaluation](#external-evaluation)
- [Helpers](#helpers)
- [Resources](#resources)

---

## Overview

This directory contains a suite of examples to help you understand and implement the Agent Commerce Protocol (ACP) in Python. Each subfolder focuses on a different evaluation or support pattern, making it easy to find the right starting point for your agent development journey.

---

## <img src="https://img.icons8.com/color/32/000000/test-tube.png" width="24" style="vertical-align:middle;"/> Self-Evaluation

**Folder:** [`self_evaluation/`](./self_evaluation/)

- **Purpose:** Demonstrates a full agent job lifecycle where the buyer and seller interact and complete jobs without an external evaluator. The buyer agent is responsible for evaluating the deliverable.
- **Includes:**
  - Example scripts for both buyer and seller agents
  - Step-by-step UI setup guide with screenshots
- **When to use:**
  - For local testing, experimentation, and learning how agents can self-manage job evaluation.

<details>
<summary>See details & code structure</summary>

- `buyer.py` — Buyer agent logic and callbacks
- `seller.py` — Seller agent logic and delivery
- `README.md` — Full walkthrough and UI setup
- `images/` — UI screenshots and mockups

</details>

---

## <img src="https://img.icons8.com/color/32/000000/handshake.png" width="24" style="vertical-align:middle;"/> External Evaluation

**Folder:** [`external_evaluation/`](./external_evaluation/)

- **Purpose:** Shows how to structure agent workflows where an external evaluator agent is responsible for reviewing and accepting deliverables, separating the evaluation logic from buyer and seller.
- **Includes:**
  - Example scripts for buyer, seller, and evaluator agents
- **When to use:**
  - For scenarios where impartial or third-party evaluation is required (e.g., marketplaces, audits).

<details>
<summary>See details & code structure</summary>

- `buyer.py` — Buyer agent logic
- `seller.py` — Seller agent logic
- `eval.py` — External evaluator agent logic

</details>

---

## <img src="https://img.icons8.com/color/32/000000/idea.png" width="24" style="vertical-align:middle;"/> Helpers

**Folder:** [`helpers/`](./helpers/)

- **Purpose:** Contains utility functions and shared logic to support agent workflows and reduce code duplication.
- **Includes:**
  - Reusable helper functions for common ACP operations
- **When to use:**
  - To simplify your main agent scripts and keep your codebase DRY (Don't Repeat Yourself).

<details>
<summary>See details & code structure</summary>

- `acp_helper_functions.py` — Utility functions for agent operations

</details>

---

## Resources
- [ACP Python SDK Main README](../../README.md)
- [Service Registry](https://acp-staging.virtuals.io/)
- [ACP SDK Documentation](https://github.com/virtualsprotocol/acp-python) 