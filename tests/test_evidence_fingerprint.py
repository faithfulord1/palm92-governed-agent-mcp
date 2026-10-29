import unittest

from src.governed_agent import Request, evidence_fingerprint, process


class FingerprintTests(unittest.TestCase):
    def test_delimited_ids_do_not_alias_a_different_list(self):
        self.assertNotEqual(evidence_fingerprint(['A|B', 'C']),
                            evidence_fingerprint(['A', 'B|C']))

    def test_order_is_independent_but_duplicates_are_preserved(self):
        self.assertEqual(evidence_fingerprint(['B', 'A']), evidence_fingerprint(['A', 'B']))
        self.assertNotEqual(evidence_fingerprint(['A']), evidence_fingerprint(['A', 'A']))

    def test_empty_list_and_empty_id_are_distinct(self):
        self.assertNotEqual(evidence_fingerprint([]), evidence_fingerprint(['']))

    def test_audit_identifies_changed_fingerprint_format(self):
        req = Request('fictional-1', 'tester', 'test', 'draft_summary', 'draft_report', 'demo', ['EV-1'])
        event = process(req)
        self.assertEqual(event['schema_version'], '0.2')
        self.assertEqual(event['evidence_fingerprint_format'], 'sorted-json-sha256-64bit-v1')
        self.assertEqual(event['evidence_fingerprint'], evidence_fingerprint(req.evidence_ids))


if __name__ == '__main__':
    unittest.main()
