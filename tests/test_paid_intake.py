"""Trusted coordinator integration; mocked HTTPS, real private CAS files."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bountyforge import paid_intake
from bountyforge.paid_review_store import SQLitePaidReviewStore
from bountyforge.paid_review_ledger import ReviewLedgerRejected
from test_stripe_order_gate import CFG, SESSION_ID, Response, record


class PaidIntakeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'review.sqlite3'
        self.env = dict(CFG, BOUNTYFORGE_PRIVATE_REVIEW_STORE_APPROVED='1')

    def run_command(self, raw=None, env=None):
        output = io.StringIO()
        with patch.dict(os.environ, env or self.env, clear=True):
            code = paid_intake.main(['--store', str(self.path)],
                                   stdin=io.BytesIO(raw if raw is not None else (SESSION_ID+'\n').encode()),
                                   stdout=output)
        text = output.getvalue()
        self.assertNotIn(SESSION_ID, text)
        self.assertNotIn(CFG['STRIPE_SECRET_KEY'], text)
        result = json.loads(text)
        self.assertFalse(result['execution_authorized'])
        self.assertFalse(result['external_submission_authorized'])
        return code, result

    def test_verified_review_survives_restart_and_replay_rechecks_all_payment_objects(self):
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = [Response(json.dumps(x).encode()) for x in record()*2]
            code, first = self.run_command()
            self.assertEqual(code, 0)
            self.assertEqual(first['status'], 'awaiting_owner_scope_review')
            code, second = self.run_command()
            self.assertEqual(second['status'], 'already_recorded')
            self.assertEqual(build.return_value.open.call_count, 6)
            self.assertTrue(all(c.args[0].get_method() == 'GET' for c in build.return_value.open.call_args_list))
        state, revision = SQLitePaidReviewStore(self.path).read()
        self.assertEqual(len(state['orders']), 1)
        self.assertEqual(revision, '1')

    def test_refund_after_review_blocks_replay_without_altering_the_record(self):
        refunded = list(record()); refunded[2]['refunded'] = True
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = [Response(json.dumps(x).encode()) for x in (*record(), *refunded)]
            self.assertEqual(self.run_command()[0], 0)
            before = SQLitePaidReviewStore(self.path).read()
            code, result = self.run_command()
        self.assertEqual(code, 2)
        self.assertEqual(result['reason'], 'payment_not_verified')
        self.assertEqual(SQLitePaidReviewStore(self.path).read(), before)

    def test_unpaid_order_has_no_review_record(self):
        session = record(session_overrides={'payment_status': 'unpaid'})[0]
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value = Response(json.dumps(session).encode())
            self.assertEqual(self.run_command()[0], 2)
        self.assertEqual(SQLitePaidReviewStore(self.path).read(), (None, None))

    def test_invalid_or_source_input_is_rejected_before_storage_or_network(self):
        for raw in (b'', b'x'*257, b'def customer_code(): pass', b'\xff',
                    (SESSION_ID+'\n'+SESSION_ID).encode()):
            with self.subTest(raw=raw[:15]), patch('urllib.request.build_opener') as build:
                self.assertEqual(self.run_command(raw=raw)[0], 2)
                build.assert_not_called()
                self.assertFalse(self.path.exists())

    def test_unapproved_volume_and_mixed_credentials_fail_before_network_or_state(self):
        cases = [dict(self.env, BOUNTYFORGE_PRIVATE_REVIEW_STORE_APPROVED='0'),
                 dict(self.env, GITHUB_ACTIONS='true')]
        cases.extend(dict(self.env, **{name: 'unit-secret'})
                     for name in ('GITHUB_TOKEN', 'GH_TOKEN', 'GROQ_API_KEY', 'OPENAI_API_KEY'))
        for env in cases:
            with self.subTest(keys=sorted(env)), patch('urllib.request.build_opener') as build:
                self.assertEqual(self.run_command(env=env)[0], 2)
                build.assert_not_called()
                self.assertFalse(self.path.exists())

    def test_privacy_loss_or_backend_failure_is_sanitized_without_blind_retry(self):
        self.path.parent.chmod(0o755)
        try:
            with patch('urllib.request.build_opener') as build:
                self.assertEqual(self.run_command()[0], 2)
                build.assert_not_called()
        finally:
            self.path.parent.chmod(0o700)
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = RuntimeError(CFG['STRIPE_SECRET_KEY'] + SESSION_ID)
            code, result = self.run_command()
            self.assertEqual(code, 2)
            self.assertEqual(result['reason'], 'payment_not_verified')
            self.assertEqual(build.return_value.open.call_count, 1)

    def test_failed_durable_write_never_emits_ready_or_retries_blindly(self):
        with patch('urllib.request.build_opener') as build, \
                patch.object(SQLitePaidReviewStore, 'write',
                             side_effect=ReviewLedgerRejected(CFG['STRIPE_SECRET_KEY'])) as write:
            build.return_value.open.side_effect = [Response(json.dumps(x).encode()) for x in record()]
            code, result = self.run_command()
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(write.call_count, 1)
        self.assertEqual(SQLitePaidReviewStore(self.path).read(), (None, None))


if __name__ == '__main__':
    unittest.main()
