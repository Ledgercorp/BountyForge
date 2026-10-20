import json,tempfile,unittest
from pathlib import Path
from bountyforge.worker import repair_fixture
class ScriptedEditModel:
 def __init__(self,*responses):self.responses=list(responses);self.calls=0
 def complete_edit(self,system,user,max_tokens):
  self.calls+=1
  return self.responses.pop(0)
class WorkerMinimalTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);(self.root/'tests').mkdir()
  (self.root/'.bountyforge-controlled-fixture').write_text('trusted controlled fixture')
  (self.root/'calc.py').write_text('def add(a, b):\n    return a - b\n')
  (self.root/'tests/test_calc.py').write_text('import unittest\nfrom calc import add\nclass Test(unittest.TestCase):\n def test_add(self): self.assertEqual(add(2,3),5)\n')
  self.issue={'verification':'unverified_candidate','title':'synthetic regression','description_excerpt':'fix addition'}
  self.correct=json.dumps({'edits':[{'path':'calc.py','old':'return a - b','new':'return a + b'}]})
  self.wrong=json.dumps({'edits':[{'path':'calc.py','old':'return a - b','new':'return a * b'}]})
 def test_minimal_succeeds(self):
  m=ScriptedEditModel(self.correct)
  result=repair_fixture(self.issue,self.root,['calc.py'],m,strategy='minimal')
  self.assertEqual(result['status'],'review_ready');self.assertEqual(m.calls,1)
  self.assertIn('return a - b',(self.root/'calc.py').read_text())
 def test_minimal_wrong_retry_correct(self):
  m=ScriptedEditModel(self.wrong,self.correct)
  result=repair_fixture(self.issue,self.root,['calc.py'],m,strategy='minimal')
  self.assertEqual(result['status'],'review_ready');self.assertEqual(m.calls,2)
 def test_minimal_wrong_path_cannot_succeed(self):
  bad=json.dumps({'edits':[{'path':'tests/test_calc.py','old':'test_add','new':'test_good'}]})
  m=ScriptedEditModel(bad,bad)
  result=repair_fixture(self.issue,self.root,['calc.py'],m,strategy='minimal')
  self.assertEqual(result['status'],'failed');self.assertIsNone(result['patch'])
 def test_minimal_invalid_python_fails(self):
  bad=json.dumps({'edits':[{'path':'calc.py','old':'return a - b','new':'return (('}]})
  m=ScriptedEditModel(bad,bad)
  result=repair_fixture(self.issue,self.root,['calc.py'],m,strategy='minimal')
  self.assertEqual(result['status'],'failed')
if __name__=='__main__':unittest.main()