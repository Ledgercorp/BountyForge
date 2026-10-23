"""Neutral development contracts, not held-out model accuracy."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.worker import _run_tests, FIXTURE_MARKER
from bountyforge.drafts import DraftRejected

class SessionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('bountyforge.repair_session'),
                             'Owned repair session is not implemented')
        from bountyforge.repair_session import repair_owned
        self.repair = repair_owned
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/FIXTURE_MARKER).write_text('owned-dev-only')
        (self.root/'subject.py').write_text('def scaled(value):\n    total = (\n        value * 2\n    )\n    return total\n')
        (self.root/'tests').mkdir()
        (self.root/'tests/test_regression.py').write_text('import unittest\nfrom subject import scaled\nFACTOR = 3\nclass Contract(unittest.TestCase):\n def test_scaled(self):\n  self.assertEqual(scaled(4), 4 * FACTOR)\n def test_zero(self):\n  self.assertEqual(scaled(0), 0)\n')
        self.pins={p:hashlib.sha256((self.root/p).read_bytes()).hexdigest()
                   for p in ('subject.py','tests/test_regression.py')}
        self.issue={'verification':'unverified_candidate','target_symbol':'scaled',
                    'description_excerpt':'Apply the stated scale while preserving zero.'}
    def run_session(self,responses,runner=_run_tests,**kw):
        class Model:
            calls=0; last_call=None
            prompts=[]
            def complete_line(self,system,prompt,max_tokens):
                self.prompts.append((system,json.loads(prompt)))
                response=responses[self.calls]; self.calls+=1
                return response
        self.model=Model()
        return self.repair(self.issue,self.root,'subject.py',self.model,
                           expected_hashes=self.pins,test_runner=runner,**kw)
    def test_correct_multiline_candidate_gets_cached_baseline_and_fresh_verification(self):
        runs=[]
        def runner(root): runs.append(root); return _run_tests(root)
        report=self.run_session(['{"changes":[{"line":2,"new":"total = value * 3"}]}'],runner)
        self.assertEqual(report['status'],'review_ready')
        self.assertEqual(len(runs),3) # Actual baseline, candidate, fresh independent copy.
        self.assertEqual(report['model_calls'],1)
        self.assertEqual(report['baseline_cache_reads'],1)
        self.assertIn('FACTOR = 3',self.model.prompts[0][1]['test_contract_untrusted'])
        self.assertEqual(report['calls'][0]['prompt'],json.dumps(self.model.prompts[0][1],ensure_ascii=True))
        self.assertFalse(report['customer_execution_authorized'])
        self.assertEqual((self.root/'subject.py').read_text().count('value * 2'),1)
    def test_retry_has_exact_rejection_metrics_and_actual_latest_test_failure(self):
        oversized=json.dumps({'changes':[{'line':2,'new':'total = value\ntotal += value\ntotal += value\nextra = 0'}]})
        report=self.run_session([oversized,'{"changes":[{"line":2,"new":"total = value * 3"}]}'])
        self.assertEqual(report['status'],'review_ready')
        second=self.model.prompts[1][1]
        self.assertEqual(second['previous_proposal_metrics']['physical_lines'],[4])
        self.assertIn('Unsafe replacement text',second['previous_error'])
        self.assertIn('test_scaled',second['failure_untrusted'])
        self.assertEqual(len(report['calls']),2)
    def test_regression_retry_gets_untruncated_new_failure_identity(self):
        report=self.run_session(['{"changes":[{"line":2,"new":"total = value * 4"}]}',
                                 '{"changes":[{"line":2,"new":"total = value * 3"}]}'])
        self.assertEqual(report['status'],'review_ready')
        self.assertIn('16 != 12',self.model.prompts[1][1]['failure_untrusted'])
        self.assertEqual(report['calls'][1]['previous_response_sha256'],
                         hashlib.sha256(report['calls'][0]['response'].encode()).hexdigest())
    def test_inconsistent_passing_receipt_fails_closed_before_model(self):
        result=self.run_session([],lambda root:{'passed':True,'exit_code':1,'timeout':False,'output':'Ran 2 tests\nOK'})
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['model_calls'],0)
        self.assertIsNone(result['patch'])
    def test_wrong_symbol_does_not_override_deterministic_localization(self):
        self.issue['target_symbol']='other'
        result=self.run_session([])
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['reason'],'scope_rejected')
        self.assertEqual(result['model_calls'],0)
    def test_changed_tests_and_extra_file_are_rejected_without_execution(self):
        (self.root/'extra.py').write_text('raise RuntimeError()')
        called=[]
        with self.assertRaises(DraftRejected):self.run_session([],lambda root:called.append(root))
        self.assertEqual(called,[])
        (self.root/'extra.py').unlink()
        (self.root/'tests/test_regression.py').write_text('raise RuntimeError()')
        with self.assertRaises(DraftRejected):self.run_session([],lambda root:called.append(root))
        self.assertEqual(called,[])
    def test_mutation_by_runner_and_no_runner_fail_closed(self):
        def runner(root):
            (root/'tests/test_regression.py').write_text('changed')
            return {'passed':False,'exit_code':1,'timeout':False,'output':'FAIL: test_scaled (Contract.test_scaled)\nRan 2 tests\nFAILED (failures=1)'}
        result=self.run_session([],runner)
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['model_calls'],0)
    def test_unavailable_model_stops_without_retry_and_no_ready_patch(self):
        class Unavailable:
            def complete_line(self,*args,**kw):raise RuntimeError('unavailable')
        result=self.repair(self.issue,self.root,'subject.py',Unavailable(),
                           expected_hashes=self.pins,test_runner=_run_tests)
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['model_calls'],1)
        self.assertIsNone(result['patch'])
    def test_new_augassign_cannot_read_deleted_binding_before_test_execution(self):
        runs=[]
        def runner(root): runs.append(root); return _run_tests(root)
        report=self.run_session(['{"changes":[{"line":2,"new":"total += value"}]}',
                                 '{"changes":[{"line":2,"new":"total = value * 3"}]}'],runner)
        self.assertEqual(report['status'],'review_ready')
        self.assertEqual(len(runs),3)
        self.assertIn('uninitialized augmented assignment',self.model.prompts[1][1]['previous_error'])
    def test_condition_walrus_binding_removal_is_rejected_without_execution(self):
        import bountyforge.repair_session as api
        guard=getattr(api,'validate_proposal_bindings',None)
        self.assertTrue(callable(guard),'Stricter proposal binding guard missing')
        source='def choose(value):\n    if (found := value):\n        return found\n    return 0\n'
        with self.assertRaisesRegex(DraftRejected,'condition binding'):
            guard(source,[2,3,4],'{"changes":[{"line":2,"new":"True"}]}')
    def test_class_and_transitive_test_fixtures_are_preserved(self):
        from bountyforge.repair_session import contract_units
        contract='ZERO = 0\nSAMPLES = [ZERO, 1]\nclass Contract(unittest.TestCase):\n EXPECTED = 3\n def test_scaled(self):\n  for value in SAMPLES:\n   self.assertEqual(scaled(value), value * self.EXPECTED)\n'
        snippets='\n'.join(code for _,code in contract_units(contract,'FAIL: test_scaled (Contract.test_scaled)'))
        self.assertIn('ZERO = 0',snippets)
        self.assertIn('SAMPLES = [ZERO, 1]',snippets)
        self.assertIn('EXPECTED = 3',snippets)
    def test_long_failure_tail_does_not_hide_exact_latest_assertion(self):
        def runner(root):
            check=_run_tests(root)
            if not check['passed']:check['output']+='\n'+'irrelevant bounded output\n'*45
            return check
        result=self.run_session(['{"changes":[{"line":2,"new":"total = value * 4"}]}',
                                 '{"changes":[{"line":2,"new":"total = value * 3"}]}'],runner)
        self.assertEqual(result['status'],'review_ready')
        self.assertIn('FAIL: test_scaled',self.model.prompts[1][1]['failure_untrusted'])
        self.assertIn('16 != 12',self.model.prompts[1][1]['failure_untrusted'])
    def test_provider_exception_types_stop_and_never_become_patch_failures(self):
        for error in (ValueError,TypeError,KeyError,AttributeError):
            class Provider:
                calls=0
                def complete_line(self,*args,**kw):
                    self.calls+=1;raise error('provider failure with private details')
            provider=Provider()
            with self.subTest(error=error.__name__):
                result=self.repair(self.issue,self.root,'subject.py',provider,
                                   expected_hashes=self.pins,test_runner=_run_tests)
                self.assertEqual(result['status'],'blocked')
                self.assertEqual(provider.calls,1)
                self.assertIsNone(result['patch'])
                self.assertNotIn('private details',json.dumps(result))
    def test_external_runner_exception_is_sanitized_and_blocked(self):
        def broken(root):raise KeyError('private runner path')
        result=self.run_session([],broken)
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['model_calls'],0)
        self.assertNotIn('private runner path',json.dumps(result))
    def test_unrepresentable_failing_contract_blocks_before_provider(self):
        test=self.root/'tests/test_regression.py'
        test.write_text('import unittest\nfrom subject import scaled\nclass Contract(unittest.TestCase):\n def test_scaled(self):\n  "'+('owned fixture description '*90)+'"\n  self.assertEqual(scaled(4),12)\n')
        self.pins['tests/test_regression.py']=hashlib.sha256(test.read_bytes()).hexdigest()
        result=self.run_session([])
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['model_calls'],0)
    def test_duplicate_method_names_fail_closed_in_contract_extraction(self):
        from bountyforge.repair_session import contract_units
        contract='class Good:\n def test_scaled(self):\n  self.assertEqual(scaled(0),0)\nclass Bad:\n def test_scaled(self):\n  self.assertEqual(scaled(4),12)\n'
        with self.assertRaisesRegex(DraftRejected,'Ambiguous'):
            contract_units(contract,'FAIL: test_scaled (test_regression.Bad.test_scaled)')
    def test_semantic_duplicate_does_not_repeat_test_execution(self):
        runs=[]
        def runner(root):runs.append(root);return _run_tests(root)
        result=self.run_session(['{"changes":[{"line":2,"new":"total = value * 4"}]}',
                                 '{"changes":[{"line":2,"new":"total = (value * 4)"}]}'],runner)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(len(runs),2)
        self.assertEqual(result['worker']['attempts'][1]['error'],'repeated_ineffective_candidate')

if __name__=='__main__':unittest.main()
