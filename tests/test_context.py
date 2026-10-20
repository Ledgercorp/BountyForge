import unittest
from bountyforge.context import select_python_context
from bountyforge.drafts import DraftRejected

class ContextTests(unittest.TestCase):
    def test_remove_docstring_preserve_function(self):
        source=('import os\nCONST = 2\ndef add(a,b):\n    """Long function description."""\n    return a + b + CONST\n'
                'def irrelevant():\n    return 999\n')
        got=select_python_context(source,['add'])
        self.assertIn('def add(a,b):',got)
        self.assertIn('return a + b + CONST',got)
        self.assertIn('CONST = 2',got)
        self.assertNotIn('Long function',got)
        self.assertNotIn('def irrelevant',got)
    def test_dependency_expansion_without_evaluation(self):
        source='A=4\nB=A+2\nC=B+3\ndef f():\n    return C\n'
        got=select_python_context(source,['f'])
        self.assertIn('A=4',got)
        self.assertIn('B=A+2',got)
        self.assertIn('C=B+3',got)

    def test_duplicate_symbol_rejected(self):
        with self.assertRaises(DraftRejected): select_python_context('def a(): pass\ndef a(): pass', ['a'])
    def test_invalid_symbol_rejected(self):
        with self.assertRaises(DraftRejected): select_python_context('def a(): pass',['../etc/passwd'])
    def test_missing_target_rejected(self):
        with self.assertRaises(DraftRejected): select_python_context('def a(): pass',['b'])
    def test_budget_gate(self):
        source='def a():\n    return "'+('x'*3500)+'"\n'
        with self.assertRaises(DraftRejected): select_python_context(source,['a'])
    def test_does_not_execute_code(self):
        source='import os\nos.system("echo impossible")\ndef target(): return 4\n'
        got=select_python_context(source,['target'])
        self.assertNotIn('os.system',got)
        self.assertIn('def target():',got)
if __name__=='__main__': unittest.main()