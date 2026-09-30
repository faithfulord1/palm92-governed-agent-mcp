# Architecture

## Objective

Create a small, inspectable reference architecture for an AI agent that can investigate evidence and invoke tools without giving the model unrestricted authority over consequential actions.

## Components

1. **Request intake** — captures the task, requester and declared purpose.
2. **Evidence layer** — retrieves only the information permitted for the task and records provenance.
3. **Agent reasoning layer** — prepares a proposed action and supporting rationale.
4. **Policy and risk gate** — applies deterministic rules and classifies the proposed action.
5. **Approval service** — pauses actions that require human review and records the reviewer decision.
6. **Tool/MCP adapter** — exposes narrowly scoped external capabilities.
7. **Audit logger** — records events needed to reconstruct what happened.

## Decision states

- `ALLOW` — policy permits automated execution.
- `REVIEW` — execution is blocked until an authorised human approves.
- `DENY` — policy prohibits the action.
- `INSUFFICIENT_EVIDENCE` — the system cannot safely decide and requests more evidence.

## Design principle

The model can recommend or propose. Authority is separated from model generation. Controls around the model determine whether a tool call is permitted, requires approval or is denied.
