# Palm92 Intelligence v0.1

> **AI investigates. Humans decide.**

Palm92 Intelligence is the umbrella product for evidence-backed, human-governed agentic work. It reuses the existing Governed Agent MCP control layer rather than creating another disconnected prototype.

## Product promise

Turn complex requests into evidence-backed recommendations and controlled actions with explicit approval and an auditable record.

## Core workflow

**Request → Understand → Investigate → Evidence → Recommend → Risk decision → Human approval when required → Action → Audit trail**

## v0.1 modules

1. **Chief of Staff** — priorities, deadlines, follow-ups, jobs, grants, competitions and project status.
2. **Opportunity & Application** — discover and qualify opportunities, prepare evidence and drafts, never submit consequential applications without approval.
3. **GRC Evidence & Vendor** — evidence collection, control checks, third-party review and auditable recommendations.
4. **Verified Request / Approval** — verify important requests, instructions and proposed actions before execution.
5. **Lead Recovery** — investigate missed enquiries, prepare responses and require approval for consequential outbound actions.

## Reusable specialist skills

- Governed AI Education
- GRC Evidence & Guardrail
- Agent Orchestration
- RepoGuard
- Vendor Due Diligence
- Verified Request
- Lead Recovery
- Pension Passport
- JobShield

## Architecture

```text
User / ChatGPT / Web
        |
        v
Palm92 Intelligence
        |
        +--> Chief of Staff
        +--> Specialist skills
        +--> Evidence tools / MCP / APIs
        +--> Computer-use fallback where appropriate
        |
        v
Governance Engine
        |
        +--> evidence completeness
        +--> policy checks
        +--> risk classification
        +--> approval requirement
        |
   +----+----------------+
   |                     |
Low-risk permitted   Approval required / blocked
   |                     |
   v                     v
Action                Human reviewer
   |                     |
   +----------+----------+
              v
          Audit trail
```

## Execution routes

**Plan A:** structured API/plugin/MCP integration.

**Plan B:** governed browser/computer-use execution when a structured integration is unavailable and the action is permitted.

**Plan C:** prepare an evidence packet and human-executable next step when neither route can safely complete the action.

## Decision routing

Palm92 does not depend on any preview-only decision service. v0.1 uses explicit deterministic policy/risk rules. A future decision/classification API can be introduced behind an adapter without changing the governance contract.

Example outcomes:

- `ALLOW` — low-risk action permitted by policy.
- `REVIEW` — human judgment required.
- `BLOCK` — policy, evidence or safety condition prevents action.
- `WAITING` — missing evidence/input.

## Proof standard

No task is marked DONE because it was discussed or drafted.

`DONE` requires a verifiable artifact or outcome such as a commit, test result, live deployment, submitted application, sent approved communication, accepted contribution, interview, user/pilot evidence or revenue event.

## Daily operating states

- DONE
- IN PROGRESS
- BLOCKED
- NEED YOUR APPROVAL
- NEXT

An unfinished item must record the concrete blocker and its Plan A / Plan B / Plan C route.

## Distribution target

Palm92 Intelligence is designed to become a globally discoverable ChatGPT-native product/plugin plus a normal web-accessible product, rather than remaining a private portfolio demo.

## Commercial direction

- Entry: basic investigation and evidence packet
- Professional: deeper investigations, case history and exports
- Business: team approvals, integrations, audit trails and dashboards
- Specialist: governed risk/compliance modules

## Product boundary

Palm92 Intelligence is not a substitute for legal, financial, regulatory, employment or security advice. Consequential actions remain subject to policy and human approval.
