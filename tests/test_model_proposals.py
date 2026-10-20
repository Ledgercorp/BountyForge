import io
import json
import unittest
from unittest.mock import patch
from bountyforge.model import LocalModel, ensure_loopback

class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

class ModelProposalTests(unittest.TestCase):
    def test_complete_uses_loopback_and_no_proxy(self):
        fake=FakeResponse(json.dumps({'choices':[{'message':{'content':'{"files":[]}'}}]}).encode())
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value=fake
            answer=LocalModel().complete('system','user',max_tokens=1500)
            req=build.return_value.open.call_args.args[0]
            payload=json.loads(req.data)
            self.assertEqual(req.full_url,'http://127.0.0.1:8080/v1/chat/completions')
            self.assertEqual(payload['max_tokens'],1500)
            self.assertEqual(build.call_args.args[0].proxies,{})
            self.assertEqual(payload['model'],'local')
        self.assertEqual(answer,'{"files":[]}')

    def test_remote_endpoints_rejected(self):
        for url in ('https://api.openai.com/v1/chat/completions','http://localhost:8080/v1/chat/completions','http://127.0.0.1:8081/v1/chat/completions'):
            with self.assertRaises(ValueError): LocalModel(url)

    def test_budget_limit(self):
        model=LocalModel()
        with self.assertRaises(ValueError): model.complete('s','x'*17000)
        with self.assertRaises(ValueError): model.complete('s','x',max_tokens=1501)

if __name__=='__main__': unittest.main()
