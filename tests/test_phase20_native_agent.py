import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch


class NativeAgentEvidenceTests(unittest.TestCase):
    def test_owner_task_selection_never_silently_runs_a_different_frozen_case(self):
        from phase20_native_agent import select_experiment
        with self.assertRaisesRegex(ValueError,'TASK_SELECTION'):select_experiment('supplemental','optional-setting')
        with self.assertRaisesRegex(ValueError,'TASK_SELECTION'):select_experiment('sdk-case',None)
        self.assertEqual(select_experiment('supplemental',None)[2]['case_id'],'chunk-count')

    def test_crashed_or_completed_arm_cannot_claim_its_inference_budget_again(self):
        from phase20_native_agent import claim_arm
        with tempfile.TemporaryDirectory() as temp,patch('phase20_native_agent.HISTORY_ROOT',Path(temp)/'empty-history'):
            p=Path(temp)/'claims'
            self.assertEqual(claim_arm('optional-setting','NATIVE_SDK',root=p),1)
            with self.assertRaisesRegex(ValueError,'ARM_ALREADY_RESERVED'):
                claim_arm('optional-setting','NATIVE_SDK',root=p)
            self.assertEqual(claim_arm('optional-setting','EXTERNAL_CONTROL',root=p),1)

    def test_completed_two_request_demo_never_gets_a_new_budget(self):
        from phase20_native_agent import claim_arm
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'ARM_ALREADY_COMPLETED'):
                claim_arm('weighted-mix','NATIVE_SDK',root=Path(temp)/'claims')

    def test_supplement_is_explicit_and_cannot_allocate_an_external_or_third_attempt(self):
        from phase20_native_agent import claim_arm
        with tempfile.TemporaryDirectory() as temp,patch('phase20_native_agent.HISTORY_ROOT',Path(temp)/'empty-history'):
            root=Path(temp)/'claims'
            self.assertEqual(claim_arm('chunk-count','NATIVE_SDK',root=root),2)
            with self.assertRaisesRegex(ValueError,'ARM_ALREADY_RESERVED'):claim_arm('chunk-count','NATIVE_SDK',root=root)
            with self.assertRaisesRegex(ValueError,'FROZEN_ARM_NOT_SELECTED'):claim_arm('chunk-count','EXTERNAL_CONTROL',root=root)

    def test_recorded_result_blocks_new_inference_even_with_a_fresh_private_store(self):
        from phase20_native_agent import claim_arm
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'new-claims'
            with self.assertRaisesRegex(ValueError,'ARM_ALREADY_COMPLETED'):
                claim_arm('optional-setting','NATIVE_SDK',root=root)
            self.assertFalse(root.exists())

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
