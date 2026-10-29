# Evidence fingerprint repair, 29 October 2026

The old delimiter encoding gave the same fingerprint for distinct ID lists:
`["A|B", "C"]` and `["A", "B|C"]`. Reproduced locally before editing.

The new encoding hashes the sorted JSON list, preserving boundaries and duplicate
IDs. Audit schema 0.2 explicitly labels the format. Historical schema 0.1 hashes
must not be compared with the new format or silently rewritten.

Four regression tests cover delimiter ambiguity, ordering, duplicates, empty
values and audit versioning. This remains a truncated 64-bit correlation hint,
not a signature, tamper-proof log or proof of evidence content or provenance.
No approval rules, secrets, network calls or production deployment were changed.

Plan A: review the draft and run repository CI before merge. Plan B: run the
dependency-free tests locally with `python -m unittest discover -s tests -p
'test_evidence_fingerprint.py' -v` when hosting is unavailable.
