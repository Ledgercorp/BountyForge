"""Offline evidence/replay validation; all mocked positives are UNIT_ONLY."""
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_phase6_evaluator import load_module, proof, InvalidModel


class PairedReplayTests(unittest.TestCase):
    def setUp(self):
        guard = patch.dict(os.environ, {name: '' for name in
                          ('GROQ_API_KEY','OPENAI_API_KEY','STRIPE_SECRET_KEY','GITHUB_TOKEN','GH_TOKEN')})
        guard.start(); self.addCleanup(guard.stop)

    def report(self):
        evaluator = load_module('scripts.phase6_evaluate')
        failed = {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                  'output': 'FAIL: test_contract (Contract.test_contract)\nAssertionError: UNIT_ONLY\nRan 6 tests\nFAILED (failures=1)',
                  'elapsed_seconds': .1}
        with tempfile.TemporaryDirectory() as directory, patch.object(evaluator, '_execute', return_value=failed):
            return evaluator.evaluate(model=InvalidModel(), proof=proof(), output=Path(directory)/'report.json', revision='a'*40)

    def test_completed_zero_score_replays_no_targets_and_no_inference(self):
        module = load_module('scripts.phase6_replay')
        report = self.report()
        with patch.object(module, 'verify_runtime_boundary', return_value=proof()) as preflight, \
                patch.object(module, '_execute', side_effect=AssertionError('No successful target to run')):
            result = module.replay(json.dumps(report).encode(), expected_revision='a'*40)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['scores'], {'line': 0, 'statement': 0})
        self.assertEqual(result['model_calls'], 0)
        self.assertEqual(preflight.call_count, 1)

    def one_neutral_positive_report(self):
        evaluator = load_module('scripts.phase6_evaluate')
        class NeutralFirst(InvalidModel):
            def complete_line(self, system, prompt, max_tokens):
                response = super().complete_line(system, prompt, max_tokens)
                if self.calls != 1: return response
                data = json.loads(prompt); number = data['editable_lines'][-1]
                row = next(r.split(': ',1)[1] for r in data['source_lines_untrusted'].split('\n')
                           if r.startswith(str(number)+': '))
                return json.dumps({'changes':[{'line':number,'new':row+' # UNIT_ONLY'}]})
        failed = {'passed':False,'returncode':1,'timeout':False,'error':None,
                  'output':'FAIL: test_contract (Contract.test_contract)\nAssertionError: UNIT_ONLY\nRan 6 tests\nFAILED (failures=1)',
                  'elapsed_seconds':.1}
        passed = {'passed':True,'returncode':0,'timeout':False,'error':None,
                  'output':'Ran 6 tests\nOK\n','elapsed_seconds':.1}
        def run(root, command, timeout):
            return passed if '# UNIT_ONLY' in (Path(root)/'subject.py').read_text() else failed
        with tempfile.TemporaryDirectory() as directory, patch.object(evaluator, '_execute', side_effect=run):
            return evaluator.evaluate(model=NeutralFirst(), proof=proof(), output=Path(directory)/'report.json', revision='a'*40)

    def test_neutral_claim_reconstructs_exact_patch_and_runs_one_independent_target(self):
        module = load_module('scripts.phase6_replay')
        report = self.one_neutral_positive_report()
        self.assertEqual(report['scores'], {'line':1,'statement':0})
        passed = {'passed':True,'returncode':0,'timeout':False,'error':None,
                  'output':'Ran 6 tests\nOK\n','elapsed_seconds':.1}
        with patch.object(module, 'verify_runtime_boundary', return_value=proof()) as preflight, \
                patch.object(module, '_execute', return_value=passed) as execute:
            result = module.replay(json.dumps(report).encode(), expected_revision='a'*40)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['scores'], {'line':1,'statement':0})
        self.assertEqual(preflight.call_count,1); self.assertEqual(execute.call_count,1)
        self.assertTrue(result['cases'][0]['verified'])
        self.assertEqual(result['model_calls'],0)

    def test_late_invalid_record_and_tampered_positive_patch_prevent_all_execution(self):
        module = load_module('scripts.phase6_replay')
        original = self.one_neutral_positive_report()
        for change in ('last_metadata','patch','inner_diff'):
            report = copy.deepcopy(original)
            if change == 'last_metadata': report['calls'][-1]['metadata']['total_tokens'] = 3
            elif change == 'patch': report['arms'][0]['worker']['patch'][0]['diff'] += 'UNIT_ONLY_TAMPER'
            else: report['arms'][0]['worker']['attempts'][0]['diff'] += 'UNIT_ONLY_TAMPER'
            with self.subTest(change=change), patch.object(module, 'verify_runtime_boundary') as preflight, \
                    patch.object(module, '_execute') as execute:
                with self.assertRaises(ValueError): module.replay(json.dumps(report).encode(), expected_revision='a'*40)
                preflight.assert_not_called(); execute.assert_not_called()

    def test_replay_regression_failure_or_timeout_cannot_complete(self):
        module = load_module('scripts.phase6_replay')
        report = self.one_neutral_positive_report()
        for timeout in (False,True):
            failed = {'passed':False,'returncode':1,'timeout':timeout,'error':None,
                      'output':'Ran 6 tests\nFAILED (failures=1)','elapsed_seconds':.1}
            with self.subTest(timeout=timeout), patch.object(module, 'verify_runtime_boundary', return_value=proof()), \
                    patch.object(module, '_execute', return_value=failed):
                result = module.replay(json.dumps(report).encode(), expected_revision='a'*40)
            self.assertNotEqual(result['status'],'completed')
            self.assertEqual(result['scores'], {'line':0,'statement':0})

    def test_tampering_rejects_before_any_docker_call(self):
        module = load_module('scripts.phase6_replay')
        original = self.report()
        for kind in ('revision','response','identity','usage','calls','proof','baseline','score','scope','core','order','blocked'):
            report = copy.deepcopy(original)
            if kind == 'revision': report['revision'] = 'b'*40
            elif kind == 'response': report['calls'][0]['response'] = '{}'
            elif kind == 'identity': report['calls'][0]['metadata']['provider_model_reported'] = 'other'
            elif kind == 'usage': report['calls'][0]['metadata']['completion_tokens'] = 1025
            elif kind == 'calls': report['model_calls'] += 1
            elif kind == 'proof': report['sandbox_preflight']['pid_pressure_enforced'] = False
            elif kind == 'baseline': report['baselines'][report['arms'][0]['id']]['output'] = 'ERROR: unittest import failed'
            elif kind == 'score': report['scores']['line'] = 1
            elif kind == 'scope': report['calls'][0]['prompt'] = '{}'
            elif kind == 'core': report['core_revision'] = '0'*40
            elif kind == 'order': report['arms'].reverse()
            else: report['arms'][0]['status'] = 'blocked'
            with self.subTest(kind=kind), patch.object(module, 'verify_runtime_boundary') as preflight, \
                    patch.object(module, '_execute') as execute:
                with self.assertRaises(ValueError): module.replay(json.dumps(report).encode(), expected_revision='a'*40)
                preflight.assert_not_called(); execute.assert_not_called()

    def test_failed_arms_require_terminal_worker_states_exact_count_and_rejection_evidence(self):
        module = load_module('scripts.phase6_replay')
        original = self.report()
        for change in ('worker_running','attempt_running','worker_count','missing_rejection'):
            report=copy.deepcopy(original); row=report['arms'][0]
            if change == 'worker_running': row['worker']['status']='running'
            elif change == 'attempt_running': row['worker']['attempts'][0]['status']='running'
            elif change == 'worker_count': row['worker']['model_calls']=999
            else:
                row.pop('source_validation_error',None)
                row['worker']['attempts'][0].pop('error',None)
            with self.subTest(change=change), patch.object(module,'verify_runtime_boundary') as preflight:
                with self.assertRaises(ValueError): module.replay(json.dumps(report).encode(),expected_revision='a'*40)
                preflight.assert_not_called()

    def test_success_claim_without_exact_patch_and_candidate_reconstruction_is_rejected(self):
        module = load_module('scripts.phase6_replay')
        report = self.report()
        report['arms'][0]['status'] = 'candidate_passed'
        report['arms'][0]['model_generated_success'] = True
        report['scores']['line'] = 1
        with patch.object(module, 'verify_runtime_boundary') as preflight:
            with self.assertRaises(ValueError): module.replay(json.dumps(report).encode(), expected_revision='a'*40)
            preflight.assert_not_called()

    def test_fabricated_zero_call_context_rejection_is_rejected(self):
        module = load_module('scripts.phase6_replay')
        report = self.report()
        report['calls'].pop(0)
        for number, call in enumerate(report['calls'], 1): call['number'] = number
        for row in report['arms'][1:]: row['call_numbers'] = [row['call_numbers'][0]-1]
        report['arms'][0]['call_numbers'] = []
        report['arms'][0]['failure_reason'] = 'scope_or_context_rejected_before_inference'
        report['model_calls'] = 7
        report['inference_backend']['transport_calls'] = 7
        report['adapter_wall_seconds_including_pacing'] = round(sum(c['seconds'] for c in report['calls']),3)
        with patch.object(module, 'verify_runtime_boundary') as preflight:
            with self.assertRaises(ValueError): module.replay(json.dumps(report).encode(), expected_revision='a'*40)
            preflight.assert_not_called()

    def test_replay_refuses_provider_credentials_before_docker(self):
        module = load_module('scripts.phase6_replay')
        report = self.report()
        with patch.dict(os.environ, {'GROQ_API_KEY':'UNIT_ONLY'}), patch.object(module, 'verify_runtime_boundary') as preflight:
            with self.assertRaises(ValueError): module.replay(json.dumps(report).encode(), expected_revision='a'*40)
            preflight.assert_not_called()

    def test_oversized_report_is_rejected_before_parsing_or_execution(self):
        module = load_module('scripts.phase6_replay')
        with patch.object(module, 'verify_runtime_boundary') as preflight:
            with self.assertRaises(ValueError): module.replay(b'x'*200001, expected_revision='a'*40)
            preflight.assert_not_called()


if __name__ == '__main__': unittest.main()
