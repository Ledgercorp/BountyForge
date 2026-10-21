"""Offline contract and negative tests for the read-only prospect worker."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from bountyforge.revenue_scout import GitHubReadOnly, ScoutError, _parse_issue, run, summary, main

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)

def issue(num=1, title='Fix Python bug bounty $125', body='Bounty $125 for regression',
          repository='good/example', state='open'):
    return {'html_url': f'https://github.com/{repository}/issues/{num}',
            'title': title, 'body': body, 'labels': [{'name': 'bounty'}],
            'state': state, 'updated_at': '2026-10-20T11:00:00Z'}

class FakeGitHub:
    def __init__(self, items, language='Python'):
        self.items, self.language, self.calls = items, language, []
    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == '/search/issues':
            return {'items': list(self.items)}
        if path.startswith('/repos/'):
            return {'language': self.language}
        raise AssertionError('Invalid URL')

class ScoutTests(unittest.TestCase):
    def test_advertised_bounty_is_never_verified(self):
        report = run(FakeGitHub([issue()]), now=NOW)
        self.assertEqual(report['prospect_count'], 1)
        candidate = report['prospects'][0]
        self.assertEqual(candidate['advertised_reward_usd'], 125)
        for key in ('payout_verified','execution_authorized','ai_allowed_verified',
                    'external_submission_authorized','eligibility_verified'):
            self.assertIs(candidate[key], False)
        self.assertEqual(report['funds_verified_usd'], 0)
        self.assertEqual(report['external_submissions'], 0)
        self.assertEqual(report['model_calls'], 0)

    def test_dedupe_and_primary_language_filter(self):
        client = FakeGitHub([issue(), issue(1), issue(2)], 'JavaScript')
        self.assertEqual(run(client, now=NOW)['prospect_count'], 0)
        self.assertEqual(sum(p.startswith('/repos/') for p, _ in client.calls), 1)

    def test_untrusted_issue_cannot_become_html_or_a_separate_link(self):
        text = '[Fake](https://evil.test) bounty $100 <script>alert(1)</script>'
        report = run(FakeGitHub([issue(title=text)]), now=NOW)
        markdown = summary(report)
        self.assertIn(r'\]\(https://evil.test\)', markdown)
        self.assertIn(r'\<script\>', markdown)
        self.assertIn('https://github.com/good/example/issues/1', markdown)
        self.assertFalse(report['prospects'][0]['ai_allowed_verified'])

    def test_closed_stale_and_pull_requests_excluded(self):
        closed = issue(state='closed')
        stale = issue(2)
        stale['updated_at'] = '2020-01-01T00:00:00Z'
        pull = issue(3)
        pull['pull_request'] = {'url':'https://github.com/x'}
        self.assertEqual(run(FakeGitHub([closed, stale, pull]), now=NOW)['prospect_count'], 0)

    def test_weak_dollar_language_not_paid_bounty(self):
        row = issue(title='User pays $200 for subscription', body='A paid pricing fix')
        row['labels'] = []
        self.assertIsNone(_parse_issue(row, NOW))

    def test_reader_never_allows_write_endpoints(self):
        client = GitHubReadOnly()
        for path in ('/user', '/repos/owner/repo/issues/1/comments',
                     '/repos/owner/repo/../secrets', '/search/code','/search/issues/hijack'):
            with self.subTest(path=path), self.assertRaises(ScoutError):
                client.get(path)

    def test_api_failure_does_not_mean_no_work(self):
        class Broken:
            def get(self, path, params=None):
                return {'message': 'rate limit exceeded'}
        with self.assertRaises(ScoutError):
            run(Broken(), now=NOW)

    def test_offline_mode_makes_no_network_call(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)/'report.json'
            with patch.object(GitHubReadOnly,'get',side_effect=AssertionError('network')):
                self.assertEqual(main(['--mode','offline','--output',str(output)]),0)
            report = json.loads(output.read_text())
            self.assertEqual(report['kind'],'offline_test_not_live_discovery')
            self.assertEqual(report['model_calls'],0)

if __name__ == '__main__':
    unittest.main()
