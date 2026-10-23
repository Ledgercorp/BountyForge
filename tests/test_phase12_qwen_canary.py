import importlib
import importlib.util
import json
from pathlib import Path
import unittest

class QwenCanaryTests(unittest.TestCase):
    def test_actual_local_model_artifact_has_shared_receipt_and_truthful_zero_success(self):
        from scripts.phase12_qwen_canary import validate_result
        from bountyforge.repair_engines import receipt_hash
        path=Path(__file__).resolve().parents[1]/'evidence/phase12/qwen_canary_39943137925.json'
        data=json.loads(path.read_bytes());validate_result(data['result'])
        self.assertEqual(data['model_calls'],2)
        self.assertEqual(data['verified_repairs'],0)
        self.assertEqual(data['result']['outcome'],'REPEATED_PROPOSAL')
        receipt=data['result']['verification_receipt']
        self.assertEqual(receipt['receipt_sha256'],receipt_hash(receipt))
        self.assertFalse(receipt['independently_verified'])
    def test_canary_budget_admission_and_actual_usage_are_required(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.phase12_qwen_canary'))
        api=importlib.import_module('scripts.phase12_qwen_canary')
        for bad in ({},{'engine':'CODEX_AGENT','model_calls':1},{'engine':'QWEN_LOCAL','model_calls':0},
                    {'engine':'QWEN_LOCAL','model_calls':3}):
            with self.assertRaises(ValueError):api.validate_result(bad)

    def test_hosted_canary_is_single_owned_task_local_only_and_explicitly_gated(self):
        path=Path(__file__).resolve().parents[1]/'.github/workflows/phase12-engine-canary.yml'
        self.assertTrue(path.is_file(),'The bounded free-runner engine canary is missing')
        s=path.read_text()
        for text in ['runs-on: ubuntu-24.04','persist-credentials: false','contents: read',
                     'bountyforge-repair-worker','[phase12-qwen-canary]','retention-days: 1',
                     'actions/cache/restore@','scripts.phase12_qwen_canary']:
            self.assertIn(text,s)
        for text in ['schedule:','secrets.','actions/cache/save','pull_request:']:
            self.assertNotIn(text,s)

if __name__=='__main__':unittest.main()
