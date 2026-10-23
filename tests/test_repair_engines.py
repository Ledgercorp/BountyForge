"""Phase12 contract tests; fake observations below are never model evidence."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class EngineContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('bountyforge.repair_engines'),
                             'The selectable owned-repair contract is missing')
        self.api = importlib.import_module('bountyforge.repair_engines')

    def service(self, results=None):
        api = self.api
        class Observations:
            def preflight(self):
                from bountyforge.phase8_evaluation import CONTROLS
                from bountyforge.curated_docker import IMAGE
                return {**dict.fromkeys(CONTROLS, True), 'image_digest': IMAGE.split('@')[1],
                        'untrusted_execution_certified': False}
            def observe(self, spec, candidate=None):
                if candidate is None:
                    return {'passed':False,'exit_code':1,'timeout':False,
                            'output':'FAIL: test_weighted (test_regression.Contract.test_weighted)\nAssertionError\nRan 1 test\nFAILED (failures=1)'}
                passed = next(values)
                if isinstance(passed,Exception):raise passed
                return {'passed':passed,'exit_code':0 if passed else 1,'timeout':False,
                        'output':'Ran 1 test\n'+('OK' if passed else 'FAILED (failures=1)')}
        values = iter(results or [False, False])
        return api.RepairService(verifier=Observations())

    def test_both_modes_are_explicit_and_no_automatic_codex_provider_exists(self):
        modes = self.api.engine_inventory()
        self.assertEqual([x['id'] for x in modes], ['QWEN_LOCAL', 'CODEX_AGENT'])
        self.assertEqual([x['label'] for x in modes], ['Autonomous Qwen', 'Codex Agent'])
        self.assertFalse(modes[1]['unattended_backend_available'])
        self.assertFalse(any(x['paid_fallback'] for x in modes))

    def test_task_handoff_has_source_units_but_no_tests_answers_or_paths(self):
        task = self.service().prepare('weighted-mix', 'CODEX_AGENT')
        self.assertIn('def weighted_mix', task['source'])
        self.assertTrue(task['edit_units'])
        self.assertFalse(task['independent_evaluation'])
        self.assertNotIn('tests', task)
        self.assertNotIn('reference', task)
        with self.assertRaises(self.api.RepairRejected):
            self.service().prepare('../../secret', 'CODEX_AGENT')
        with self.assertRaises(self.api.RepairRejected):
            self.service().prepare('weighted-mix', 'GROQ')

    def test_revision_is_fenced_and_wrong_engine_cannot_submit(self):
        service = self.service(); task = service.prepare('weighted-mix', 'CODEX_AGENT')
        with self.assertRaises(self.api.RepairRejected):
            service.submit(task['task_id'], 7, {'changes':[]})
        qwen = service.prepare('weighted-mix', 'QWEN_LOCAL')
        with self.assertRaises(self.api.RepairRejected):
            service.submit(qwen['task_id'], 0, {'changes':[]})

    def test_detailed_statement_rejection_and_bounded_revisions(self):
        service = self.service(); task = service.prepare('weighted-mix', 'CODEX_AGENT')
        bad = {'changes':[{'line':5,'new':'if denominator:\n    return 0'}]}
        one = service.submit(task['task_id'], 0, bad)
        self.assertEqual(one['outcome'], 'SOURCE_REJECTED')
        self.assertIn('expression', one['diagnostic'])
        two = service.submit(task['task_id'], 1, bad)
        self.assertEqual(two['outcome'], 'REPEATED_PROPOSAL')
        self.assertEqual(two['state'], 'EXHAUSTED')
        self.assertNotEqual(one['receipt_sha256'], two['receipt_sha256'])
        with self.assertRaises(self.api.RepairRejected):
            service.submit(task['task_id'], 2, bad)

    def test_test_failures_and_independent_failures_never_promote(self):
        for values, outcome in [([False], 'TEST_FAILED'), ([True, False], 'INDEPENDENT_VERIFICATION_FAILED')]:
            with self.subTest(outcome=outcome):
                service = self.service(values); task = service.prepare('weighted-mix', 'CODEX_AGENT')
                result = service.submit(task['task_id'], 0, {'changes':[{'line':4,'new':'denominator = 123'}]})
                self.assertEqual(result['outcome'], outcome)
                self.assertFalse(result['independently_verified'])

    def test_same_hash_bound_receipt_requires_two_fresh_passing_observations(self):
        service=self.service([True, True]); task=service.prepare('weighted-mix','CODEX_AGENT')
        result=service.submit(task['task_id'],0,{'changes':[{'line':4,'new':'denominator = 123'}]})
        self.assertTrue(result['independently_verified'])
        self.assertEqual(result['state'],'AWAITING_OWNER_APPROVAL')
        self.assertEqual(result['engine'],'CODEX_AGENT')
        self.assertFalse(result['authorship_identity_attested'])
        self.assertEqual(result['receipt_sha256'],self.api.receipt_hash(result))
        self.assertFalse(result['delivery_authorized'])

    def test_runtime_and_provider_failures_are_distinct_and_no_hidden_fallback(self):
        service=self.service(); task=service.prepare('weighted-mix','QWEN_LOCAL')
        with patch.object(self.api, 'qwen_availability', return_value=False), \
                patch.object(self.api, 'LocalModel') as model:
            result=service.run_qwen(task['task_id'],0)
            model.assert_not_called()
            self.assertEqual(result['outcome'],'QWEN_UNAVAILABLE')
        with self.assertRaises(self.api.RepairRejected):
            service.run_qwen('missing',0)

    def test_qwen_uses_same_submission_validator_and_records_actual_calls(self):
        service=self.service([False,False]); task=service.prepare('weighted-mix','QWEN_LOCAL')
        class Model:
            last_call={'prompt_tokens':5,'completion_tokens':4}
            def complete_line(self,*args,**kwargs):
                return json.dumps({'changes':[{'line':4,'new':'denominator = 123'}]})
        with patch.object(self.api,'qwen_availability',return_value=True), \
                patch.object(self.api,'LocalModel',return_value=Model()):
            result=service.run_qwen(task['task_id'],0)
        self.assertEqual(result['engine'],'QWEN_LOCAL')
        self.assertEqual(result['model_calls'],2)
        self.assertFalse(result['independently_verified'])
        self.assertEqual(result['attempts'][0]['outcome'],'TEST_FAILED')
        self.assertEqual(result['attempts'][1]['outcome'],'REPEATED_PROPOSAL')

    def test_independent_runner_outage_identifies_its_stage(self):
        service=self.service([True,RuntimeError('private host details must not escape')])
        task=service.prepare('weighted-mix','CODEX_AGENT')
        result=service.submit(task['task_id'],0,{'changes':[{'line':4,'new':'denominator = 123'}]})
        self.assertEqual(result['state'],'BLOCKED')
        self.assertEqual(result['failure_stage'],'independent_replay')
        self.assertNotIn('private host',json.dumps(result))

    def test_admission_outage_is_not_inference_failure(self):
        service=self.service()
        with patch.object(service.verifier,'preflight',side_effect=RuntimeError('internal')):
            with self.assertRaisesRegex(self.api.RepairUnavailable,'SANDBOX_ADMISSION_UNAVAILABLE'):
                service.prepare('weighted-mix','CODEX_AGENT')

    def test_nonregular_manifest_is_rejected_before_reading(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);os.mkfifo(root/'manifest.json')
            original=Path.read_bytes
            def guarded(path):
                if path==root/'manifest.json':raise AssertionError('A FIFO must never be read')
                return original(path)
            with patch.object(self.api,'CATALOG',root),patch.object(Path,'read_bytes',guarded):
                with self.assertRaises(self.api.RepairRejected):self.api.catalog()

    def test_expiration_and_process_restart_do_not_revive_capabilities(self):
        service=self.service();task=service.prepare('weighted-mix','CODEX_AGENT')
        service.tasks[task['task_id']]['created']-=601
        with self.assertRaises(self.api.RepairRejected):service.submit(task['task_id'],0,{'changes':[]})
        with self.assertRaises(self.api.RepairRejected):self.service().submit(task['task_id'],0,{'changes':[]})

    def test_equivalent_ast_candidate_is_not_executed_twice(self):
        service=self.service([False]);task=service.prepare('weighted-mix','CODEX_AGENT')
        first=service.submit(task['task_id'],0,{'changes':[{'line':4,'new':'denominator=123'}]})
        self.assertEqual(first['outcome'],'TEST_FAILED')
        second=service.submit(task['task_id'],1,{'changes':[{'line':4,'new':'denominator = 123'}]})
        self.assertEqual(second['outcome'],'REPEATED_PROPOSAL')
        self.assertNotIn('targeted',second)


if __name__=='__main__': unittest.main()
