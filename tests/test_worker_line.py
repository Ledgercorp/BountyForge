import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.worker import repair_fixture
from bountyforge.drafts import DraftRejected

class LineModel:
    def __init__(self, responses):
        self.responses=list(responses)
        self.calls=0
    def complete_line(self, system, prompt, max_tokens):
        self.calls+=1
        return self.responses.pop(0)

class LineWorkerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'.bountyforge-controlled-fixture').write_text('synthetic')
        (self.root/'calc.py').write_text('def add(a,b):\n    return a-b\n')
        (self.root/'tests').mkdir()
        (self.root/'tests'/'test_calc.py').write_text('import unittest\nfrom calc import add\nclass T(unittest.TestCase):\n def test_add(self): self.assertEqual(add(2,3),5)\n')
        self.issue={'verification':'unverified_candidate','description_excerpt':'sum operands'}
    def test_line_repair_passes_without_mutating_source(self):
        m=LineModel([json.dumps({'changes':[{'line':2,'new':'return a+b'}]})])
        r=repair_fixture(self.issue,self.root,['calc.py'],m,strategy='line',editable_lines={'calc.py':[2]})
        self.assertEqual(r['status'],'review_ready')
        self.assertEqual(r['model_calls'],1)
        self.assertFalse(r['submitted'])
        self.assertEqual((self.root/'calc.py').read_text(),'def add(a,b):\n    return a-b\n')
    def test_line_strategy_requires_explicit_scope(self):
        with self.assertRaises(DraftRejected):
            repair_fixture(self.issue,self.root,['calc.py'],LineModel([]),strategy='line')
    def test_rejects_unapproved_line(self):
        m=LineModel([json.dumps({'changes':[{'line':1,'new':'def add(a,b): pass'}]})]*2)
        r=repair_fixture(self.issue,self.root,['calc.py'],m,strategy='line',editable_lines={'calc.py':[2]})
        self.assertEqual(r['status'],'failed')
        self.assertIsNone(r['patch'])
    def test_rejects_invalid_source(self):
        m=LineModel([json.dumps({'changes':[{'line':2,'new':'return ('}]})]*2)
        r=repair_fixture(self.issue,self.root,['calc.py'],m,strategy='line',editable_lines={'calc.py':[2]})
        self.assertEqual(r['status'],'failed')

if __name__=='__main__': unittest.main()
