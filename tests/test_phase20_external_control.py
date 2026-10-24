import json
import unittest


class ExternalControlStreamTests(unittest.TestCase):
    def test_only_complete_text_stream_can_supply_a_candidate(self):
        from phase20_external_client import parse_stream
        text='data: '+json.dumps({'choices':[{'delta':{'content':'{"changes":[]}'}}]})+'\n\ndata: [DONE]\n\n'
        self.assertEqual(parse_stream(text.encode())['response'],'{"changes":[]}')
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_MODEL_STREAM'):parse_stream(text.split('data: [DONE]')[0].encode())
        tools=('data: '+json.dumps({'choices':[{'delta':{'tool_calls':[{'name':'bash'}]}}]})+'\n\ndata: [DONE]\n\n').encode()
        with self.assertRaisesRegex(ValueError,'TOOL_CALL'):parse_stream(tools)
