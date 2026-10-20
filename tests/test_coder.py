import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.coder import propose_draft
from bountyforge.drafts import DraftRejected

class FakeModel:
    def __init__(self, output):
        self.output=output
        self.called=False
    def complete(self,system,user,max_tokens):
        self.called=True
        assert 'untrusted' in system.lower()
        assert 'approved.py' in user
        assert max_tokens<=1500
        return self.output

class CoderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace=Path(self.tmp.name)
        (self.workspace/'approved.py').write_text('def add(a,b):\n    return a-b\n')
        self.issue={'url':'https://github.com/example/repo/issues/7','title':'Fix addition','description_excerpt':'Add two integers.','verification':'unverified_candidate'}

    def test_draft_staged_without_workspace_mutation(self):
        model=FakeModel(json.dumps({'files':[{'path':'approved.py','content':'def add(a,b):\n    return a+b\n'}]}))
        outcome=propose_draft(self.issue,self.workspace,['approved.py'],model)
        self.assertTrue(model.called)
        self.assertFalse(outcome['execution_performed'])
        self.assertEqual(outcome['model'],'local-only')
        self.assertEqual((self.workspace/'approved.py').read_text(),'def add(a,b):\n    return a-b\n')
        self.assertIn('+    return a+b',outcome['files'][0]['diff'])

    def test_declines_unverified_schema_failure(self):
        model=FakeModel('do not run tests')
        with self.assertRaises(DraftRejected):
            propose_draft(self.issue,self.workspace,['approved.py'],model)

    def test_never_reads_an_unapproved_file(self):
        model=FakeModel('')
        with self.assertRaises(DraftRejected):
            propose_draft(self.issue,self.workspace,['secret.env'],model)
        self.assertFalse(model.called)

    def test_rejects_large_source_before_model_call(self):
        (self.workspace/'approved.py').write_text('x'*4010)
        model=FakeModel('')
        with self.assertRaises(DraftRejected):
            propose_draft(self.issue,self.workspace,['approved.py'],model)
        self.assertFalse(model.called)

    def test_disallows_unknown_issue_state(self):
        model=FakeModel('')
        issue={**self.issue,'verification':'funded_verified'}
        with self.assertRaises(DraftRejected):
            propose_draft(issue,self.workspace,['approved.py'],model)

if __name__=='__main__': unittest.main()
