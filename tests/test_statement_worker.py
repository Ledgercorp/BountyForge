import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.worker import repair_fixture


class StatementWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'.bountyforge-controlled-fixture').write_text('owned-neutral')
        (self.root/'subject.py').write_text('def cost(x):\n    amount = (\n        x * 2\n    )\n    return amount\n')
        (self.root/'tests').mkdir()
        (self.root/'tests/test_cost.py').write_text('import unittest\nfrom subject import cost\nclass T(unittest.TestCase):\n def test_cost(self): self.assertEqual(cost(2),6)\n')
        self.issue = {'verification':'unverified_candidate','target_symbol':'cost',
                      'description_excerpt':'Return triple the amount.'}

    def run_worker(self, responses, runner=None):
        class Model:
            calls = 0
            def complete_line(self, system, prompt, max_tokens):
                self.calls += 1
                return responses[self.calls-1]
        try:
            return repair_fixture(self.issue, self.root, ['subject.py'], Model(), strategy='statement',
                                  editable_lines={'subject.py':[2,5]}, test_runner=runner)
        except ValueError as exc:
            self.fail('Statement worker integration rejected the supported strategy: '+str(exc))

    def test_multiline_repair_gets_fresh_independent_verification_and_transcript(self):
        report = self.run_worker(['{"changes":[{"line":2,"new":"amount = x * 3"}]}'])
        self.assertEqual(report['status'], 'review_ready')
        self.assertEqual(report['model_calls'], 1)
        self.assertTrue(report['independent_verification']['passed'])
        self.assertEqual(len(report['attempts'][0]['calls']), 1)
        self.assertIn('x * 2', (self.root/'subject.py').read_text())

    def test_semantic_duplicate_is_not_executed_again(self):
        executed = []
        def runner(root):
            executed.append(root)
            return {'passed':False,'exit_code':1,'timeout':False,
                    'output':'FAIL: test_cost (T.test_cost)\nAssertionError: wrong\nFAILED (failures=1)'}
        report = self.run_worker(['{"changes":[{"line":2,"new":"amount = x * 4"}]}',
                                  '{"changes":[{"line":2,"new":"amount = (x * 4)"}]}'], runner)
        self.assertEqual(report['model_calls'], 2)
        self.assertEqual(len(executed), 2)  # Baseline and first wrong candidate.
        self.assertEqual(report['attempts'][-1]['error'], 'repeated_ineffective_candidate')
        self.assertEqual(report['status'], 'failed')

    def test_independent_regression_failure_never_becomes_ready(self):
        results = iter([{'passed':False,'exit_code':1,'timeout':False,
                         'output':'FAIL: test_cost (T.test_cost)\nFAILED (failures=1)'},
                        {'passed':True,'exit_code':0,'timeout':False,'output':'Ran 1 test\nOK'},
                        {'passed':False,'exit_code':1,'timeout':False,'output':'AssertionError: independent'}])
        report = self.run_worker(['{"changes":[{"line":2,"new":"amount = x * 3"}]}'], lambda root: next(results))
        self.assertEqual(report['status'], 'failed')
        self.assertIsNone(report['patch'])
        self.assertEqual(report['error'], 'independent_verification_failed')


if __name__ == '__main__': unittest.main()
