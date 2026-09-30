# Governance Controls

| Control | Purpose | Evidence |
|---|---|---|
| Request identity and purpose | Establish why the workflow is running | Request record |
| Least-privilege tool access | Reduce unnecessary agent authority | Tool allow-list / permissions |
| Evidence provenance | Make source material traceable | Evidence metadata |
| Policy gate | Apply explicit constraints before action | Policy evaluation record |
| Human approval | Keep consequential decisions accountable | Approval/rejection event |
| Audit logging | Reconstruct the workflow | Timestamped audit events |
| Data minimisation | Limit unnecessary personal/sensitive data | Input/schema rules |
| Failure/escalation path | Prevent silent action under uncertainty | REVIEW / DENY / INSUFFICIENT_EVIDENCE state |

## Human review

Human review should show the proposed action, supporting evidence, policy result, risk flags and known uncertainty. Approval should be explicit and attributable rather than inferred from silence.

## Current limitations

This is a portfolio prototype. Controls described here still require implementation and testing before any production use.
