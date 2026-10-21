"""Offline coordinator checks: neutral comments are not real repair results."""
import json
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from benchmarks.phase4 import benchmark_runner as runner
from bountyforge.groq_adapter import MODEL_ID
from scripts.verify_phase5_repairs import verify


class HostedHistoricalTests(unittest.TestCase):
    def hosted_zero_report(self):
        class Invalid:
            def complete_line(self, *args, **kwargs):
                self.last_call = {'provider': 'groq', 'model': MODEL_ID,
                                  'provider_model_reported': MODEL_ID, 'finish_reason': 'stop',
                                  'requested_max_completion_tokens': 1024,
                                  'prompt_tokens': 500, 'completion_tokens': 100, 'total_tokens': 600}
                return '{"changes":[]}'
        proof = json.loads(Path('evidence/revenue/groq-owned-baseline/sandbox-preflight.json').read_text())
        baseline = {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                    'output': 'Ran 2 tests\nFAILED (failures=1)'}
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict('os.environ', {'BOUNTYFORGE_CURATED_DOCKER': '1'}), \
                patch.object(runner, 'tests', return_value=baseline), \
                patch('bountyforge.curated_docker.verify_runtime_boundary', return_value=proof):
            result = runner.run(model=Invalid(), protocol='ast_contract_v7', backend='groq',
                                output=Path(directory) / 'report.json')
        result['inference_backend'] = {'provider': 'groq', 'model': MODEL_ID,
                                       'transport_calls': result['model_calls'],
                                       'total_generation_tokens_per_call': 1024,
                                       'minimum_interval_seconds': 60}
        return result

    def test_completed_zero_score_validates_without_any_target_execution(self):
        report = self.hosted_zero_report()
        with patch('scripts.verify_phase5_repairs.run_curated', side_effect=AssertionError('No success')):
            checked = verify(report, expected_revision=report['revision'])
        self.assertEqual(checked['passed'], 0)
        self.assertFalse(checked['billing_independently_verified'])

    def test_hosted_gate_rejects_missing_revision_usage_and_docker_controls(self):
        original = self.hosted_zero_report()
        with self.assertRaises(ValueError): verify(original)
        for change in ('revision', 'provider', 'backend', 'tokens', 'response', 'sandbox', 'blocked', 'timing', 'false_success'):
            report = copy.deepcopy(original)
            call = report['tasks'][0]['attempts'][0]['calls'][0]
            if change == 'revision': report['revision'] = '0' * 40
            elif change == 'provider': call['model_metadata']['provider_model_reported'] = 'other'
            elif change == 'backend': report['inference_provider'] = 'local_qwen'
            elif change == 'tokens': call['model_metadata']['completion_tokens'] = 1025
            elif change == 'response': call['response'] = '{}'
            elif change == 'sandbox': report['sandbox_preflight']['network_denied'] = False
            elif change == 'blocked': report['tasks'][-1]['status'] = 'blocked'
            elif change == 'timing': report['adapter_wall_seconds_including_pacing'] = 99999
            elif change == 'false_success': report['tasks'][0]['model_generated_success'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify(report, expected_revision=original['revision'])

    def test_successful_transcript_cannot_change_scope_or_stale_source_binding(self):
        from scripts.verify_phase5_repairs import validate_successful_transcript
        import hashlib
        source = 'def f(x):\n    return x\n'
        call = {'symbol': 'f', 'kind': 'patch', 'stage': 'source_validated',
                'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'prompt': json.dumps({'approved_file': 'module.py', 'target_symbol': 'f', 'editable_lines': [2]}),
                'response': '{"changes":[{"line":2,"new":"return x # UNIT_ONLY"}]}'}
        task = {'file': 'module.py', 'symbols': ['f']}
        revised, proposals = validate_successful_transcript(source, task, [call], 'ast_contract_v7')
        self.assertIn('UNIT_ONLY', revised)
        self.assertEqual(len(proposals), 1)
        for field, value in [('source_sha256', '0' * 64), ('prompt', '{}'), ('stage', 'source_rejected')]:
            with self.subTest(field=field), self.assertRaises((ValueError, KeyError)):
                validate_successful_transcript(source, task, [{**call, field: value}], 'ast_contract_v7')

    def test_eight_call_cap_reserves_attempts_for_all_five_cases(self):
        class Neutral:
            calls = 0
            def complete_line(self, system, prompt, max_tokens):
                self.calls += 1
                data = json.loads(prompt)
                line = data['editable_lines'][-1]
                row = next(r.split(': ', 1)[1] for r in data['source_lines_untrusted'].split('\n')
                           if r.startswith(str(line) + ': '))
                return json.dumps({'changes': [{'line': line, 'new': row + f' # UNIT_ONLY_{self.calls}'}]})
        model = Neutral()
        baseline = {'passed': False, 'returncode': 1, 'output': 'FAILED (failures=1)'}
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict('os.environ', {'BOUNTYFORGE_CURATED_DOCKER': '1'}), \
                patch.object(runner, 'tests', return_value=baseline), \
                patch('bountyforge.curated_docker.verify_runtime_boundary', return_value={}):
            result = runner.run(model=model, protocol='ast_contract_v7', backend='groq',
                                output=Path(directory) / 'report.json')
        self.assertEqual(result['max_total_model_calls'], 8)
        self.assertEqual(result['model_calls'], model.calls)
        self.assertEqual(model.calls, 8)
        self.assertEqual(result['attempted'], 5)
        self.assertEqual(result['blocked'], 0)
        self.assertEqual(result['passed'], 0)
        self.assertIsNone(result['model_sha256'])
        self.assertEqual(result['run_type'], 'real_groq_hosted')
        self.assertTrue(any(t.get('retry_omitted') for t in result['tasks']))

    def test_hosted_backend_cannot_silently_use_local_or_legacy_protocol(self):
        for options in ({'backend': 'groq'}, {'backend': 'unknown'},
                        {'backend': 'groq', 'protocol': 'ast_contract_v6', 'model': object()}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                runner.run(**options)

    def test_hosted_transport_failure_remains_blocked_not_zero_score(self):
        class Unavailable:
            def complete_line(self, *args, **kwargs):
                raise RuntimeError('UNIT_ONLY unavailable')
        baseline = {'passed': False, 'returncode': 1, 'output': 'FAILED (failures=1)'}
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict('os.environ', {'BOUNTYFORGE_CURATED_DOCKER': '1'}), \
                patch.object(runner, 'tests', return_value=baseline), \
                patch('bountyforge.curated_docker.verify_runtime_boundary', return_value={}):
            result = runner.run(model=Unavailable(), protocol='ast_contract_v7', backend='groq',
                                output=Path(directory) / 'report.json')
        self.assertEqual(result['model_calls'], 1)
        self.assertEqual(result['blocked'], 5)
        self.assertIsNone(result['tasks'][0]['attempts'][0]['calls'][0]['model_metadata'])
        self.assertEqual(result['tasks'][0]['attempts'][0]['failure_reason'], 'inference_unavailable_or_timeout')


if __name__ == '__main__':
    unittest.main()
