"""Black Box process-boundary acceptance: executable CLIs, not internal mocks.

No credentials, network, real orders, external code, delivery or production writes.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = [sys.executable, '-m', 'scripts.phase7_owned_demo']
INTAKE = [sys.executable, '-m', 'bountyforge.paid_intake']


class BlackBoxCLIAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bf-blackbox-')
        self.addCleanup(self.temp.cleanup)
        self.scratch = Path(self.temp.name)
        self.environment = dict(os.environ)
        self.environment['TMPDIR'] = str(self.scratch)
        for field in ('STRIPE_SECRET_KEY', 'GROQ_API_KEY', 'OPENAI_API_KEY',
                      'GH_TOKEN', 'GITHUB_TOKEN', 'BOUNTYFORGE_PRIVATE_REVIEW_STORE_APPROVED'):
            self.environment.pop(field, None)
        self.environment['PYTHONDONTWRITEBYTECODE'] = '1'

    def process(self, args, *, payload=b'', environment=None):
        return subprocess.run(
            args, cwd=ROOT, env=environment or self.environment,
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=15, check=False)

    def test_synthetic_cli_happy_path_has_no_payment_or_execution_authority(self):
        result = self.process(DEMO)
        self.assertEqual(result.returncode, 0, result.stderr[:200])
        self.assertEqual(result.stderr, b'')
        output = json.loads(result.stdout)
        self.assertEqual(output['kind'], 'owned_only_fulfillment_demo')
        self.assertEqual(output['state'], 'AWAITING_OWNER_APPROVAL')
        self.assertTrue(output['owned_replay_passed'])
        for key in ('real_payment_verified', 'delivery_authorized',
                    'private_execution_authorized'):
            self.assertIs(output[key], False)
        self.assertEqual(output['model_calls'], 0)
        self.assertEqual(output['received_revenue_usd'], 0)
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_synthetic_cli_rejects_unapproved_external_arguments_without_side_effects(self):
        sentinel = 'SECRET_CUSTOMER_PATH_NEVER_PRINT'
        for argset in (
            ['--execute-customer'], ['--payment-verified'],
            ['--source', sentinel], [sentinel], ['--help'],
        ):
            with self.subTest(args=argset):
                response = self.process(DEMO + argset)
                self.assertEqual(response.returncode, 2)
                self.assertEqual(response.stdout, b'')
                self.assertIn(b'accepts no arguments', response.stderr)
                self.assertNotIn(sentinel.encode(), response.stderr)
                self.assertEqual(list(self.scratch.iterdir()), [])

    def test_deterministic_replay_without_persistent_external_state(self):
        first, second = self.process(DEMO), self.process(DEMO)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        a, b = json.loads(first.stdout), json.loads(second.stdout)
        self.assertEqual(a, b)
        self.assertEqual(a['revision'], 4)
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_payment_cli_rejects_unauthorized_private_store_and_never_calls_provider(self):
        env = dict(self.environment)
        env['GITHUB_ACTIONS'] = 'true'
        env['BOUNTYFORGE_PRIVATE_REVIEW_STORE_APPROVED'] = '1'
        env['STRIPE_SECRET_KEY'] = 'rk_live_FAKE_BLACKBOX_NO_PROVIDER'
        store = self.scratch / 'unapproved.sqlite'
        response = self.process(
            INTAKE + ['--store', str(store)],
            payload=b'cs_live_' + b'A' * 28 + b'\n', environment=env)
        self.assertEqual(response.returncode, 2)
        record = json.loads(response.stdout)
        self.assertEqual(record['kind'], 'private_paid_order_review')
        self.assertEqual(record['status'], 'rejected')
        self.assertIs(record['execution_authorized'], False)
        self.assertIs(record['customer_source_accepted'], False)
        self.assertIs(record['fulfillment_dispatched'], False)
        self.assertEqual(record['model_calls'], 0)
        self.assertFalse(store.exists())
        self.assertNotIn(b'FAKE_BLACKBOX', response.stdout + response.stderr)
        self.assertNotIn(str(store).encode(), response.stdout + response.stderr)

    def test_payment_cli_rejects_oversized_untrusted_input_before_external_api(self):
        env = dict(self.environment)
        env.pop('GITHUB_ACTIONS', None)
        env['BOUNTYFORGE_PRIVATE_REVIEW_STORE_APPROVED'] = '1'
        store = self.scratch / 'not_created.sqlite'
        response = self.process(
            INTAKE + ['--store', str(store)],
            payload=b'cs_live_' + b'A' * 400,
            environment=env)
        self.assertEqual(response.returncode, 2)
        record = json.loads(response.stdout)
        self.assertEqual(record['status'], 'rejected')
        self.assertEqual(record['reason'], 'invalid_review_reference')
        self.assertIs(record['execution_authorized'], False)
        self.assertFalse(store.exists())
        self.assertNotIn(b'AAAAAAA', response.stderr)


if __name__ == '__main__':
    unittest.main()
