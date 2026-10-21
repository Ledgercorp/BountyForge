import importlib.util,json,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('runner',HERE/'benchmark_runner.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
class BenchmarkTests(unittest.TestCase):
 def test_five_historical_tasks_grounded(self):
  tasks=runner.MANIFEST['tasks'];self.assertEqual(len(tasks),5)
  self.assertEqual({x['id'] for x in tasks},{'454','459','460','475','524'})
  for t in tasks:
   self.assertTrue(t['issue'].startswith('https://github.com/mahmoud/boltons/'))
   self.assertIn(t['blob'],{'5df8cf6f2e067ce5a11691304f67faf6c2bac7cb','856bf195483aafbfcdb8f6f93a168daf0c9b5857'})
   self.assertTrue((HERE/'tasks'/t['id']/t['file']).is_file())
 def test_exact_valid_patch(self):
  source='def f():\n    return 1\n'
  fixed,diff=runner.stage(source,'{"edits":[{"path":"target.py","old":"return 1","new":"return 2"}]}','target.py')
  self.assertIn('return 2',fixed);self.assertIn('-    return 1',diff)
 def test_unauthorized_path(self):
  with self.assertRaises(ValueError):runner.stage('def f(): pass','{"edits":[{"path":"../../etc/passwd","old":"pass","new":"1"}]}','target.py')
 def test_invalid_python(self):
  with self.assertRaises(SyntaxError):runner.stage('def f():\n    return 1\n','{"edits":[{"path":"target.py","old":"return 1","new":"return ("}]}','target.py')
 def test_duplicate_old_rejected(self):
  with self.assertRaises(ValueError):runner.stage('a=1\na=1\n','{"edits":[{"path":"target.py","old":"a=1","new":"a=2"}]}','target.py')
 def test_no_namespace_or_host_execution_fallback(self):
  with patch.dict('os.environ',{},clear=True):
   result=runner.tests(Path('/does-not-exist'))
  self.assertEqual(result.get('error'),'sandbox_not_admitted')
  self.assertFalse(result['passed'])
 def test_blocked_cycle_records_no_model_attempts(self):
  class NeverModel:
   def complete_line(self,*args,**kwargs):raise AssertionError('Inference must not be reached')
  with tempfile.TemporaryDirectory() as d,patch.dict('os.environ',{'BOUNTYFORGE_CURATED_DOCKER':'0'}):
   out=Path(d)/'fresh.json'
   result=runner.run(model=NeverModel(),output=out)
   self.assertEqual(result['attempted'],0)
   self.assertEqual(result['model_calls'],0)
   self.assertEqual(result['blocked'],5)
   self.assertNotEqual(result['run_type'],'real_qwen_cpu')
   self.assertEqual(json.loads(out.read_text())['blocked'],5)
 def test_rejected_calls_retain_transcript_and_latency(self):
  class InvalidModel:
   last_call={'finish_reason':'stop'}
   def complete_line(self,*args,**kwargs):return '{"changes":[]}'
  baseline={'passed':False,'returncode':1,'output':'FAILED (failures=1)'}
  with tempfile.TemporaryDirectory() as d,patch.dict('os.environ',{'BOUNTYFORGE_CURATED_DOCKER':'1'}),patch.object(runner,'tests',return_value=baseline),patch('bountyforge.curated_docker.verify_runtime_boundary',return_value={'test_only':True}):
   result=runner.run(model=InvalidModel(),output=Path(d)/'calls.json')
  calls=[c for t in result['tasks'] for a in t['attempts'] for c in a['calls']]
  self.assertGreater(len(calls),0)
  self.assertEqual(len(calls),result['model_calls'])
  for c in calls:
   self.assertEqual(c['response'],'{"changes":[]}')
   self.assertEqual(c['stage'],'source_rejected')
   self.assertGreaterEqual(c['seconds'],0)
   self.assertIn('target_symbol',json.loads(c['prompt']))
if __name__=='__main__': unittest.main()
