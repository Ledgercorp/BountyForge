import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.worker import repair_fixture
from bountyforge.line_scope import infer_editable_lines
from bountyforge.drafts import DraftRejected

class Model:
    def complete_line(self, system, prompt, max_tokens):
        return json.dumps({"changes":[{"line":2,"new":"return a+b"}]})

class AutoScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'.bountyforge-controlled-fixture').write_text('synthetic')
        (self.root/'calc.py').write_text('def add(a,b):\n    return a-b\n')
        (self.root/'tests').mkdir()
        (self.root/'tests'/'test_calc.py').write_text('import unittest\nfrom calc import add\nclass T(unittest.TestCase):\n def test_add(self): self.assertEqual(add(2,3),5)\n')
        self.issue={'verification':'unverified_candidate','description_excerpt':'addition bug'}
    def test_infer_scope(self):
        self.assertEqual(infer_editable_lines(self.root,'calc.py','FAIL: test_add (test_calc.T)'),[2])
    def test_multiple_failures_identify_same_source_function(self):
        (self.root/'tests'/'test_calc.py').write_text(
            'from calc import add\nimport unittest\n'
            'class T(unittest.TestCase):\n'
            ' def test_positive(self): self.assertEqual(add(2,3),5)\n'
            ' def test_negative(self): self.assertEqual(add(-2,3),1)\n')
        failures = ('FAIL: test_positive (test_calc.T.test_positive)\n'
                    'FAIL: test_negative (test_calc.T.test_negative)')
        self.assertEqual(infer_editable_lines(self.root,'calc.py',failures),[2])

    def test_multiple_failures_different_functions_rejected(self):
        (self.root/'calc.py').write_text(
            'def add(a,b):\n    return a-b\n'
            'def other(a,b):\n    return a-b\n')
        (self.root/'tests'/'test_calc.py').write_text(
            'from calc import add, other\nimport unittest\n'
            'class T(unittest.TestCase):\n'
            ' def test_positive(self): self.assertEqual(add(2,3),5)\n'
            ' def test_negative(self): self.assertEqual(other(-2,3),1)\n')
        with self.assertRaises(DraftRejected):
            infer_editable_lines(self.root,'calc.py',
                'FAIL: test_positive (test_calc.T.test_positive)\n'
                'FAIL: test_negative (test_calc.T.test_negative)')

    def test_missing_failing_test_definition_rejected(self):
        with self.assertRaises(DraftRejected):
            infer_editable_lines(self.root,'calc.py',
                'FAIL: test_add (test_calc.T.test_add)\n'
                'FAIL: test_missing (test_calc.T.test_missing)')

    def test_no_failure_rejected(self):
        with self.assertRaises(DraftRejected):
            infer_editable_lines(self.root,'calc.py','ERROR: import failed')
    def test_duplicate_source_function_rejected(self):
        (self.root/'calc.py').write_text('def add(a,b):\n    return a-b\ndef add(a,b):\n    return a-b\n')
        with self.assertRaises(DraftRejected):
            infer_editable_lines(self.root,'calc.py','FAIL: test_add (test_calc.T)')
    def test_end_to_end_controlled_auto_repair(self):
        r=repair_fixture(self.issue,self.root,['calc.py'],Model(),strategy='auto_line')
        self.assertEqual(r['status'],'review_ready')
        self.assertEqual(r['inferred_editable_lines'],[2])
        self.assertFalse(r['submitted'])
        self.assertIn('return a-b',(self.root/'calc.py').read_text())
    def test_ambiguous_source_fails_closed(self):
        (self.root/'calc.py').write_text('def other(a,b):\n    return a-b\n')
        r=repair_fixture(self.issue,self.root,['calc.py'],Model(),strategy='auto_line')
        self.assertEqual(r['error'],'automatic_scope_rejected')
        self.assertEqual(r['model_calls'],0)

if __name__=='__main__': unittest.main()
