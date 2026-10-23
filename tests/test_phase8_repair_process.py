"""TEST-DRIVER process acceptance, not an exposed commercial product CLI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = [sys.executable, '-m', 'tests.support.phase8_repair_driver']
ENV = {'PATH': os.defpath, 'PYTHONPATH': str(ROOT),
       'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C.UTF-8'}


class Phase8RepairProcessTests(unittest.TestCase):
    def run_scenario(self, scenario):
        completed = subprocess.run(COMMAND + [scenario], env=ENV, cwd=ROOT,
                                   input=b'', capture_output=True, timeout=10)
        self.assertNotIn(b'Traceback', completed.stderr)
        self.assertTrue(completed.stdout, 'Test-only repair driver is missing or produced no receipt')
        report = json.loads(completed.stdout)
        self.assertIs(report['test_driver_only'], True)
        self.assertIs(report['provider_simulator'], True)
        self.assertEqual(report['live_model_calls'], 0)
        self.assertEqual(report['received_revenue_usd'], 0)
        self.assertIs(report['customer_execution_authorized'], False)
        self.assertIs(report['delivery_authorized'], False)
        self.assertIs(report['production_ready'], False)
        for field in ('customer_source_accepted', 'customer_environment_tested',
                      'customer_rights_verified', 'owner_consent_verified',
                      'real_payment_verified', 'launch_enabled'):
            self.assertIs(report[field], False)
        self.assertIs(report['original_fixture_unchanged'], True)
        self.assertEqual(report['simulated_backend_processes'], report['simulated_model_calls'])
        self.assertEqual(report['backend_requests'], report['session']['model_calls'])
        self.assertEqual(len(report['backend_receipts']), report['backend_requests'])
        for actual, call in zip(report['backend_receipts'], report['session']['calls']):
            self.assertEqual(actual['prompt_sha256'], hashlib.sha256(call['prompt'].encode()).hexdigest())
            self.assertEqual(actual['exit_code'], 2 if scenario == 'providerfailure' else 0)
        self.assertNotIn(b'OWNED_PROVIDER_FAILURE_DETAIL', completed.stdout + completed.stderr)
        return completed, report

    def test_healthy_fixed_response_has_actual_fresh_independent_verification(self):
        completed, report = self.run_scenario('healthy')
        self.assertEqual(completed.returncode, 0)
        session = report['session']
        self.assertEqual(session['status'], 'review_ready')
        self.assertEqual(report['simulated_model_calls'], 1)
        self.assertEqual([r['passed'] for r in report['actual_test_runs']], [False, True, True])
        self.assertEqual([r['role'] for r in report['actual_test_runs']], ['baseline', 'candidate', 'independent'])
        self.assertTrue(session['worker']['independent_verification']['passed'])
        self.assertIn('total = value * 3', session['patch'][0]['diff'])
        self.assertEqual(session['candidate_sha256'], report['expected_candidate_sha256'])

    def test_invalid_proposals_exhaust_bounded_attempts_without_candidate_execution(self):
        completed, report = self.run_scenario('invalidproposal')
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(report['session']['status'], 'failed')
        self.assertIsNone(report['session']['patch'])
        self.assertEqual(report['simulated_model_calls'], 2)
        self.assertEqual(len(report['actual_test_runs']), 1)
        self.assertFalse(report['actual_test_runs'][0]['passed'])
        calls = report['session']['calls']
        self.assertEqual(calls[1]['previous_response_sha256'],
                         hashlib.sha256(calls[0]['response'].encode()).hexdigest())
        prompt = json.loads(calls[1]['prompt'])
        self.assertFalse(prompt['previous_proposal_metrics']['parseable_change_metrics'])
        self.assertIn('test_scaled', prompt['failure_untrusted'])

    def test_wrong_candidate_runs_real_failing_tests_and_never_becomes_ready(self):
        completed, report = self.run_scenario('wrongcandidate')
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(report['session']['status'], 'failed')
        self.assertIsNone(report['session']['patch'])
        self.assertEqual(report['simulated_model_calls'], 2)
        self.assertEqual([r['passed'] for r in report['actual_test_runs']], [False, False])
        self.assertIn('16 != 12', report['actual_test_runs'][1]['output'])
        self.assertIn('16 != 12', json.loads(report['session']['calls'][1]['prompt'])['failure_untrusted'])
        self.assertEqual(report['session']['worker']['attempts'][1]['error'], 'repeated_ineffective_candidate')

    def test_provider_failure_is_sanitized_and_stops_after_one_process(self):
        completed, report = self.run_scenario('providerfailure')
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(report['session']['status'], 'blocked')
        self.assertIsNone(report['session']['patch'])
        self.assertEqual(report['simulated_model_calls'], 1)
        self.assertEqual(len(report['actual_test_runs']), 1)
        self.assertEqual(report['session']['reason'], 'inference_or_regression_unavailable')
        self.assertIsNone(report['session']['calls'][0]['response'])

    def test_driver_rejects_non_enum_flags_paths_and_all_stdin(self):
        for args, data in (([], b''), (['customer.py'], b''),
                           (['healthy', '--source', '/private/owned-sentinel'], b''),
                           (['healthy'], b'owned-unapproved-stdin'),
                           (['healthy'], b'x' * 257)):
            with self.subTest(args=args, bytes=len(data)):
                completed = subprocess.run(COMMAND + args, input=data, env=ENV, cwd=ROOT,
                                           capture_output=True, timeout=5)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, b'')
                self.assertEqual(completed.stderr, b'Owned TEST-DRIVER input rejected\n')


if __name__ == '__main__':
    unittest.main()
