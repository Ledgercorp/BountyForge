import copy
import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.autonomy import (make_evidence, verify_envelope, save_evidence,
                                  summarize_canary, validate_evidence)

ISSUE = {'url': 'https://github.com/example/repo/issues/42',
         'verification': 'unverified_candidate', 'title': 'Claim $999'}
TIME = '2026-10-20T20:00:00+00:00'

class AutonomyTests(unittest.TestCase):
    def record(self, candidates=None, **kwargs):
        return make_evidence([ISSUE] if candidates is None else candidates,
                             scan_source='fictional_demo', generated_at=TIME, **kwargs)

    def test_candidates_are_unverified_and_not_executed(self):
        r = verify_envelope(self.record())
        self.assertEqual(r['scan_count'], 1)
        self.assertFalse(r['candidates'][0]['qualified_for_external_execution'])
        self.assertEqual(r['real_repairs_attempted'], 0)
        self.assertEqual(r['external_submissions'], 0)

    def test_deduplicate_and_reject_invalid_issue_urls(self):
        r = verify_envelope(self.record([ISSUE, ISSUE, {'url': 'https://evil.example/issues/42'}]))
        self.assertEqual(r['scan_count'], 1)

    def test_tampering_fails_integrity(self):
        a = self.record()
        a['record']['revenue_usd_confirmed'] = 999
        with self.assertRaises(ValueError):
            verify_envelope(a)
        b = self.record()
        b['record']['scan_count'] += 1
        with self.assertRaises(ValueError):
            verify_envelope(b)
        c = self.record()
        c['record']['canary']['status'] = 'synthetic_review_ready'
        with self.assertRaises(ValueError):
            verify_envelope(c)

    def test_digest_rejects_modified_valid_record(self):
        a = self.record()
        a['record']['generated_at'] = '2026-10-21T00:00:00+00:00'
        with self.assertRaises(ValueError):
            verify_envelope(a)

    def test_synthetic_canary_strips_logs_and_diff(self):
        canary = summarize_canary({'status': 'review_ready', 'source_sha256': 'a'*64,
            'controlled_synthetic_fixture': True, 'code_executed_in_trusted_fixture_only': True,
            'submitted': False, 'verified_payout': False, 'paid_model_calls': 0,
            'model_calls': 1, 'baseline': {'passed': False, 'output': 'SECRET'},
            'attempts': [{'number': 1, 'status': 'passed',
                          'diff': 'PRIVATE CODE', 'test': {'passed': True, 'output': 'SECRET'}}],
            'patch': [{'path': 'calc.py', 'diff': 'PRIVATE CODE'}]})
        self.assertEqual(canary['status'], 'synthetic_review_ready')
        self.assertNotIn('SECRET', json.dumps(canary))
        self.assertNotIn('PRIVATE CODE', json.dumps(canary))
        self.assertEqual(verify_envelope(self.record(canary=canary))['canary']['status'],
                         'synthetic_review_ready')

    def test_worker_provenance_required(self):
        valid = {'status': 'failed', 'controlled_synthetic_fixture': True,
                 'code_executed_in_trusted_fixture_only': True,
                 'submitted': False, 'verified_payout': False,
                 'paid_model_calls': 0, 'model_calls': 0, 'attempts': []}
        self.assertEqual(summarize_canary(valid)['status'], 'synthetic_failed')
        for name, value in (('submitted', True), ('verified_payout', True),
                            ('controlled_synthetic_fixture', False),
                            ('code_executed_in_trusted_fixture_only', False),
                            ('paid_model_calls', 1)):
            forged = dict(valid, **{name: value})
            with self.subTest(name=name), self.assertRaises(ValueError):
                summarize_canary(forged)
        with self.assertRaises(ValueError):
            summarize_canary({'status': 'failed', 'attempts': []})

    def test_forged_inference_count_rejected(self):
        valid = {'status': 'failed', 'controlled_synthetic_fixture': True,
                 'code_executed_in_trusted_fixture_only': True,
                 'submitted': False, 'verified_payout': False,
                 'paid_model_calls': 0, 'model_calls': 0, 'attempts': []}
        with self.assertRaises(ValueError):
            summarize_canary(dict(valid, model_calls=2))

    def test_refuses_bad_source(self):
        with self.assertRaises(ValueError):
            make_evidence([], scan_source='unknown')

    def test_exclusive_save_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'evidence.json'
            save_evidence(path, self.record())
            with self.assertRaises(FileExistsError):
                save_evidence(path, self.record())
            self.assertEqual(verify_envelope(json.loads(path.read_text()))['scan_count'], 1)

    def test_symlink_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)/'data.txt'; target.write_text('safe')
            link = Path(d)/'out.json'; link.symlink_to(target)
            with self.assertRaises(ValueError):
                save_evidence(link, self.record())
            self.assertEqual(target.read_text(), 'safe')

    def test_bogus_synthetic_claim_rejected(self):
        good = self.record(canary={'status': 'synthetic_failed', 'synthetic_only': True,
                                  'submitted': False, 'third_party_code_executed': False,
                                  'model_calls': 0})
        validate_evidence(good['record'])
        bad = copy.deepcopy(good['record']); bad['canary']['submitted'] = True
        with self.assertRaises(ValueError):
            validate_evidence(bad)

if __name__ == '__main__': unittest.main()
