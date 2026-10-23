import unittest
from unittest.mock import patch
from bountyforge.native_qwen import NativeStatementModel


class NativeTransportTests(unittest.TestCase):
    def test_uses_model_template_and_native_schema_without_provider_fallback(self):
        model=NativeStatementModel()
        with patch.object(model,'_post_native',side_effect=[{'prompt':'model-rendered'},
              {'content':'{"ok":"locked"}','tokens_evaluated':12,'tokens_predicted':8,'stop_type':'eos'}]) as post:
            schema={'type':'object','properties':{'ok':{'const':'locked'}}}
            result=model._complete_bounded_schema('system','user',24,schema,'probe')
        self.assertEqual(result,'{"ok":"locked"}')
        self.assertEqual(post.call_args_list[0].args[0],'/apply-template')
        path,body=post.call_args_list[1].args
        self.assertEqual(path,'/completion');self.assertEqual(body['json_schema'],schema)
        self.assertEqual(body['prompt'],'model-rendered');self.assertNotIn('response_format',body)
        self.assertEqual(model.last_call['completion_tokens'],8)

    def test_missing_native_endpoint_or_invalid_template_fails_closed(self):
        model=NativeStatementModel()
        with patch.object(model,'_post_native',return_value={'prompt':None}) as post:
            with self.assertRaises(RuntimeError):model._complete_bounded_schema('s','u',24,{},'x')
        self.assertEqual(post.call_count,1)
        with self.assertRaises(ValueError):NativeStatementModel(endpoint='https://paid.example/v1/chat/completions')

    def test_non_object_native_responses_fail_closed(self):
        for replies in ([[]], [{'prompt':'rendered'}, []]):
            with self.subTest(replies=replies), patch.object(NativeStatementModel,'_post_native',side_effect=replies):
                with self.assertRaises(RuntimeError):
                    NativeStatementModel()._complete_bounded_schema('s','u',24,{},'x')
