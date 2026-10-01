"""Deployment-ready Palm92 Governed Agent web + MCP application.

Endpoints:
- /        Reviewer-friendly visual demo
- /api/evaluate  JSON governance evaluation for the visual demo
- /mcp     Stateless Streamable HTTP MCP endpoint
- /health  Lightweight deployment health check

External consequential actions remain simulated by design.
"""
from __future__ import annotations

import html
import json

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from src.governed_agent import Request, evaluate_policy, process

mcp = MCPServer("Palm92 Governed Agent")


@mcp.tool()
def evaluate_action(
    request_id: str,
    requester: str,
    purpose: str,
    action: str,
    tool: str,
    target: str,
    evidence_ids: list[str],
) -> dict:
    """Evaluate a proposed action against deterministic Palm92 governance controls."""
    req = Request(request_id, requester, purpose, action, tool, target, evidence_ids)
    result = evaluate_policy(req)
    return {
        "decision": result.decision.value,
        "reason": result.reason,
        "rule_id": result.rule_id,
    }


@mcp.tool()
def create_governance_record(
    request_id: str,
    requester: str,
    purpose: str,
    action: str,
    tool: str,
    target: str,
    evidence_ids: list[str],
) -> dict:
    """Create a traceable governance record without executing an external action."""
    req = Request(request_id, requester, purpose, action, tool, target, evidence_ids)
    return process(req)


@mcp.tool()
def record_human_decision(
    request_id: str,
    requester: str,
    purpose: str,
    action: str,
    tool: str,
    target: str,
    evidence_ids: list[str],
    reviewer: str,
    approved: bool,
) -> dict:
    """Record explicit human approval or rejection for a governed request."""
    req = Request(request_id, requester, purpose, action, tool, target, evidence_ids)
    return process(req, reviewer=reviewer, approved=approved)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: StarletteRequest) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": "Palm92 Governed Agent MCP",
            "mcp_endpoint": "/mcp",
            "execution_mode": "simulated",
        }
    )


@mcp.custom_route("/api/evaluate", methods=["POST"])
async def api_evaluate(request: StarletteRequest) -> JSONResponse:
    body = await request.json()
    req = Request(
        str(body.get("request_id", "DEMO-001")),
        str(body.get("requester", "demo-user")),
        str(body.get("purpose", "Review a proposed action")),
        str(body.get("action", "draft_summary")),
        str(body.get("tool", "draft_report")),
        str(body.get("target", "synthetic-case")),
        [str(x) for x in body.get("evidence_ids", ["EV-001"]) if str(x).strip()],
    )
    reviewer = body.get("reviewer")
    approved = body.get("approved")
    result = process(req, reviewer=reviewer, approved=approved)
    return JSONResponse(result)


@mcp.custom_route("/", methods=["GET"])
async def homepage(_: StarletteRequest) -> HTMLResponse:
    page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Palm92 Governed Agent MCP</title>
<style>
:root{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#0f172a;background:#f8fafc}
*{box-sizing:border-box}
body{margin:0}
header{background:#0f172a;color:#fff;padding:28px 22px}
.wrap{max-width:1100px;margin:auto}
.badge{display:inline-block;padding:6px 10px;border-radius:999px;background:#1e293b;font-size:12px}
h1{margin:10px 0 4px;font-size:clamp(28px,5vw,48px)}
.lead{color:#cbd5e1;max-width:760px}
main{padding:28px 22px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:18px;padding:20px;box-shadow:0 10px 30px rgba(15,23,42,.05)}
label{display:block;font-size:13px;font-weight:700;margin:12px 0 6px}
input,select,textarea,button{width:100%;padding:11px 12px;border-radius:10px;border:1px solid #cbd5e1;font:inherit}
button{border:0;background:#0f172a;color:white;font-weight:700;cursor:pointer;margin-top:14px}
button.secondary{background:#334155}
button.danger{background:#991b1b}
pre{white-space:pre-wrap;word-break:break-word;background:#020617;color:#d1fae5;padding:16px;border-radius:12px;min-height:280px}
.flow{font-weight:700;line-height:1.8;color:#334155}
.status{font-size:34px;font-weight:800;margin:8px 0}
.small{font-size:13px;color:#64748b}
@media(max-width:780px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <span class="badge">PUBLIC PORTFOLIO PROTOTYPE</span>
    <h1>Palm92 Governed Agent MCP</h1>
    <p class="lead">AI investigates. Humans decide. A human-in-the-loop governance demonstration for Agentic AI, policy enforcement, evidence traceability and auditability.</p>
  </div>
</header>
<main class="wrap">
  <div class="grid">
    <section class="card">
      <h2>Governance request</h2>
      <label>Action</label>
      <select id="action">
        <option value="draft_summary">draft_summary</option>
        <option value="send_payment">send_payment</option>
        <option value="change_access">change_access</option>
        <option value="disable_audit">disable_audit</option>
      </select>
      <label>Tool</label>
      <select id="tool">
        <option value="draft_report">draft_report</option>
        <option value="payment_api">payment_api</option>
        <option value="access_admin">access_admin</option>
        <option value="unknown_tool">unknown_tool</option>
      </select>
      <label>Evidence IDs</label>
      <input id="evidence" value="EV-001,EV-002" />
      <button onclick="runCase()">Evaluate request</button>
      <div id="approval" style="display:none">
        <label>Human reviewer</label>
        <input id="reviewer" value="human-reviewer" />
        <button class="secondary" onclick="decide(true)">Approve</button>
        <button class="danger" onclick="decide(false)">Reject</button>
      </div>
    </section>
    <section class="card">
      <h2>Decision</h2>
      <div id="decision" class="status">READY</div>
      <div id="reason" class="small">Run a synthetic request to inspect the governance path.</div>
      <p class="flow">Request → Evidence → Policy check → Human approval when required → Simulated action → Audit record</p>
      <p class="small">MCP endpoint: <code>/mcp</code> · Health check: <code>/health</code></p>
    </section>
  </div>
  <section class="card" style="margin-top:20px">
    <h2>Structured audit record</h2>
    <pre id="output">{ "status": "waiting" }</pre>
  </section>
</main>
<script>
let lastBody = null;
function baseBody(){
  return {
    request_id:"DEMO-001",
    requester:"portfolio-reviewer",
    purpose:"Review a governed agent action",
    action:document.getElementById("action").value,
    tool:document.getElementById("tool").value,
    target:"synthetic-case",
    evidence_ids:document.getElementById("evidence").value.split(",").map(x=>x.trim()).filter(Boolean)
  };
}
async function send(body){
  const res = await fetch("/api/evaluate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const data = await res.json();
  lastBody = body;
  document.getElementById("decision").textContent = data.final_state;
  document.getElementById("reason").textContent = data.policy.reason + " · " + data.policy.rule_id;
  document.getElementById("output").textContent = JSON.stringify(data,null,2);
  document.getElementById("approval").style.display = data.policy.decision === "REVIEW" && !data.approval ? "block" : "none";
}
function runCase(){ send(baseBody()); }
function decide(approved){
  const body = {...(lastBody || baseBody()), reviewer:document.getElementById("reviewer").value, approved};
  send(body);
}
</script>
</body>
</html>"""
    return HTMLResponse(page)


security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
    transport_security=security,
)
