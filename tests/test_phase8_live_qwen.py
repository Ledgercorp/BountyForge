"""The live adapter stays opt-in; tests use stubs and never infer or run subjects."""
import json
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bountyforge import phase8_live_qwen as live
from scripts import phase8_live_qwen as cli


class LiveQwenAdmissionTests(unittest.TestCase):
    def test_workflow_is_manual_gated_public_standard_and_secret_free(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    '.github/workflows/phase8-frozen-qwen-evaluation.yml').read_text()
        self.assertIn('workflow_dispatch:', workflow)
        self.assertIn("paths: ['.github/workflows/phase8-frozen-qwen-evaluation.yml']", workflow)
        self.assertIn('[qwen-frozen-eval]', workflow)
        self.assertIn('confirm_zero_cost:', workflow)
        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertIn('timeout-minutes: 70', workflow)
        self.assertIn('retention-days: 1', workflow)
        self.assertIn('actions/cache/restore@', workflow)
        self.assertIn('docker pull --platform linux/amd64 python@sha256:8a00ec', workflow)
        self.assertNotIn('schedule:', workflow)
        self.assertNotIn('secrets.', workflow)
        self.assertNotIn('actions/cache/save', workflow)
        self.assertIn('--continue-pinned-partial', workflow)

    def test_cli_requires_explicit_pinned_continuation(self):
        with patch.object(cli, 'evaluate') as evaluate, patch('sys.stdout', new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as raised:
                cli.main(['--output', 'result.json'])
            self.assertEqual(raised.exception.code, 2)
            evaluate.assert_not_called()
        with patch.object(cli, 'evaluate', return_value={'status': 'completed', 'attempted_cases': 20}), \
                patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(cli.main(['--continue-pinned-partial', '--output', 'result.json']), 0)

    def test_host_admission_requires_exact_repo_ref_event_and_runner(self):
        allowed = {
            'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'Ledgercorp/BountyForge',
            'GITHUB_EVENT_NAME': 'workflow_dispatch',
            'BOUNTYFORGE_QWEN_COST_ACK': 'true',
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
        tagged_push = dict(allowed, GITHUB_EVENT_NAME='push', BOUNTYFORGE_QWEN_PUSH_ACK='true')
        with patch.dict(os.environ, tagged_push, clear=True):
            live.require_hosted_admission()
        tagged_push['BOUNTYFORGE_QWEN_PUSH_ACK'] = 'false'
        with patch.dict(os.environ, tagged_push, clear=True):
            with self.assertRaises(live.EvaluationRejected):
                live.require_hosted_admission()

    def test_credentials_block_before_preflight_or_model_creation(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {'GROQ_API_KEY': ''}, clear=True), \
                patch.object(live, 'require_hosted_admission'), \
                patch.object(live, 'preflight') as preflight, \
                patch.object(live, 'LocalModel') as model:
            report = live.evaluate(output=Path(directory)/'report.json')
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
            report = live.evaluate(output=Path(directory)/'report.json')
            model.assert_not_called()
            self.assertEqual(report['status'], 'blocked')
            self.assertEqual(report['inference_calls'], 35)
            self.assertIsNone(report['accuracy'])

    def test_resume_source_digest_is_fixed_before_any_new_inference(self):
        catalog = live.Catalog(live.SELECTION, live.SELECTION_SHA256)
        tasks = catalog.tasks()
        resumed = live.load_resume_report(catalog, tasks)
        self.assertEqual([row['case_id'] for row in resumed['cases']], list(live.EXPOSED_CASES))
        self.assertEqual(resumed['inference_calls'], 35)
        self.assertEqual(resumed['cases'][0]['failure_category'], 'source_or_patch_validation_rejection')
        self.assertEqual(resumed['cases'][3]['failure_category'], 'ineffective_model_proposal')
        self.assertEqual(resumed['cases'][5]['failure_category'], 'inference_or_test_runner_failure')
        with patch.object(live, 'RESUME_REPORT_SHA256', '0'*64):
            with self.assertRaises(live.EvaluationRejected):
                live.load_resume_report(catalog, tasks)

    def test_evaluation_uses_pinned_twenty_and_replays_only_ready_patch(self):
        class Backend:
            pass

        def session_for(task):
            return {
                'schema': 1, 'protocol': 'owned_statement_session_v8',
                'status': 'review_ready' if task['id'] == 'network_word_order' else 'failed',
                'patch': [{'path': 'subject.py', 'diff': 'owned diff'}] if task['id'] == 'network_word_order' else None,
                'model_calls': 1, 'calls': [{'seconds': 0.25, 'metadata': {'prompt_tokens': 10, 'completion_tokens': 4}}],
                'worker': {'status': 'review_ready' if task['id'] == 'network_word_order' else 'failed',
                           'attempts': ([{'status': 'passed'}] if task['id'] == 'network_word_order'
                                        else [{'error': 'test_failure_or_timeout'}])},
                'source_sha256': task['sha256']['subject.py'],
                'tests_sha256': task['sha256']['tests/test_regression.py'],
            }

        remaining_specs = live.Catalog(live.SELECTION, live.SELECTION_SHA256).tasks()[len(live.EXPOSED_CASES):]
        remaining = iter(remaining_specs)
        processed = []
        def fake_repair(issue, root, path, model, **kwargs):
            spec = next(remaining)
            processed.append(spec['id'])
            return session_for(spec)

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
        self.assertEqual(processed, [spec['id'] for spec in remaining_specs])
        self.assertEqual(report['attempted_cases'], 20)
        self.assertEqual(report['inference_calls'], 36)
        self.assertEqual(report['independently_replayed_successes'], 1)
        self.assertEqual(report['accuracy'], {'verified_repairs': 1, 'attempted': 20})
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['prompt_tokens'], 34225)
        self.assertEqual(report['failure_category_counts']['independently_replayed_success'], 1)
        self.assertEqual(report['proposal_and_verification_counts']['targeted_test_failures'], 0)
        self.assertEqual(report['proposal_and_verification_counts']['source_validation_rejections'], 25)
        self.assertEqual(report['proposal_and_verification_counts']['ineffective_proposals_rejected'], 4)
        self.assertEqual(report['failure_category_counts']['source_or_patch_validation_rejection'], 13)
        self.assertEqual(report['failure_category_counts']['ineffective_model_proposal'], 2)
        self.assertEqual(report['failure_category_counts']['inference_or_test_runner_failure'], 3)
        self.assertEqual(report['failure_category_counts']['other_patch_validation_rejection'], 1)
        self.assertFalse(saved['customer_execution_authorized'])
        self.assertFalse(saved['delivery_authorized'])
        self.assertEqual(len(saved['cases']), 20)


if __name__ == '__main__':
    unittest.main()
