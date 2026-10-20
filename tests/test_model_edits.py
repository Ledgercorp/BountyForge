import io,json,unittest
from unittest.mock import patch
from bountyforge.model import LocalModel
class Reply(io.BytesIO):
 def __enter__(self):return self
 def __exit__(self,*exc):self.close()
class EditModelTests(unittest.TestCase):
 def test_schema_and_endpoint(self):
  content='{"edits":[{"path":"x.py","old":"foo","new":"bar"}]}'
  response=Reply(json.dumps({'choices':[{'message':{'content':content}}]}).encode())
  with patch('urllib.request.build_opener') as build:
   build.return_value.open.return_value=response
   got=LocalModel('http://127.0.0.1:18080/v1/chat/completions').complete_edit('system','prompt',max_tokens=170)
   req=build.return_value.open.call_args.args[0]
   spec=json.loads(req.data)
   self.assertEqual(spec['response_format']['json_schema']['schema']['required'],['edits'])
   self.assertEqual(build.call_args.args[0].proxies,{})
   self.assertEqual(req.full_url,'http://127.0.0.1:18080/v1/chat/completions')
  self.assertEqual(got,content)
 def test_edit_budget(self):
  with self.assertRaises(ValueError):LocalModel().complete_edit('s','x'*10000)
  with self.assertRaises(ValueError):LocalModel().complete_edit('s','x',max_tokens=1000)
if __name__=='__main__':unittest.main()