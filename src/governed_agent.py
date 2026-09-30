"""Minimal governed-agent reference implementation.

This prototype deliberately separates an agent's proposal from authority to act.
No external systems are called. Tool execution is simulated so the governance
flow can be inspected safely.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    DENY = "DENY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class Request:
    request_id: str
    requester: str
    purpose: str
    action: str
    tool: str
    target: str
    evidence_ids: list[str]


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    reason: str
    rule_id: str


HIGH_RISK_ACTIONS = {"send_payment", "delete_record", "publish_external", "change_access"}
PROHIBITED_ACTIONS = {"disable_audit", "exfiltrate_secret"}
ALLOWED_TOOLS = {"evidence_search", "risk_lookup", "draft_report", "payment_api", "access_admin"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate_policy(request: Request) -> PolicyResult:
    if not request.evidence_ids:
        return PolicyResult(Decision.INSUFFICIENT_EVIDENCE, "No evidence supplied.", "EVIDENCE-001")
    if request.action in PROHIBITED_ACTIONS:
        return PolicyResult(Decision.DENY, "Action is prohibited by policy.", "POLICY-001")
    if request.tool not in ALLOWED_TOOLS:
        return PolicyResult(Decision.DENY, "Tool is not on the allow-list.", "TOOL-001")
    if request.action in HIGH_RISK_ACTIONS:
        return PolicyResult(Decision.REVIEW, "Consequential action requires human approval.", "HITL-001")
    return PolicyResult(Decision.ALLOW, "Low-risk action may proceed.", "AUTO-001")


def evidence_fingerprint(evidence_ids: list[str]) -> str:
    payload = "|".join(sorted(evidence_ids)).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def process(request: Request, reviewer: str | None = None, approved: bool | None = None) -> dict[str, Any]:
    policy = evaluate_policy(request)
    final = policy.decision
    approval = None

    if policy.decision == Decision.REVIEW:
        if reviewer is None or approved is None:
            final = Decision.REVIEW
        else:
            approval = {"reviewer": reviewer, "approved": approved, "timestamp": utc_now()}
            final = Decision.ALLOW if approved else Decision.DENY

    event = {
        "schema_version": "0.1",
        "timestamp": utc_now(),
        "request": asdict(request),
        "evidence_fingerprint": evidence_fingerprint(request.evidence_ids),
        "policy": {**asdict(policy), "decision": policy.decision.value},
        "approval": approval,
        "final_state": final.value,
        "execution": "SIMULATED" if final == Decision.ALLOW else "BLOCKED",
    }
    return event


def append_audit(event: dict[str, Any], path: str = "audit.jsonl") -> None:
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


if __name__ == "__main__":
    example = Request(
        request_id="REQ-001", requester="demo-user", purpose="Prepare a GRC evidence summary",
        action="draft_summary", tool="draft_report", target="case-001", evidence_ids=["EV-001", "EV-002"]
    )
    result = process(example)
    print(json.dumps(result, indent=2))
