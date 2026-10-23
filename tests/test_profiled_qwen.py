import unittest
from unittest.mock import patch
from bountyforge.native_qwen import NativeStatementModel
from bountyforge.profiled_qwen import ProfiledStatementModel,ProfiledInferenceError


class ProfiledContextTests(unittest.TestCase):
    def test_tokenizer_checks_full_model_template_before_completion(self):
        model=ProfiledStatementModel()
        with patch.object(NativeStatementModel,'_post_native',side_effect=[{'prompt':'rendered'},
                {'tokens':[4]*100},{'content':'{}','tokens_evaluated':100,'tokens_predicted':2}]) as post:
            model._complete_bounded_schema('s','u',150,{},'probe')
        self.assertEqual([c.args[0] for c in post.call_args_list],['/apply-template','/tokenize','/completion'])
        self.assertEqual(model.last_call['completion_requests'],1)
        self.assertEqual(model.last_call['tokenized_prompt_tokens'],100)

    def test_context_overflow_and_invalid_tokenizer_stop_before_inference(self):
        for response in [{'tokens':[4]*1900},{'tokens':['bad']},[]]:
            with self.subTest(response_size=len(str(response))),patch.object(NativeStatementModel,'_post_native',
                    side_effect=[{'prompt':'rendered'},response]) as post:
                model=ProfiledStatementModel()
                with self.assertRaises(ProfiledInferenceError):model._complete_bounded_schema('s','u',150,{},'probe')
                self.assertEqual(post.call_count,2);self.assertEqual(model.last_call['completion_requests'],0)

    def test_transport_outage_is_sanitized_and_has_a_specific_stage(self):
        with patch.object(NativeStatementModel,'_post_native',side_effect=RuntimeError('sensitive host detail')):
            model=ProfiledStatementModel()
            with self.assertRaisesRegex(ProfiledInferenceError,'LOCAL_APPLY_TEMPLATE_UNAVAILABLE'):
                model._complete_bounded_schema('s','u',150,{},'probe')
            self.assertEqual(model.last_call['completion_requests'],0)

    def test_narrow_model_profile_refuses_over_700_tokens_before_completion(self):
        with patch.object(NativeStatementModel,'_post_native',side_effect=[{'prompt':'rendered'},{'tokens':[4]*701}]) as post:
            model=ProfiledStatementModel(prompt_token_limit=700)
            with self.assertRaisesRegex(ProfiledInferenceError,'CONTEXT_LIMIT_EXCEEDED'):
                model._complete_bounded_schema('s','u',150,{},'probe')
            self.assertEqual(post.call_count,2);self.assertEqual(model.last_call['completion_requests'],0)
