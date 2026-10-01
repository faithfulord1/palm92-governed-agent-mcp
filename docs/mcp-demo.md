# MCP Demonstration

This repository now contains a real MCP-compatible demonstration server in `mcp_server.py`.

## Exposed tools

- `evaluate_action` — evaluates a proposed action against deterministic governance rules.
- `create_governance_record` — creates a traceable record without executing an external action.
- `record_human_decision` — records explicit approval or rejection for a governed request.

The MCP layer deliberately does **not** expose unrestricted payment, deletion or access-change execution. This demonstrates the project's central control objective: tool connectivity does not automatically grant authority.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python mcp_server.py
```

The server uses the official-style FastMCP interface supplied by the Python MCP SDK. Exact client configuration depends on the MCP host used.

## Governance test

Ask the MCP tool to evaluate a low-risk `draft_summary` request with evidence. It should return `ALLOW`. A `send_payment` request should return `REVIEW`; `disable_audit` should return `DENY`; a request with no evidence should return `INSUFFICIENT_EVIDENCE`.
