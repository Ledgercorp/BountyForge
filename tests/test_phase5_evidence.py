import copy
import hashlib
import json
import unittest
from pathlib import Path
from scripts.verify_phase5_repairs import verify, validate_successful_transcript
from unittest.mock import patch
from benchmarks.phase4 import benchmark_runner as runner
import tempfile


class Phase5EvidenceTests(unittest.TestCase):
    def setUp(self):
        class Invalid:
            def complete_line(self,*a,**kw):return '{"changes":[]}'
        with tempfile.TemporaryDirectory() as d, patch.dict('os.environ', {'BOUNTYFORGE_CURATED_DOCKER':'1'}), patch.object(runner,'tests',return_value={'passed':False,'returncode':1,'output':'FAILED (failures=1)'}), patch('bountyforge.curated_docker.verify_runtime_boundary',return_value={}):
            self.report=runner.run(model=Invalid(),output=Path(d)/'report.json')
    def test_zero_success_is_truthful_without_executing_any_target(self):
        with patch('scripts.verify_phase5_repairs.run_curated',side_effect=AssertionError('No success to execute')):
            result=verify(self.report)
        self.assertEqual(result['passed'],0)
        self.assertEqual(result['inference_calls'],0)
    def test_tampered_score_source_and_call_counts_rejected(self):
        for field,value in [('passed',1),('model_calls',1),('blocked',1)]:
            report=copy.deepcopy(self.report);report[field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):verify(report)
        report=copy.deepcopy(self.report);report['tasks'][0]['source_sha256']='0'*64
        with self.assertRaises(ValueError):verify(report)
    def test_missing_or_invented_success_rejected(self):
        report=copy.deepcopy(self.report);report['tasks'][0]['model_generated_success']=True
        with self.assertRaises(ValueError):verify(report)


class DiagnosisEvidenceTests(unittest.TestCase):
    def calls(self,patchline=2):
        source='def f():\n    x=1\n    return x\n'
        common={'symbol':'f','source_sha256':hashlib.sha256(source.encode()).hexdigest()}
        data={'approved_file':'app.py','target_symbol':'f','editable_lines':[2,3]}
        diagnosis={**common,'kind':'diagnosis','prompt':json.dumps(data),
                   'response':json.dumps({'lines':[2],'reason':'inspect assignment'})}
        data['editable_lines']=[2]
        patch_call={**common,'kind':'patch','stage':'source_validated','prompt':json.dumps(data),
                    'response':json.dumps({'changes':[{'line':patchline,'new':'x=2' if patchline==2 else 'return x+1'}]})}
        return source,[diagnosis,patch_call]
    def test_valid_ordered_narrowing_replays_without_execution(self):
        source,calls=self.calls()
        revised,proposals=validate_successful_transcript(source,{'file':'app.py','symbols':['f']},calls,'ast_contract_v6')
        self.assertIn('x=2',revised);self.assertEqual(len(proposals),1)
    def test_tampered_diagnosis_cannot_authorize_other_original_scope_line(self):
        source,calls=self.calls(patchline=3)
        with self.assertRaises(ValueError):
            validate_successful_transcript(source,{'file':'app.py','symbols':['f']},calls,'ast_contract_v6')
    def test_tampered_order_and_stale_source_fail_closed(self):
        source,calls=self.calls()
        for changed in (list(reversed(calls)),[calls[0],{**calls[1],'source_sha256':'0'*64}]):
            with self.assertRaises(ValueError):
                validate_successful_transcript(source,{'file':'app.py','symbols':['f']},changed,'ast_contract_v6')
