import json,tempfile,unittest
from pathlib import Path
from bountyforge.minimal import stage_edits,propose_minimal
from bountyforge.drafts import DraftRejected
class Scripted:
 def __init__(self,ans): self.ans=ans;self.calls=0;self.text=''
 def complete_edit(self,sys,user,max_tokens): self.calls+=1;self.text=user;return self.ans
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);(self.root/'x.py').write_text('def add(a,b):\n    return a-b\n')
  self.old='    return a-b';self.new='    return a+b'
 def e(self,**kw): return json.dumps({'edits':[{'path':'x.py','old':self.old,'new':self.new,**kw}]})
 def test_minimal_does_not_write(self):
  r=stage_edits(self.e(),self.root,['x.py']);self.assertEqual(r['files'][0]['content'],'def add(a,b):\n    return a+b\n');self.assertEqual((self.root/'x.py').read_text(),'def add(a,b):\n    return a-b\n')
 def test_wrong_path(self):
  with self.assertRaises(DraftRejected):stage_edits(self.e(path='other.py'),self.root,['x.py'])
 def test_non_unique_old(self):
  with self.assertRaises(DraftRejected):stage_edits(self.e(old=' '),self.root,['x.py'])
 def test_invalid_syntax(self):
  with self.assertRaises(DraftRejected):stage_edits(self.e(new=' return (('),self.root,['x.py'])
 def test_extra_json_key(self):
  with self.assertRaises(DraftRejected):stage_edits(self.e().replace('{"edits":','{"command":"rm -rf .", "edits":'),self.root,['x.py'])
 def test_malformed(self):
  with self.assertRaises(DraftRejected):stage_edits('{invalid',self.root,['x.py'])
 def test_schema_wrong(self):
  with self.assertRaises(DraftRejected):stage_edits(json.dumps({'files':[]}),self.root,['x.py'])
 def test_model_receives_exact_path_and_failure(self):
  m=Scripted(self.e());r=propose_minimal({'verification':'unverified_candidate','description_excerpt':'add','test_failure_excerpt':'test_add failed'},self.root,['x.py'],m)
  self.assertTrue(r['review_required']);self.assertEqual(m.calls,1);self.assertIn('test_add failed',m.text)
 def test_model_never_called_if_missing_source(self):
  m=Scripted(self.e())
  with self.assertRaises(DraftRejected):propose_minimal({'verification':'unverified_candidate'},self.root,['no.py'],m)
  self.assertEqual(m.calls,0)
 def test_traversal(self):
  with self.assertRaises(DraftRejected):stage_edits(self.e(path='../x.py'),self.root,['x.py'])
if __name__=='__main__':unittest.main()