import json,tempfile,unittest
from pathlib import Path
from bountyforge.operator import process_one
from bountyforge.queue import Queue

class Model:
 def complete(self,system,user,max_tokens):
  return json.dumps({'files':[{'path':'calc.py','content':'def add(a,b):\n    return a+b\n'}]})
class OperatorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  base=Path(self.tmp.name)
  self.q=Queue(base/'q.db');self.addCleanup(self.q.close)
  fixture=base/'fixture';fixture.mkdir()
  (fixture/'.bountyforge-controlled-fixture').write_text('synthetic')
  (fixture/'calc.py').write_text('def add(a,b):\n    return a-b\n')
  (fixture/'tests').mkdir()
  (fixture/'tests'/'test_calc.py').write_text('import unittest\nfrom calc import add\nclass T(unittest.TestCase):\n def test_add(self): self.assertEqual(add(2,3),5)\n')
  self.catalog={'addition':{'root':fixture,'approved_paths':['calc.py'],'issue':{'title':'Fix add','description_excerpt':'return a+b','verification':'unverified_candidate'}}}
 def test_one_job_durable(self):
  self.q.enqueue('repair-1',{'fixture_id':'addition'})
  r=process_one(self.q,self.catalog,Model());self.assertEqual(r['state'],'review_ready')
  self.assertEqual(self.q.get('repair-1')['state'],'review_ready')
  self.assertEqual(process_one(self.q,self.catalog,Model())['state'],'idle')
 def test_unknown_fixture_rejected(self):
  self.q.enqueue('bad',{'fixture_id':'third_party'})
  r=process_one(self.q,self.catalog,Model());self.assertEqual(r['state'],'failed')
if __name__=='__main__': unittest.main()