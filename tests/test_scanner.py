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

    def test_scan_bounds(self):
        with self.assertRaises(ValueError):
            scan_github(31)
        with self.assertRaises(ValueError):
            scan_github(0)


if __name__ == "__main__":
    unittest.main()
