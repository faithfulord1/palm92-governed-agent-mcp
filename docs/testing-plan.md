# Testing Plan

The prototype will be tested with scenarios that exercise both functionality and governance.

## Required scenarios

1. **Allowed low-risk request** — sufficient evidence, policy allows execution.
2. **Human approval required** — agent proposes an action but execution remains blocked.
3. **Denied request** — explicit policy prevents the tool call.
4. **Missing evidence** — system returns INSUFFICIENT_EVIDENCE.
5. **Conflicting evidence** — workflow escalates rather than silently choosing a source.
6. **Prompt-injection attempt** — untrusted evidence cannot override the governance layer.
7. **Unauthorised reviewer** — approval attempt is rejected.
8. **Audit reconstruction** — events are sufficient to explain request, evidence, decision and outcome.

## Evidence to retain

For each test: scenario ID, input, evidence IDs, policy result, proposed action, reviewer decision where applicable, final state, timestamps and expected-versus-actual result.
