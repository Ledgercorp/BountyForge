"""Admission tests only; model responses in the published experiment are real."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch


class ExternalModelAdmissionTests(unittest.TestCase):
    def test_inference_is_disabled_without_explicit_experiment_admission(self):
        from phase19_qwen_handoff import run
        with patch('bountyforge.local_model_runtime.LocalRuntime') as runtime:
            with self.assertRaisesRegex(ValueError,'EXPLICIT_OWNED_MODEL_EXPERIMENT_REQUIRED'):run(False)
            runtime.assert_not_called()

    def test_frozen_experiment_cannot_raise_budget_or_select_another_task(self):
        from phase19_qwen_handoff import validate_experiment,EXPERIMENT
        raw=EXPERIMENT.read_bytes();self.assertEqual(validate_experiment(raw)['maximum_requests'],2)
        for key,value in [('maximum_requests',3),('case_id','arbitrary-customer-job'),('model_profile','GROQ')]:
            record=json.loads(raw);record[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'FROZEN_EXPERIMENT_CHANGED'):
                validate_experiment(json.dumps(record).encode())

    def test_sdk_config_only_or_tampered_receipt_cannot_admit_inference(self):
        from phase19_qwen_handoff import validate_sdk_receipt,SDK_RECEIPT
        from bountyforge.repair_engines import receipt_hash
        record=json.loads(SDK_RECEIPT.read_text());validate_sdk_receipt(record)
        for key,value in [('initialize_confirmed',False),('model_requests',1),('runtime_audit',{}),('container_absent_after_cleanup',False)]:
            changed=copy.deepcopy(record);changed[key]=value;changed['receipt_sha256']=receipt_hash(changed)
            with self.subTest(key=key),self.assertRaisesRegex((ValueError,RuntimeError),'SDK_'):
                validate_sdk_receipt(changed)
        record['status']='BLOCKED'
        with self.assertRaisesRegex(ValueError,'SDK_RECEIPT_HASH'):validate_sdk_receipt(record)

    def test_capacity_rejects_unsupported_cpu_memory_or_disk(self):
        from phase19_qwen_handoff import validate_capacity
        validate_capacity(2,4*1024**2,2*1024**3)
        for args in [(1,4*1024**2,2*1024**3),(2,1024,2*1024**3),(2,4*1024**2,1024)]:
            with self.subTest(args=args),self.assertRaisesRegex(ValueError,'LOCAL_CAPACITY_UNAVAILABLE'):
                validate_capacity(*args)
