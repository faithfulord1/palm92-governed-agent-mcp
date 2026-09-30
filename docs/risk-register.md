# Initial Risk Register

| Risk | Example | Planned control |
|---|---|---|
| Excessive agent authority | Agent can invoke a sensitive tool without review | Least privilege + policy gate |
| Hallucinated evidence | Agent cites information that was never retrieved | Evidence IDs and provenance |
| Prompt injection | Retrieved content tries to override policy | Separate untrusted content from control instructions |
| Unauthorised approval | Wrong person approves an action | Reviewer identity/role checks |
| Missing audit evidence | Action cannot be reconstructed later | Structured audit events |
| Sensitive-data exposure | Unnecessary personal data enters prompts/logs | Data minimisation and redaction |
| Automation bias | Reviewer accepts agent output without scrutiny | Evidence-first review interface |
| Policy ambiguity | Rule cannot determine a safe outcome | Escalate to human review |
