"""Visual Streamlit demo for the Palm92 governed-agent prototype."""
import json
import streamlit as st
from src.governed_agent import Request, process

st.set_page_config(page_title="Palm92 Governed Agent", page_icon="🛡️", layout="wide")
st.title("Palm92 Governed Agent MCP")
st.caption("AI investigates. Humans decide.")
st.info("Portfolio prototype using synthetic/demo inputs. It does not execute external actions.")

with st.sidebar:
    st.header("Governance request")
    request_id = st.text_input("Request ID", "DEMO-001")
    requester = st.text_input("Requester", "demo-user")
    purpose = st.text_input("Purpose", "Review a proposed action")
    action = st.selectbox("Action", ["draft_summary", "send_payment", "change_access", "disable_audit"])
    tool = st.selectbox("Tool", ["draft_report", "payment_api", "access_admin", "unknown_tool"])
    target = st.text_input("Target", "synthetic-case")
    evidence = st.text_input("Evidence IDs (comma separated)", "EV-001,EV-002")

req = Request(request_id, requester, purpose, action, tool, target,
              [x.strip() for x in evidence.split(",") if x.strip()])
initial = process(req)

c1, c2, c3 = st.columns(3)
c1.metric("Policy decision", initial["policy"]["decision"])
c2.metric("Final state", initial["final_state"])
c3.metric("Execution", initial["execution"])

st.subheader("Policy result")
st.write(initial["policy"]["reason"])
st.code(initial["policy"]["rule_id"])

result = initial
if initial["policy"]["decision"] == "REVIEW":
    st.warning("This action is paused. A human decision is required.")
    reviewer = st.text_input("Reviewer ID", "human-reviewer")
    left, right = st.columns(2)
    if left.button("Approve", type="primary"):
        result = process(req, reviewer=reviewer, approved=True)
    if right.button("Reject"):
        result = process(req, reviewer=reviewer, approved=False)

st.subheader("Audit record")
st.json(result)
st.download_button("Download audit record", json.dumps(result, indent=2),
                   file_name=f"{request_id}-audit.json", mime="application/json")

st.divider()
st.markdown("**Control path:** Request → Evidence → Policy check → Human approval when required → Simulated action → Audit record")
