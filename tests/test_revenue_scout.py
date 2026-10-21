"""Offline contract and negative tests for the read-only prospect worker."""
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from bountyforge.revenue_scout import (
    GitHubReadOnly, ScoutError, MAX_RESPONSE_BYTES, MAX_REPO_LOOKUPS,
    _NoRedirect, _parse_issue, run, summary, main,
)

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
            return {'items': list(self.items), 'incomplete_results': False,
                    'total_count': len(self.items)}
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

    def test_thousands_and_compact_k_rewards_are_not_misranked(self):
        examples = [
            issue(11, title='Bounty $1,200 for an isolated Python fix'),
            issue(12, title='Reward $1.5k for an isolated Python fix'),
        ]
        report = run(FakeGitHub(examples), now=NOW)
        by_url = {item['issue_url']: item['advertised_reward_usd']
                  for item in report['prospects']}
        self.assertEqual(by_url['https://github.com/good/example/issues/11'], 1200)
        self.assertEqual(by_url['https://github.com/good/example/issues/12'], 1500)
        self.assertEqual(report['funds_verified_usd'], 0)

    def test_known_unfunded_aggregator_and_absurd_amounts_are_excluded(self):
        candidates = [
            issue(100, repository='zhangjiayang6835-cyber/bounty-plaza',
                  title='Bounty $400 aggregator mirror'),
            issue(101, repository='good/example',
                  title='Bounty $999,999,999,999,999,999 spam'),
            issue(102, repository='good/example',
                  title='Bounty $225 for Python regression'),
        ]
        report = run(FakeGitHub(candidates), now=NOW)
        self.assertEqual([x['issue_url'] for x in report['prospects']],
                         ['https://github.com/good/example/issues/102'])
        self.assertEqual(report['funds_verified_usd'], 0)

    def test_unknown_aggregators_declared_in_repo_metadata_are_excluded(self):
        class Metadata(FakeGitHub):
            def get(self, path, params=None):
                if path == '/repos/working/mirror':
                    self.calls.append((path, params))
                    return {'language':'Python',
                            'description':'Bounty aggregator collecting third-party GitHub issues'}
                return super().get(path, params)
        report = run(Metadata([
            issue(111, repository='working/mirror', title='Bounty $400'),
            issue(112, repository='good/example', title='Bounty $125')
        ]), now=NOW)
        self.assertEqual(report['prospect_count'], 1)
        self.assertIn('/good/example/', report['prospects'][0]['issue_url'])

    def test_filters_12_high_scoring_mirrors_before_the_primary_source(self):
        mirrors = [issue(i, repository='zhangjiayang6835-cyber/bounty-plaza',
                         title='Bounty $400 mirrored issue') for i in range(1, 13)]
        original = issue(101, repository='zzzzzz/original', title='Bounty $125 Python fix')
        report = run(FakeGitHub(mirrors + [original]), now=NOW)
        self.assertEqual(report['prospect_count'], 1)
        self.assertEqual(report['prospects'][0]['issue_url'],
                         'https://github.com/zzzzzz/original/issues/101')

    def test_no_advertised_money_is_not_a_revenue_prospect(self):
        educational = issue(404, repository='lessons/learning',
                            title='[Bounty] Answer three linked questions',
                            body='Earn a lesson badge for explaining this example')
        frames = issue(405, repository='data/annotation',
                       title='Bounty: label 250 frames from scratch',
                       body='No cash amount is advertised')
        report = run(FakeGitHub([educational, frames]), now=NOW)
        self.assertEqual(report['prospect_count'], 0)
        self.assertEqual(report['funds_verified_usd'], 0)

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

    def test_incomplete_or_unattested_search_is_not_a_successful_zero(self):
        for completeness in (True, None, 'false'):
            class Incomplete:
                def get(self, path, params=None):
                    response = {'items': [], 'total_count': 100}
                    if completeness is not None:
                        response['incomplete_results'] = completeness
                    return response
            with self.subTest(completeness=completeness), self.assertRaises(ScoutError):
                run(Incomplete(), now=NOW)

    def test_metadata_budget_exhaustion_is_visible_without_more_requests(self):
        class Limited(FakeGitHub):
            def get(self, path, params=None):
                if path == '/search/issues':
                    self.calls.append((path, params))
                    rows = ([issue(i, repository=f'aaaa/r{i}')
                             for i in range(1, MAX_REPO_LOOKUPS + 1)]
                            if 'label:' in params['q'] else
                            [issue(999, repository='zzzz/source')])
                    return {'items': rows, 'incomplete_results': False,
                            'total_count': len(rows)}
                self.calls.append((path, params))
                return {'language': 'Python' if path == '/repos/zzzz/source' else 'TypeScript'}
        client = Limited([])
        report = run(client, now=NOW)
        self.assertEqual(report['prospect_count'], 0)
        self.assertEqual(report['observation_status'], 'incomplete_metadata_budget')
        self.assertTrue(report['metadata_budget_exhausted'])
        self.assertEqual(report['unexamined_candidate_count'], 1)
        self.assertEqual(sum(p.startswith('/repos/') for p, _ in client.calls), MAX_REPO_LOOKUPS)
        self.assertIn('Incomplete observation', summary(report))
        self.assertIn('1 unexamined', summary(report))
        self.assertEqual(report['commercial_review_ready'], 0)

    def test_complete_empty_sample_is_distinct_from_budget_exhaustion(self):
        report = run(FakeGitHub([]), now=NOW)
        self.assertEqual(report['observation_status'], 'bounded_sample_complete')
        self.assertFalse(report['metadata_budget_exhausted'])
        self.assertEqual(report['unexamined_candidate_count'], 0)
        self.assertNotIn('Incomplete observation', summary(report))

    def test_malformed_money_and_explicit_non_usd_are_not_usd_advertisements(self):
        for amount in ('$1,200,50', '$1.234', 'CA$200', 'CAD $200', '$200 AUD', 'HK$200'):
            with self.subTest(amount=amount):
                self.assertIsNone(_parse_issue(issue(title='Bounty ' + amount, body=''), NOW))
        for amount in ('$200', 'US$200', 'USD $200', '$200 USD', '$200.'):
            with self.subTest(amount=amount):
                self.assertEqual(_parse_issue(issue(title='Bounty ' + amount, body=''), NOW)['advertised_reward_usd'], 200)

    def test_reader_disables_environment_proxies_and_installs_redirect_denial(self):
        with patch('bountyforge.revenue_scout.urllib.request.build_opener') as build:
            GitHubReadOnly('test-only-token')
        handlers = build.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], _NoRedirect)
        with self.assertRaises(ScoutError):
            handlers[1].redirect_request(None, None, 302, 'redirect', {}, 'https://evil.invalid')

    def test_reader_caps_response_before_json_parsing(self):
        response = io.BytesIO(b' ' * (MAX_RESPONSE_BYTES + 1))
        client = GitHubReadOnly()
        client.opener = Mock()
        client.opener.open.return_value = response
        with self.assertRaisesRegex(ScoutError, 'bounded size'):
            client.get('/search/issues')
        request = client.opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertEqual(request.full_url, 'https://api.github.com/search/issues')

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
