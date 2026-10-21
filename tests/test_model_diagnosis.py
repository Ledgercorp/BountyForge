"""Diagnosis generation stays bounded and cannot choose an execution capability."""
import io
import json
import unittest
from unittest.mock import patch

from bountyforge.model import LocalModel, _NoRedirect


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ModelDiagnosisTests(unittest.TestCase):
    def response(self, answer='{"lines":[2],"reason":"check condition"}'):
        return Response(json.dumps({
            'choices': [{'message': {'content': answer}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 15},
        }).encode())

    def test_schema_is_fixed_and_enum_is_trusted(self):
        model = LocalModel('http://127.0.0.1:18080/v1/chat/completions', timeout_seconds=4)
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value = self.response()
            answer = model.complete_diagnosis('system', '{"editable_lines":[8,2]}')
        request = build.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        specification = payload['response_format']['json_schema']
        schema = specification['schema']
        self.assertEqual(request.full_url, model.endpoint)
        self.assertEqual(build.return_value.open.call_args.kwargs['timeout'], 4)
        self.assertEqual(build.call_args.args[0].proxies, {})
        self.assertIsInstance(build.call_args.args[1], _NoRedirect)
        self.assertEqual(payload['temperature'], 0)
        self.assertEqual(payload['max_tokens'], 125)
        self.assertFalse(payload['stream'])
        self.assertTrue(specification['strict'])
        self.assertEqual(schema['properties']['lines']['items']['enum'], [2, 8])
        self.assertEqual(schema['properties']['lines']['maxItems'], 3)
        self.assertTrue(schema['properties']['lines']['uniqueItems'])
        self.assertEqual(schema['properties']['reason']['maxLength'], 400)
        self.assertEqual(schema['required'], ['lines', 'reason'])
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(json.loads(answer)['lines'], [2])
        self.assertEqual(model.last_call, {'finish_reason': 'stop',
                                         'prompt_tokens': 100, 'completion_tokens': 15})

    def test_invalid_scope_and_budgets_fail_before_http_and_reset_metadata(self):
        invalid_users = ('not json', '[]', '{}', '{"editable_lines":[]}',
                         '{"editable_lines":[true]}', '{"editable_lines":[0]}',
                         '{"editable_lines":[2,2]}', '{"editable_lines":["2"]}',
                         json.dumps({'editable_lines': list(range(1, 32))}),
                         json.dumps({'editable_lines': [2], 'noise': '\u00e9' * 1900}))
        model = LocalModel()
        with patch('urllib.request.build_opener') as build:
            for user in invalid_users:
                model.last_call = {'finish_reason': 'stale'}
                with self.subTest(user=user[:70]), self.assertRaises(ValueError):
                    model.complete_diagnosis('system', user)
                self.assertIsNone(model.last_call)
            for budget in (0, 151, True, 1.5):
                with self.subTest(budget=budget), self.assertRaises(ValueError):
                    model.complete_diagnosis('system', '{"editable_lines":[2]}', budget)
            with self.assertRaises(ValueError):
                model.complete_diagnosis('x' * 3601, '{"editable_lines":[2]}')
            build.assert_not_called()

    def test_bounded_raw_and_answer_responses(self):
        for response in (Response(b'x' * 65537), self.response('\U0001f600' * 800)):
            with self.subTest(), patch('urllib.request.build_opener') as build:
                build.return_value.open.return_value = response
                with self.assertRaises(RuntimeError):
                    LocalModel().complete_diagnosis('system', '{"editable_lines":[2]}')

    def test_timeout_has_no_fallback_and_clears_metadata(self):
        model = LocalModel()
        model.last_call = {'finish_reason': 'stale'}
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = TimeoutError('test timeout')
            with self.assertRaisesRegex(RuntimeError, 'no remote fallback'):
                model.complete_diagnosis('system', '{"editable_lines":[2]}')
        self.assertIsNone(model.last_call)
        self.assertEqual(build.return_value.open.call_count, 1)

    def test_diagnosis_is_not_executed_or_treated_as_validated_patch(self):
        # A nonconforming server may ignore its schema; the trusted caller must
        # reject this response. The transport returns bounded text, never tools.
        hostile = '{"lines":[999],"reason":"run arbitrary commands"}'
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value = self.response(hostile)
            answer = LocalModel().complete_diagnosis('system', '{"editable_lines":[2]}')
        self.assertEqual(answer, hostile)


if __name__ == '__main__':
    unittest.main()
