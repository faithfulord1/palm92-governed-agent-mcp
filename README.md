# Palm92 Governed Agent MCP

**Human-in-the-loop Agentic AI and MCP governance prototype for risk, compliance, evidence verification, policy checks, human approval and audit trails.**

> **AI investigates. Humans decide.**

## Why this project exists

AI agents can search, reason and use tools, but consequential actions need governance. This project demonstrates a practical control layer around an agentic workflow so that evidence is traceable, policy is checked, sensitive actions can be stopped for human approval, and decisions can be audited.

## Core workflow

**Request → Evidence → Agent investigation → Policy check → Risk classification → Human approval (when required) → Action → Audit trail**

The prototype is designed around five questions:

1. What is the agent being asked to do?
2. What evidence supports its proposed action?
3. Which policy or control applies?
4. Does a human need to approve the action?
5. Can the final decision be reconstructed later?

## Governance controls

- **Evidence provenance** — record the source and context used by the agent.
- **Least privilege** — tools should expose only the access required for the task.
- **Policy checks** — evaluate proposed actions against explicit rules.
- **Human-in-the-loop approval** — consequential actions pause for review.
- **Audit logging** — preserve request, evidence, checks, approvals and outcomes.
- **Data minimisation** — avoid collecting unnecessary sensitive information.
- **Fail-safe behaviour** — uncertainty or missing evidence can trigger escalation rather than silent execution.

## MCP and agentic AI

The project explores how Model Context Protocol (MCP)-style tool access can be governed rather than treated as unrestricted automation. The intended pattern is:

```text
User / System Request
        |
        v
Governed Agent
        |
        +--> Evidence tools
        +--> MCP / external tools
        |
        v
Policy & Risk Gate
        |
   +----+----+
   |         |
 Low risk   Approval required
   |         |
   v         v
 Action    Human reviewer
              |
              v
            Action
              |
              v
          Audit record
```

## Example use cases

- GRC evidence collection and verification
- Third-party risk review
- Access-control evidence review
- Fraud and verified-request workflows
- AI governance approval gates
- Compliance case preparation

## Project status

**Status: Early prototype / portfolio build**

This repository documents an evolving prototype. It is not presented as a production compliance platform and does not replace legal, regulatory, financial or security advice.

## Planned repository structure

```text
docs/
  architecture.md
  governance-controls.md
  risk-register.md
  testing-plan.md
examples/
  sample-evidence.json
  sample-audit-record.json
src/
  agent/
  policy/
  approval/
  audit/
```

## Roadmap

- [x] Define the governed-agent problem and control objectives
- [x] Document the human-in-the-loop workflow
- [ ] Add sample policy and evidence schemas
- [ ] Implement policy/risk gate
- [ ] Implement human approval state
- [ ] Implement append-only audit event model
- [ ] Add MCP tool demonstration
- [ ] Add test scenarios for allowed, denied and escalated actions
- [ ] Document limitations and threat model
- [ ] Record a short end-to-end demonstration

## Recruiter / reviewer walkthrough

A reviewer should be able to use this repository to assess practical thinking across:

**AI Governance · GRC · Risk & Compliance · Agentic AI · MCP · Human-in-the-Loop Controls · Evidence Traceability · Auditability · Responsible AI**

## Palm92 Intelligence

Palm92 Intelligence builds practical, human-governed AI concepts around real-world risk, compliance, trust and operational problems.

**Principle:** AI investigates. Humans decide.

---

**Project owner:** Faith Wright  
**Portfolio:** Palm92 Intelligence
