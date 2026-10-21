import copy
import hashlib
import json
import unittest
from pathlib import Path
from scripts.verify_phase5_repairs import verify
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
