"""Palm92 Governed Agent MCP server.

A small MCP-compatible demonstration server. It exposes governance tools, not
unrestricted actions. High-risk requests remain subject to human approval.

Run after installing the optional MCP SDK:
    pip install "mcp[cli]"
    python mcp_server.py
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from src.governed_agent import Request, evaluate_policy, process

mcp = FastMCP("Palm92 Governed Agent")


@mcp.tool()
def evaluate_action(request_id: str, requester: str, purpose: str, action: str,
                    tool: str, target: str, evidence_ids: list[str]) -> dict:
    """Evaluate a proposed action against Palm92 governance controls."""
    req = Request(request_id, requester, purpose, action, tool, target, evidence_ids)
    result = evaluate_policy(req)
    return {"decision": result.decision.value, "reason": result.reason, "rule_id": result.rule_id}


@mcp.tool()
def create_governance_record(request_id: str, requester: str, purpose: str,
                             action: str, tool: str, target: str,
                             evidence_ids: list[str]) -> dict:
    """Create a traceable governance record without executing an external action."""
    req = Request(request_id, requester, purpose, action, tool, target, evidence_ids)
    return process(req)


@mcp.tool()
def record_human_decision(request_id: str, requester: str, purpose: str,
                          action: str, tool: str, target: str,
                          evidence_ids: list[str], reviewer: str,
                          approved: bool) -> dict:
    """Record an explicit human approval/rejection for a governed request."""
    req = Request(request_id, requester, purpose, action, tool, target, evidence_ids)
    return process(req, reviewer=reviewer, approved=approved)


if __name__ == "__main__":
    mcp.run()
