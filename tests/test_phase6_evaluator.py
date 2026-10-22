"""Offline paired coordinator and source-admission negatives; no benchmark claims."""
import copy
import hashlib
import importlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load_module(name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        raise AssertionError('Missing paired evaluation implementation: ' + name) from None


def proof():
    return json.loads(Path('evidence/revenue/groq-owned-baseline/sandbox-preflight.json').read_text())


class InvalidModel:
    total_generation_tokens = 1024
    minimum_interval_seconds = 60
    calls = 0
    last_call = None
    def complete_line(self, *args, **kwargs):
        self.calls += 1
        self.last_call = {'provider': 'groq', 'model': 'openai/gpt-oss-120b',
                          'provider_model_reported': 'openai/gpt-oss-120b',
                          'finish_reason': 'stop', 'requested_max_completion_tokens': 1024,
                          'prompt_tokens': 500, 'completion_tokens': 100, 'total_tokens': 600,
                          'reasoning_tokens': 80}
        return '{"changes":[]}'


class PairedEvaluatorTests(unittest.TestCase):
    def test_eight_counterbalanced_arms_share_four_cached_baselines(self):
        module = load_module('scripts.phase6_evaluate')
        model = InvalidModel()
        failed = {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                  'output': 'FAIL: test_contract (Contract.test_contract)\nAssertionError: UNIT_ONLY\nRan 6 tests\nFAILED (failures=1)',
                  'elapsed_seconds': 0.1}
        with tempfile.TemporaryDirectory() as directory, patch.object(module, '_execute', return_value=failed) as execute:
            report = module.evaluate(model=model, proof=proof(), output=Path(directory)/'report.json', revision='a'*40)
            saved = json.loads((Path(directory)/'report.json').read_text())
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['model_calls'], 8)
        self.assertEqual(len(report['arms']), 8)
        self.assertEqual(execute.call_count, 4)
        self.assertEqual([a['arm'] for a in report['arms']], ['line','statement','statement','line','line','statement','statement','line'])
        self.assertEqual(report['scores'], {'line': 0, 'statement': 0})
        self.assertEqual(saved['calls'], report['calls'])
        self.assertTrue(all(c['response_sha256'] == hashlib.sha256(c['response'].encode()).hexdigest() for c in report['calls']))
        self.assertTrue(all(c['metadata']['completion_tokens'] == 100 for c in report['calls']))

    def test_non_assertion_baseline_is_blocked_without_final_score(self):
        module = load_module('scripts.phase6_evaluate')
        bad = {'passed':False,'returncode':1,'timeout':False,'error':None,
               'output':'ERROR: test_import (Contract.test_import)\nRan 1 test\nFAILED (errors=1)', 'elapsed_seconds':.1}
        model=InvalidModel()
        with tempfile.TemporaryDirectory() as directory, patch.object(module,'_execute',return_value=bad):
            report=module.evaluate(model=model,proof=proof(),output=Path(directory)/'report.json',revision='a'*40)
        self.assertEqual(report['status'],'blocked')
        self.assertEqual(report.get('score_final'),False)
        self.assertEqual(report['model_calls'],0)
        self.assertTrue(all(row['status']=='blocked' for row in report['arms']))

    def test_bad_proof_never_runs_docker_or_inference(self):
        module = load_module('scripts.phase6_evaluate')
        model = InvalidModel(); bad = proof(); bad['network_denied'] = False
        with tempfile.TemporaryDirectory() as directory, patch.object(module, '_execute') as execute:
            with self.assertRaises(ValueError):
                module.evaluate(model=model, proof=bad, output=Path(directory)/'report.json', revision='a'*40)
        self.assertEqual(model.calls, 0)
        execute.assert_not_called()

    def test_changed_tests_extra_files_and_symlinks_fail_before_docker(self):
        module = load_module('scripts.phase6_evaluate')
        task = module.catalog()['tasks'][0]
        for change in ('tests', 'extra', 'symlink', 'hardlink', 'source'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'candidate'; shutil.copytree(module.TASKS/task['id'], root)
                (root/module.FIXTURE_MARKER).write_text(task['id'])
                if change == 'tests': (root/'tests/test_regression.py').write_text('print("OK")\n')
                elif change == 'extra': (root/'extra.py').write_text('pass\n')
                elif change == 'symlink': (root/'extra').symlink_to(root/task['file'])
                elif change == 'hardlink': os.link(root/task['file'], root/'linked')
                else: (root/task['file']).write_text('raise RuntimeError("UNIT_ONLY")\n')
                with self.assertRaises(ValueError): module.admit(root, task, arm='line', response=None)

    def test_caller_authored_task_metadata_is_rejected(self):
        module = load_module('scripts.phase6_evaluate')
        task = module.catalog()['tasks'][0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'candidate'; shutil.copytree(module.TASKS/task['id'], root)
            (root/module.FIXTURE_MARKER).write_text(task['id'])
            changed = dict(task, description='caller-authored')
            with self.assertRaises(ValueError): module.admit(root, changed, arm='line', response=None)

    def test_pre_http_value_error_blocks_and_fuses_remaining_inference(self):
        module = load_module('scripts.phase6_evaluate')
        class InvalidRequest(InvalidModel):
            def complete_line(self,*args,**kwargs): raise ValueError('UNIT_ONLY pre-HTTP validation')
        failed = {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                  'output': 'FAIL: test_contract (Contract.test_contract)\nRan 6 tests\nFAILED (failures=1)', 'elapsed_seconds': .1}
        with tempfile.TemporaryDirectory() as directory, patch.object(module, '_execute', return_value=failed):
            report = module.evaluate(model=InvalidRequest(), proof=proof(), output=Path(directory)/'report.json', revision='a'*40)
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['score_final'])
        self.assertEqual(report['model_calls'], 0)
        self.assertEqual(len(report['calls']), 1)

    def test_pre_inference_scope_rejection_cannot_complete_comparison(self):
        module = load_module('scripts.phase6_evaluate')
        from bountyforge.drafts import DraftRejected
        failed = {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                  'output': 'FAIL: test_contract (Contract.test_contract)\nRan 6 tests\nFAILED (failures=1)', 'elapsed_seconds': .1}
        with tempfile.TemporaryDirectory() as directory, patch.object(module, '_execute', return_value=failed), \
                patch('bountyforge.worker.propose_lines', side_effect=DraftRejected('UNIT_ONLY oversized context')):
            report = module.evaluate(model=InvalidModel(), proof=proof(), output=Path(directory)/'report.json', revision='a'*40)
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['score_final'])
        self.assertEqual(report['model_calls'], 4)
        self.assertEqual(sum(row.get('failure_reason') == 'scope_or_context_rejected_before_inference' for row in report['arms']), 4)

    def test_missing_or_wrong_provider_metadata_fuses_model_stream(self):
        module = load_module('scripts.phase6_evaluate')
        class WrongIdentity(InvalidModel):
            def complete_line(self,*args,**kwargs):
                response = super().complete_line(*args,**kwargs)
                self.last_call['provider_model_reported'] = 'other'
                return response
        failed = {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                  'output': 'FAIL: test_contract (Contract.test_contract)\nRan 6 tests\nFAILED (failures=1)', 'elapsed_seconds': .1}
        with tempfile.TemporaryDirectory() as directory, patch.object(module, '_execute', return_value=failed):
            report = module.evaluate(model=WrongIdentity(), proof=proof(), output=Path(directory)/'report.json', revision='a'*40)
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['score_final'])
        self.assertEqual(report['model_calls'], 1)

    def test_transport_failure_checkpoints_then_stops_without_scoring_remaining_arms(self):
        module = load_module('scripts.phase6_evaluate')
        class Unavailable(InvalidModel):
            def complete_line(self,*args,**kwargs):
                self.calls += 1
                raise RuntimeError('UNIT_ONLY unavailable')
        failed = {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                  'output': 'FAIL: test_contract (Contract.test_contract)\nRan 6 tests\nFAILED (failures=1)', 'elapsed_seconds': .1}
        with tempfile.TemporaryDirectory() as directory, patch.object(module, '_execute', return_value=failed):
            report = module.evaluate(model=Unavailable(), proof=proof(), output=Path(directory)/'report.json', revision='a'*40)
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['model_calls'], 1)
        self.assertEqual(len(report['calls']), 1)
        self.assertEqual(report['calls'][0]['error'], 'RuntimeError')
        self.assertEqual(sum(a['status'] == 'blocked' for a in report['arms']), 8)

    def test_independent_worker_failure_cannot_be_a_completed_experiment(self):
        module=load_module('scripts.phase6_evaluate')
        failed={'passed':False,'returncode':1,'timeout':False,'error':None,
                'output':'FAIL: test_contract (Contract.test_contract)\nRan 6 tests\nFAILED (failures=1)','elapsed_seconds':.1}
        def failed_worker(issue,root,paths,model,**kwargs):
            model.complete_line('UNIT_ONLY', '{"editable_lines":[2]}',150)
            return {'status':'failed','error':'independent_verification_failed',
                    'attempts':[{'number':1,'status':'failed','error':'independent_verification_failed'}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(module,'_execute',return_value=failed), \
                patch.object(module,'repair_fixture',side_effect=failed_worker):
            report=module.evaluate(model=InvalidModel(),proof=proof(),output=Path(directory)/'report.json',revision='a'*40)
        self.assertEqual(report['status'],'blocked')
        self.assertFalse(report['score_final'])

    def test_candidate_sandbox_failure_blocks_and_fuses_remaining_inference(self):
        module = load_module('scripts.phase6_evaluate')
        from bountyforge.curated_docker import CuratedSandboxUnavailable
        class Neutral(InvalidModel):
            def complete_line(self,system,prompt,max_tokens):
                super().complete_line(system,prompt,max_tokens)
                data=json.loads(prompt); line=data['editable_lines'][-1]
                row=next(r.split(': ',1)[1] for r in data['source_lines_untrusted'].split('\n')
                         if r.startswith(str(line)+': '))
                return json.dumps({'changes':[{'line':line,'new':row+' # UNIT_ONLY'}]})
        failed = {'passed':False,'returncode':1,'timeout':False,'error':None,
                  'output':'FAIL: test_contract (Contract.test_contract)\nRan 6 tests\nFAILED (failures=1)','elapsed_seconds':.1}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(module,'_execute',side_effect=[failed]*4+[CuratedSandboxUnavailable('UNIT_ONLY')]):
            report=module.evaluate(model=Neutral(),proof=proof(),output=Path(directory)/'report.json',revision='a'*40)
        self.assertEqual(report['status'],'blocked')
        self.assertFalse(report['score_final'])
        self.assertEqual(report['model_calls'],1)
        self.assertTrue(all(row['status']=='blocked' for row in report['arms']))

    def test_interruption_preserves_incomplete_call_without_promoting_success(self):
        module = load_module('scripts.phase6_evaluate')
        class Interrupted(InvalidModel):
            def complete_line(self,*args,**kwargs):
                self.calls += 1
                raise KeyboardInterrupt()
        failed = {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                  'output': 'FAIL: test_contract (Contract.test_contract)\nRan 6 tests\nFAILED (failures=1)', 'elapsed_seconds': .1}
        with tempfile.TemporaryDirectory() as directory, patch.object(module, '_execute', return_value=failed):
            out = Path(directory)/'report.json'
            with self.assertRaises(KeyboardInterrupt): module.evaluate(model=Interrupted(), proof=proof(), output=out, revision='a'*40)
            saved = json.loads(out.read_text())
        self.assertEqual(saved['status'], 'running')
        self.assertEqual(saved['model_calls'], 1)
        self.assertIsNone(saved['calls'][0]['response'])
        self.assertEqual(saved['scores'], {'line': 0, 'statement': 0})


if __name__ == '__main__': unittest.main()
