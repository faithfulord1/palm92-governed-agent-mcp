import unittest
from src.governed_agent import Decision, Request, evaluate_policy, process


def req(action="draft_summary", tool="draft_report", evidence=None):
    return Request("T-1", "tester", "test", action, tool, "target", ["EV-1"] if evidence is None else evidence)


class GovernanceTests(unittest.TestCase):
    def test_low_risk_allowed(self):
        self.assertEqual(evaluate_policy(req()).decision, Decision.ALLOW)

    def test_high_risk_requires_review(self):
        self.assertEqual(evaluate_policy(req("send_payment", "payment_api")).decision, Decision.REVIEW)

    def test_human_can_reject(self):
        result = process(req("send_payment", "payment_api"), reviewer="reviewer-1", approved=False)
        self.assertEqual(result["final_state"], "DENY")
        self.assertEqual(result["execution"], "BLOCKED")

    def test_missing_evidence_blocks(self):
        self.assertEqual(evaluate_policy(req(evidence=[])).decision, Decision.INSUFFICIENT_EVIDENCE)

    def test_prohibited_action_denied(self):
        self.assertEqual(evaluate_policy(req("disable_audit")).decision, Decision.DENY)

    def test_unknown_tool_denied(self):
        self.assertEqual(evaluate_policy(req(tool="unknown_tool")).decision, Decision.DENY)


if __name__ == "__main__":
    unittest.main()
