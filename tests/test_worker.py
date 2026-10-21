import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.worker import repair_fixture
from bountyforge.drafts import DraftRejected

class ScriptedModel:
    def __init__(self, responses): self.responses=list(responses); self.calls=0
    def complete(self, system, user, max_tokens):
        self.calls+=1
        response=self.responses.pop(0)
        if isinstance(response, Exception): raise response
        return response

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name) / 'fixture'; self.root.mkdir()
        (self.root/'.bountyforge-controlled-fixture').write_text('controlled fixture v1')
        (self.root/'calc.py').write_text('def add(a,b):\n    return a-b\n')
        (self.root/'tests').mkdir()
        (self.root/'tests'/'test_calc.py').write_text('import unittest\nfrom calc import add\nclass TestCalc(unittest.TestCase):\n def test_add(self): self.assertEqual(add(2,3),5)\n')
        self.issue={'title':'addition regression','description_excerpt':'add must sum','verification':'unverified_candidate','url':'https://github.com/test/test/issues/1'}
        self.fixed=json.dumps({'files':[{'path':'calc.py','content':'def add(a,b):\n    return a+b\n'}]})
        self.wrong=json.dumps({'files':[{'path':'calc.py','content':'def add(a,b):\n    return a*b\n'}]})
    def run_worker(self, responses): return repair_fixture(self.issue,self.root,['calc.py'],ScriptedModel(responses))
    def test_repair_success(self):
        result=self.run_worker([self.fixed]); self.assertEqual(result['status'],'review_ready')
        self.assertFalse(result['submitted']); self.assertEqual(result['model_calls'],1)
        self.assertEqual((self.root/'calc.py').read_text(),'def add(a,b):\n    return a-b\n')
    def test_repair_wrong_then_correct(self):
        result=self.run_worker([self.wrong,self.fixed]); self.assertEqual(result['status'],'review_ready')
        self.assertEqual([x['status'] for x in result['attempts']],['failed','passed'])
    def test_invalid_json_cannot_pass(self):
        result=self.run_worker(['No patch','No patch']); self.assertEqual(result['status'],'failed'); self.assertIsNone(result['patch'])
    def test_bad_patch_cannot_pass(self):
        result=self.run_worker([self.wrong,self.wrong]); self.assertEqual(result['status'],'failed')
    def test_model_unavailable(self):
        result=self.run_worker([RuntimeError('offline'),RuntimeError('offline')]); self.assertEqual(result['status'],'failed')
        self.assertEqual(result['model_calls'],1)
    def test_empty_test_suite_does_not_pass(self):
        from bountyforge.worker import _run_tests
        (self.root/'tests'/'test_calc.py').unlink()
        self.assertFalse(_run_tests(self.root)['passed'])
    def test_baseline_import_error_does_not_trigger_inference(self):
        (self.root/'calc.py').write_text('raise ImportError("broken dependency")\n')
        model=ScriptedModel([self.fixed])
        result=repair_fixture(self.issue,self.root,['calc.py'],model)
        self.assertEqual(model.calls,0)
    def test_baseline_must_fail(self):
        (self.root/'calc.py').write_text('def add(a,b):\n    return a+b\n')
        model=ScriptedModel([self.fixed]); result=repair_fixture(self.issue,self.root,['calc.py'],model)
        self.assertEqual(result['error'],'baseline_does_not_reproduce'); self.assertEqual(model.calls,0)
    def test_fixture_marker_required(self):
        (self.root/'.bountyforge-controlled-fixture').unlink()
        with self.assertRaises(DraftRejected): self.run_worker([self.fixed])
    def test_forged_test_patch_denied(self):
        model=ScriptedModel([json.dumps({'files':[{'path':'tests/test_calc.py','content':'pass'}]})]*2)
        result=repair_fixture(self.issue,self.root,['calc.py'],model); self.assertEqual(result['status'],'failed')
    def test_explicit_process_timeout_is_failure(self):
        from bountyforge.worker import _run_tests
        (self.root/'tests'/'test_calc.py').write_text('import unittest,time\nclass T(unittest.TestCase):\n def test_sleep(self): time.sleep(30)\n')
        outcome=_run_tests(self.root,timeout=1)
        self.assertTrue(outcome['timeout'])
        self.assertFalse(outcome['passed'])

    def test_timeout(self):
        (self.root/'tests'/'test_calc.py').write_text('import unittest,time\nclass Test(unittest.TestCase):\n def test_hang(self): time.sleep(0.3)\n')
        # time-bound baseline with an internal zero baseline failure prevention
        result=self.run_worker([self.fixed]);self.assertEqual(result['error'],'baseline_does_not_reproduce')

if __name__=='__main__':unittest.main()
