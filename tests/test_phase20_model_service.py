import json
import unittest


class ModelGatewayTests(unittest.TestCase):
    def request(self,**extra):
        return json.dumps({'model':'bountyforge-qwen-1.5b','messages':[{'role':'user','content':'owned defect'}],
                           'stream':True,'max_tokens':150,**extra}).encode()

    def test_gateway_rejects_remote_models_tools_and_excessive_generation(self):
        from phase20_model_service import admit_request
        for extra in ({'model':'paid-provider'},{'tools':[{'type':'function'}]},{'max_tokens':151},
                      {'messages':[{'role':'user','content':[{'type':'image_url','image_url':{'url':'https://private'}}]}]}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                admit_request('/v1/chat/completions',self.request(**extra))
        for path in ('/completion','https://example.com/v1/chat/completions','/v1/files'):
            with self.assertRaises(ValueError):admit_request(path,self.request())

    def test_gateway_preserves_streaming_content_and_binds_model_and_temperature(self):
        from phase20_model_service import admit_request
        request=admit_request('/v1/chat/completions',self.request(temperature=1.2))
        self.assertEqual(request['model'],'bountyforge-qwen-1.5b')
        self.assertEqual(request['messages'],[{'role':'user','content':'owned defect'}])
        self.assertIs(request['stream'],True);self.assertEqual(request['temperature'],0)

    def test_duplicate_keys_and_oversized_payloads_fail_closed(self):
        from phase20_model_service import admit_request
        for raw in (b'{"model":"one","model":"two"}',b'x'*12289):
            with self.assertRaises(ValueError):admit_request('/v1/chat/completions',raw)

    def test_budget_refuses_third_request_and_cannot_be_reset_by_model(self):
        from phase20_model_service import RequestBudget
        budget=RequestBudget(2);budget.reserve();budget.reserve()
        with self.assertRaisesRegex(ValueError,'REQUEST_BUDGET'):budget.reserve()
        self.assertEqual(budget.dispatched,2)
