import unittest


class NativeAgentEvidenceTests(unittest.TestCase):
    def test_absent_sdk_assistant_event_is_not_replaced_by_an_external_model_answer(self):
        from phase20_native_agent import assistant_response
        self.assertEqual(assistant_response([{'method':'session.status','params':{'status':'idle'}}]),'')
        event={'method':'session.event','params':{'event':{'type':'assistant/message',
            'data':{'message':{'content':[{'type':'text','text':'{"changes":[]}'},{'type':'tool_call','name':'bash'}]}}}}}
        with self.assertRaisesRegex(ValueError,'SDK_TOOL_RESPONSE'):assistant_response([event])
        event['params']['event']['data']['message']['content'].pop()
        self.assertEqual(assistant_response([event]),'{"changes":[]}')

    def test_configuration_only_audit_or_exposed_tools_cannot_admit_a_turn(self):
        from phase20_native_agent import validate_live_audit
        for record in ({},{'tool_names':['bash'],'refusals':[]},{'tool_names':[],'refusals':[]}):
            with self.assertRaisesRegex(ValueError,'LIVE_CAPABILITY'):validate_live_audit(record)

    def test_cli_without_admission_cannot_start_any_process(self):
        from phase20_native_agent import run_experiment
        with self.assertRaisesRegex(ValueError,'EXPLICIT_NATIVE_QWEN_ADMISSION'):run_experiment(False)
