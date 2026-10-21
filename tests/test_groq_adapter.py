"""Mocked Groq transport checks; no live API calls or billable actions."""
import io
import json
import os
import unittest
from unittest.mock import patch
from bountyforge.groq_adapter import HostedGroqModel


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class HostedGroqTests(unittest.TestCase):
    def test_no_secret_or_explicit_free_plan_gates(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'not enabled'):
                HostedGroqModel()
        with patch.dict(os.environ, {'GROQ_API_KEY': 'secret'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'not enabled'):
                HostedGroqModel()

    def test_fixed_model_origin_strict_schema_and_no_tools(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'sk_test_0123456789',
                                     'BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED': '1'}, clear=True):
            model = HostedGroqModel()
            returned = {'choices': [{'message': {'content': '{"changes":[{"line":2,"new":"return 2"}]}'},
                                     'finish_reason': 'stop'}],
                        'usage': {'prompt_tokens': 33, 'completion_tokens': 12}}
            with patch('urllib.request.build_opener') as build:
                build.return_value.open.return_value = Response(json.dumps(returned).encode())
                out = model.complete_line('system', '{"editable_lines":[2,3]}', max_tokens=100)
            request = build.return_value.open.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(request.get_method(), 'POST')
            self.assertEqual(request.full_url, 'https://api.groq.com/openai/v1/chat/completions')
            self.assertEqual(request.get_header('Authorization'), 'Bearer sk_test_0123456789')
            self.assertEqual(payload['model'], 'openai/gpt-oss-120b')
            self.assertTrue(payload['response_format']['json_schema']['strict'])
            self.assertEqual(payload['response_format']['json_schema']['schema']
                             ['properties']['changes']['items']['properties']['line']['enum'], [2, 3])
            self.assertFalse(payload.get('tools'))
            self.assertEqual(out, returned['choices'][0]['message']['content'])
            self.assertEqual(model.last_call['completion_tokens'], 12)

    def test_no_key_or_prompt_in_exception(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'top-secret-123',
                                     'BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED': '1'}, clear=True):
            model = HostedGroqModel()
            with patch('urllib.request.build_opener') as build:
                build.return_value.open.side_effect = RuntimeError('top-secret-123 bad-request')
                with self.assertRaisesRegex(RuntimeError, 'Hosted inference unavailable') as ctx:
                    model.complete_line('secret prompt', '{"editable_lines":[1]}')
                self.assertNotIn('top-secret-123', str(ctx.exception))

    def test_timeout_rate_limit_is_terminal_no_retry(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'secure-key',
                                     'BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED': '1'}, clear=True):
            model = HostedGroqModel()
            with patch('urllib.request.build_opener') as build:
                build.return_value.open.side_effect = TimeoutError('offline')
                with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                    model.complete_line('system', '{"editable_lines":[1]}')
                self.assertEqual(build.return_value.open.call_count, 1)
                self.assertIsNone(model.last_call)

    def test_invalid_scope_and_budget_never_call_http(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'secure-key',
                                     'BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED': '1'}, clear=True):
            model = HostedGroqModel()
            with patch('urllib.request.build_opener') as build:
                for value in ('oops', '{}', '{"editable_lines":[1,1]}',
                              '{"editable_lines":[true]}', '{"editable_lines":[]}'):
                    with self.subTest(value=value), self.assertRaises(ValueError):
                        model.complete_line('sys', value)
                with self.assertRaises(ValueError):
                    model.complete_line('sys', '{"editable_lines":[1]}', max_tokens=151)
                build.assert_not_called()

    def test_diagnosis_requires_trusted_lines(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'secure-key',
                                     'BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED': '1'}, clear=True):
            model = HostedGroqModel()
            with patch('urllib.request.build_opener') as build:
                response = {'choices': [{'message': {'content': '{"lines":[1],"reason":"bad condition"}'},
                                         'finish_reason': 'stop'}]}
                build.return_value.open.return_value = Response(json.dumps(response).encode())
                self.assertIn('lines', model.complete_diagnosis('sys', '{"editable_lines":[1,2]}'))
                payload = json.loads(build.return_value.open.call_args.args[0].data)
                self.assertEqual(payload['response_format']['json_schema']['schema']
                                 ['properties']['lines']['items']['enum'], [1, 2])

    def test_eight_call_ceiling_is_enforced_without_extra_http(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'secure-key',
                                     'BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED': '1'}, clear=True):
            model = HostedGroqModel()
            response = {'choices': [{'message': {'content': '{"changes":[{"line":1,"new":"return 1"}]}'},
                                     'finish_reason': 'stop'}]}
            with patch('urllib.request.build_opener') as build:
                for _ in range(8):
                    build.return_value.open.return_value = Response(json.dumps(response).encode())
                    model.complete_line('system', '{"editable_lines":[1]}')
                with self.assertRaisesRegex(RuntimeError, 'budget exhausted'):
                    model.complete_line('system', '{"editable_lines":[1]}')
                self.assertEqual(build.return_value.open.call_count, 8)

    def test_oversized_response_rejected_without_dumping_content(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'secure-key',
                                     'BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED': '1'}, clear=True):
            model = HostedGroqModel()
            with patch('urllib.request.build_opener') as build:
                build.return_value.open.return_value = Response(b'x' * 65537)
                with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                    model.complete_line('sys', '{"editable_lines":[1]}')


if __name__ == '__main__':
    unittest.main()
