import unittest
from unittest.mock import patch

from bountyforge.scanner import make_report, normalize_issue, payout_mentions, scan_github


def issue(title="Bounty: $250 to fix parser"):
    return {
        "id": 51,
        "title": title,
        "body": "Acceptance criteria: tests should pass, with enough details to implement correctly. " * 4,
        "html_url": "https://github.com/example/team/issues/17",
    }


class ScannerTests(unittest.TestCase):
    def test_amounts(self):
        self.assertEqual(payout_mentions("Pay $1,200 and USD 30, not $0"), [30, 1200])
        self.assertEqual(payout_mentions("$5k and $1.5K and $250"), [250, 1500, 5000])
        self.assertEqual(payout_mentions("$1m"), [])

    def test_conservative_verification(self):
        candidate = normalize_issue(issue())
        self.assertEqual(candidate["verification"], "unverified_candidate")
        self.assertEqual(candidate["mentioned_amounts_usd"], [250])
        self.assertGreater(candidate["score"], 20)

    def test_rejects_external_links(self):
        raw = issue()
        raw["html_url"] = "https://github.com.evil.test/owner/repo/issues/1"
        self.assertIsNone(normalize_issue(raw))

    def test_rejects_pull_requests(self):
        raw = issue()
        raw["pull_request"] = {"url": "https://api.github.com/repos/other/pulls/1"}
        self.assertIsNone(normalize_issue(raw))

    def test_rejects_invalid_urls(self):
        for url in ("http://github.com/a/b/issues/1", "https://github.com/a/b", "https://github.com/a/b/issues/nope"):
            raw = issue()
            raw["html_url"] = url
            self.assertIsNone(normalize_issue(raw))

    def test_report_never_claims_payment(self):
        report = make_report([normalize_issue(issue())], "unit test")
        self.assertIn("unverified", report["disclaimer"].lower())

    def test_proposals_rank_below_actionable_candidates(self):
        normal = normalize_issue(issue("Bounty: $250 CSV parser fix"))
        proposed = normalize_issue(issue("Bounty proposal: $250 CSV parser fix"))
        self.assertLess(proposed["score"], normal["score"])

    def test_paid_api_requirement_penalty(self):
        normal = normalize_issue(issue("Bounty: $250 CSV parser fix"))
        paid = issue("Bounty: $250 CSV parser fix")
        paid["body"] += " Requires Claude API calls and billing."
        self.assertLess(normalize_issue(paid)["score"], normal["score"])

    def test_application_issue_is_not_a_paid_job(self):
        candidate = normalize_issue(issue("Application: bounty item 27 — Employee Directory ($150)"))
        self.assertLess(candidate["score"], normalize_issue(issue("Bounty: $150 build directory"))["score"])

    def test_gameplay_bounties_are_penalized(self):
        candidate = normalize_issue(issue("When attacking a merchant, there is a bounty on you"))
        self.assertEqual(candidate["score"], 0)

    def test_scan_bounds(self):
        with self.assertRaises(ValueError):
            scan_github(31)
        with self.assertRaises(ValueError):
            scan_github(0)


if __name__ == "__main__":
    unittest.main()
