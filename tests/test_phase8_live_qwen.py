"""The live adapter stays opt-in; tests use stubs and never infer or run subjects."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bountyforge import phase8_live_qwen as live


class LiveQwenAdmissionTests(unittest.TestCase):
    def test_workflow_is_manual_gated_public_standard_and_secret_free(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    '.github/workflows/phase8-frozen-qwen-evaluation.yml').read_text()
        self.assertIn('workflow_dispatch:', workflow)
        self.assertIn('confirm_zero_cost:', workflow)
        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertIn('timeout-minutes: 70', workflow)
        self.assertIn('retention-days: 1', workflow)
        self.assertIn('actions/cache/restore@', workflow)
        self.assertIn('docker pull --platform linux/amd64 python@sha256:8a00ec', workflow)
        self.assertNotIn('schedule:', workflow)
        self.assertNotIn('secrets.', workflow)
        self.assertNotIn('actions/cache/save', workflow)

    def test_host_admission_requires_exact_repo_ref_event_and_runner(self):
        allowed = {
            'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'Ledgercorp/BountyForge',
            'GITHUB_EVENT_NAME': 'workflow_dispatch',
            'GITHUB_REF': 'refs/heads/engineering/revenue-linux-scout-20261021',
            'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64',
        }
        with patch.dict(os.environ, allowed, clear=True):
            live.require_hosted_admission()
        for name, wrong in [('GITHUB_EVENT_NAME', 'push'), ('GITHUB_REPOSITORY', 'elsewhere/repo'),
                            ('RUNNER_ARCH', 'ARM64'), ('GITHUB_REF', 'refs/heads/main')]:
            changed = dict(allowed, **{name: wrong})
            with self.subTest(name=name), patch.dict(os.environ, changed, clear=True):
                with self.assertRaises(live.EvaluationRejected):
                    live.require_hosted_admission()

    def test_credentials_block_before_preflight_or_model_creation(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {'GROQ_API_KEY': ''}, clear=True), \
                patch.object(live, 'require_hosted_admission'), \
                patch.object(live, 'preflight') as preflight, \
                patch.object(live, 'LocalModel') as model:
            report = live.evaluate(output=Path(directory)/'report.json', enforce_hosted=False)
            preflight.assert_not_called(); model.assert_not_called()
            self.assertEqual(report['status'], 'blocked')
            self.assertIsNone(report['accuracy'])
            self.assertEqual(report['inference_calls'], 0)
            self.assertNotIn('GROQ_API_KEY', (Path(directory)/'report.json').read_text())

    def test_preflight_rejection_produces_no_model_calls(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {}, clear=True), \
                patch.object(live, 'require_hosted_admission'), \
                patch.object(live, 'preflight', side_effect=live.EvaluationRejected('control missing')), \
                patch.object(live, 'LocalModel') as model:
            report = live.evaluate(output=Path(directory)/'report.json', enforce_hosted=False)
            model.assert_not_called()
            self.assertEqual(report['status'], 'blocked')
            self.assertEqual(report['inference_calls'], 0)
            self.assertIsNone(report['accuracy'])

    def test_evaluation_uses_pinned_twenty_and_replays_only_ready_patch(self):
        class Backend:
            pass

        def session_for(task):
            return {
                'schema': 1, 'protocol': 'owned_statement_session_v8',
                'status': 'review_ready' if task['id'] == 'stock_admission' else 'failed',
                'patch': [{'path': 'subject.py', 'diff': 'owned diff'}] if task['id'] == 'stock_admission' else None,
                'model_calls': 1, 'calls': [{'seconds': 0.25, 'metadata': {'prompt_tokens': 10, 'completion_tokens': 4}}],
                'worker': {'status': 'review_ready' if task['id'] == 'stock_admission' else 'failed',
                           'attempts': ([{'status': 'passed'}] if task['id'] == 'stock_admission'
                                        else [{'error': 'test_failure_or_timeout'}])},
                'source_sha256': task['sha256']['subject.py'],
                'tests_sha256': task['sha256']['tests/test_regression.py'],
            }

        remaining = iter(live.Catalog(live.SELECTION, live.SELECTION_SHA256).tasks())
        def fake_repair(issue, root, path, model, **kwargs):
            return session_for(next(remaining))

        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {}, clear=True), \
                patch.object(live, 'require_hosted_admission'), \
                patch.object(live, 'preflight', return_value={'all_controls': True}), \
                patch.object(live, 'LocalModel', return_value=Backend()), \
                patch.object(live, 'materialize'), \
                patch.object(live, 'repair_owned', side_effect=fake_repair), \
                patch.object(live, 'replay', return_value={'status': 'replay_passed'}) as replay:
            output = Path(directory)/'report.json'
            report = live.evaluate(output=output)
            saved = json.loads(output.read_text())
        replay.assert_called_once()
        self.assertEqual(report['attempted_cases'], 20)
        self.assertEqual(report['inference_calls'], 20)
        self.assertEqual(report['independently_replayed_successes'], 1)
        self.assertEqual(report['accuracy'], {'verified_repairs': 1, 'attempted': 20})
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['prompt_tokens'], 200)
        self.assertEqual(report['failure_category_counts']['independently_replayed_success'], 1)
        self.assertEqual(report['proposal_and_verification_counts']['targeted_test_failures'], 19)
        self.assertFalse(saved['customer_execution_authorized'])
        self.assertFalse(saved['delivery_authorized'])
        self.assertEqual(len(saved['cases']), 20)


if __name__ == '__main__':
    unittest.main()
