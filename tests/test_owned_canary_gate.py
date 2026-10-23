"""Offline negative acceptance for the owned hosted-model workflow evidence."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.phase5 import development_runner as dev
from bountyforge.curated_docker import IMAGE
from bountyforge.curated_tasks import editable_scope
from bountyforge.groq_adapter import MODEL_ID
from scripts.validate_owned_canary import CanaryRejected, validate_owned_canary

REVISION = 'a' * 40


def completed_report():
    proof = {key: True for key in (
        'network_denied', 'loopback_inference_unreachable', 'source_writes_denied',
        'root_writes_denied', 'secrets_absent', 'uid_unprivileged', 'capabilities_empty',
        'no_new_privileges', 'seccomp_active', 'memory_limit_enforced', 'swap_disabled',
        'cpu_quota_verified', 'pid_limit_verified', 'tmpfs_bounded_noexec',
        'wall_clock_enforced', 'cleanup_verified', 'output_bounded',
        'docker_socket_absent', 'pid_pressure_enforced', 'cpu_pressure_enforced')}
    proof.update(image_digest=IMAGE.split('@')[1], untrusted_execution_certified=False)
    report = {'revision': REVISION, 'benchmark': 'owned_phase5_development',
              'suite': 'structural', 'protocol': 'ast_contract_v5', 'image': IMAGE,
              'commercial_bounty': False, 'historical_evaluation': False,
              'paid_inference': False, 'external_submission': False,
              'sandbox_preflight': proof, 'max_model_calls': 8, 'max_attempts_per_task': 2,
              'model_calls': 4, 'attempted': 4, 'passed': 0, 'inference_seconds': 4,
              'inference_backend': {'provider': 'groq', 'model': MODEL_ID, 'transport_calls': 4,
                                    'total_generation_tokens_per_call':1024,'minimum_interval_seconds':60},
              'tasks': []}
    for number, spec in enumerate(dev.SUITES['structural'][1]['tasks'], 1):
        response = json.dumps({'changes': [{'line': 3, 'new': 'return 2'}]})
        source = (dev.SUITES['structural'][0] / spec['id'] / spec['file']).read_text()
        prompt = json.dumps({'approved_file': spec['file'], 'target_symbol': spec['symbol'],
                             'editable_lines': editable_scope(source, spec['symbol'])})
        report['tasks'].append({
            'id': spec['id'], 'symbol': spec['symbol'],
            'source_sha256': spec['sha256'][spec['file']],
            'tests_sha256': spec['sha256']['tests/test_regression.py'],
            'baseline_reproduced': True,
            'baseline': {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                         'output': 'Ran 3 tests\nFAILED (failures=1)'},
            'status': 'failed', 'model_generated_success': False,
            'attempts': [{'number': 1, 'status': 'failed', 'failure_reason': 'proposal_rejected'}],
            'calls': [{'number': number, 'kind': 'patch', 'round': 1, 'max_tokens': 150,
                       'system': 'Bounded owned task only.', 'prompt': prompt,
                       'response': response, 'response_sha256': hashlib.sha256(response.encode()).hexdigest(),
                       'seconds': 1, 'metadata': {'provider': 'groq', 'model': MODEL_ID,
                                                'finish_reason': 'stop', 'prompt_tokens': 200,
                                                'completion_tokens': 20, 'requested_max_completion_tokens':1024,
                                                'provider_model_reported':MODEL_ID}}]})
    return report


class OwnedCanaryGateTests(unittest.TestCase):
    def validate(self, report):
        return validate_owned_canary(report, suite='structural', expected_revision=REVISION)

    def test_completed_zero_repair_experiment_is_truthful_valid_evidence(self):
        result = self.validate(completed_report())
        self.assertEqual(result['completed_tasks'], 4)
        self.assertEqual(result['repairs_passed'], 0)
        self.assertFalse(result['billing_independently_verified'])

    def test_total_reasoning_tokens_are_bounded_separately_from_final_patch(self):
        report=completed_report()
        for task in report['tasks']:
            for call in task['calls']:
                call['metadata']['requested_max_completion_tokens']=1024
                call['metadata']['completion_tokens']=720
        self.assertEqual(self.validate(report)['completed_tasks'],4)
        report['tasks'][0]['calls'][0]['metadata']['completion_tokens']=1025
        with self.assertRaises(CanaryRejected):self.validate(report)

    def test_actual_runner_transport_failure_cannot_make_green_canary(self):
        class Unavailable:
            def complete_line(self, *args, **kwargs):
                raise RuntimeError('mock transport unavailable')
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(dev, 'verify_runtime_boundary', return_value={'mock': True}), \
                    patch.object(dev, 'run_development_tests', return_value={
                        'passed': False, 'returncode': 1, 'output': 'FAILED (failures=1)'}):
                report = dev.run(model=Unavailable(), suite='structural', protocol='ast_contract_v5',
                                 output=Path(directory) / 'report.json')
        # This satisfied the old workflow's assertions, despite three blocked tasks.
        self.assertFalse(report.get('blocked'))
        self.assertEqual(report['model_calls'], 1)
        self.assertEqual(sum(task['status'] == 'blocked' for task in report['tasks']), 3)
        with self.assertRaises(CanaryRejected):
            self.validate(report)

    def test_any_blocked_task_or_incomplete_task_set_rejects(self):
        report = completed_report()
        report['tasks'][-1]['status'] = 'blocked'
        with self.assertRaisesRegex(CanaryRejected, 'blocked'):
            self.validate(report)
        report = completed_report()
        report['tasks'].pop()
        with self.assertRaisesRegex(CanaryRejected, 'exactly four'):
            self.validate(report)

    def test_missing_baseline_and_false_reproduction_reject(self):
        for change in ('missing', 'not_reproduced', 'import_error', 'timeout'):
            with self.subTest(change=change):
                report = completed_report()
                task = report['tasks'][0]
                if change == 'missing': task.pop('baseline')
                elif change == 'not_reproduced': task['baseline_reproduced'] = False
                elif change == 'import_error': task['baseline']['output'] = 'ImportError: tests unavailable'
                else: task['baseline']['timeout'] = True
                with self.assertRaisesRegex(CanaryRejected, 'baseline'):
                    self.validate(report)

    def test_changed_source_tests_suite_or_revision_reject(self):
        for field, value in [('source_sha256', 'b' * 64), ('tests_sha256', 'b' * 64),
                             ('id', 'not-owned'), ('symbol', 'unapproved')]:
            with self.subTest(field=field):
                report = completed_report()
                report['tasks'][0][field] = value
                with self.assertRaises(CanaryRejected): self.validate(report)
        for field, value in [('suite', 'original'), ('revision', 'b' * 40),
                             ('protocol', 'ast_contract_v6'), ('image', 'python:latest')]:
            with self.subTest(field=field):
                report = completed_report()
                report[field] = value
                with self.assertRaises(CanaryRejected): self.validate(report)

    def test_partial_sandbox_proof_and_global_admission_failure_reject(self):
        for field in ('network_denied', 'cleanup_verified', 'cpu_pressure_enforced', 'secrets_absent'):
            with self.subTest(field=field):
                report = completed_report()
                report['sandbox_preflight'][field] = False
                with self.assertRaisesRegex(CanaryRejected, 'controls'): self.validate(report)
        report = completed_report()
        report['blocked'] = 'sandbox_admission_failed'
        with self.assertRaisesRegex(CanaryRejected, 'blocked'): self.validate(report)

    def test_call_metadata_provider_identity_and_accounting_required(self):
        for field, value in [('provider', 'other'), ('model', 'other'), ('finish_reason', 'length'),
                             ('completion_tokens', None), ('prompt_tokens', None), ('completion_tokens', 1025)]:
            with self.subTest(field=field, value=value):
                report = completed_report()
                report['tasks'][0]['calls'][0]['metadata'][field] = value
                with self.assertRaisesRegex(CanaryRejected, 'accounting'): self.validate(report)
        report = completed_report()
        report['inference_backend']['transport_calls'] = 3
        with self.assertRaisesRegex(CanaryRejected, 'accounting'): self.validate(report)

    def test_call_sequences_transcripts_and_timing_must_reconcile(self):
        changes = [('number', 2), ('response', 'tampered'), ('seconds', float('nan')),
                   ('error', 'RuntimeError'), ('kind', 'diagnosis'), ('prompt', '{}')]
        for field, value in changes:
            with self.subTest(field=field):
                report = completed_report()
                report['tasks'][0]['calls'][0][field] = value
                with self.assertRaises(CanaryRejected): self.validate(report)
        report = completed_report()
        report['inference_seconds'] = 100
        with self.assertRaisesRegex(CanaryRejected, 'timing'): self.validate(report)

    def test_success_without_independently_passing_tests_rejects(self):
        report = completed_report()
        task = report['tasks'][0]
        task.update(status='owned_development_passed', model_generated_success=True)
        task['attempts'][0]['status'] = 'passed'
        report['passed'] = 1
        with self.assertRaisesRegex(CanaryRejected, 'isolated tests'): self.validate(report)
        task['attempts'][0]['test'] = {'passed': True, 'returncode': 0, 'timeout': False,
                                      'error': None, 'output': 'Ran 3 tests\nOK\n'}
        self.assertEqual(self.validate(report)['repairs_passed'], 1)

    def test_totals_or_expanded_budgets_reject(self):
        for field, value in [('model_calls', 5), ('attempted', 3), ('passed', 1),
                             ('max_model_calls', 16), ('max_attempts_per_task', 3)]:
            with self.subTest(field=field):
                report = completed_report()
                report[field] = value
                with self.assertRaises(CanaryRejected): self.validate(report)


if __name__ == '__main__':
    unittest.main()
