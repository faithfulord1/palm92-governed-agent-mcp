# Decision Routing Adapter

Palm92 Intelligence treats decision/classification services as replaceable infrastructure, not as the governance authority.

## Contract

Input:

```json
{
  "request_id": "string",
  "action_type": "string",
  "evidence_complete": true,
  "risk_signals": [],
  "policy_context": {}
}
```

Output:

```json
{
  "route": "ALLOW | REVIEW | BLOCK | WAITING",
  "reasons": [],
  "required_approval": false,
  "missing_evidence": []
}
```

## v0.1

Use deterministic rules so the product works independently of preview or unavailable APIs.

## Future adapter

A supported decision/classification API may propose the route, but Palm92 policy remains authoritative. A model/API response cannot override a hard policy block or remove a required human approval.

## Fail-safe

If the decision service is unavailable, malformed, uncertain or unsupported, fall back to deterministic policy rules. If those rules cannot safely resolve the request, return `REVIEW` or `WAITING`, never silent autonomous execution.
