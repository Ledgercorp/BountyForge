import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.worker import repair_fixture

class FaultModel:
 def __init__(self,result): self.result=result;self.calls=0
 def complete_line(self,system,prompt,max_tokens):
  self.calls+=1
  if isinstance(self.result,Exception): raise self.result
  return self.result

class OperationalControls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  (self.root/'.bountyforge-controlled-fixture').write_text('owned fault fixture')
  (self.root/'calc.py').write_text('def add(a,b):\n    return a-b\n')
  (self.root/'tests').mkdir()
  (self.root/'tests/test_calc.py').write_text('import unittest\nfrom calc import add\nclass T(unittest.TestCase):\n def test_add(self): self.assertEqual(add(2,3),5)\n def test_related(self): self.assertEqual(add(-2,3),1)\n')
  self.issue={'verification':'unverified_candidate','description_excerpt':'addition'}
 def run_model(self,model,attempts=2):
  return repair_fixture(self.issue,self.root,['calc.py'],model,strategy='auto_line',max_attempts=attempts)
 def test_model_timeout_stops_after_one_request(self):
  model=FaultModel(TimeoutError('fault injection'))
  result=self.run_model(model)
  self.assertEqual(model.calls,1);self.assertEqual(result['status'],'failed')
 def test_partial_repair_fails_related_regression(self):
  model=FaultModel(json.dumps({'changes':[{'line':2,'new':'return 5'}]}))
  result=self.run_model(model)
  self.assertEqual(result['status'],'failed');self.assertIsNone(result['patch'])
  self.assertTrue(all(not a['test']['passed'] for a in result['attempts']))
 def test_model_attempt_budget_exhaustion(self):
  model=FaultModel('{"changes":[]}')
  result=self.run_model(model)
  self.assertEqual(model.calls,2);self.assertEqual(result['status'],'failed')
  with self.assertRaises(ValueError):self.run_model(model,attempts=3)
