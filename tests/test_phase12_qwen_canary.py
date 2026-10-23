import importlib
import importlib.util
from pathlib import Path
import unittest

class QwenCanaryTests(unittest.TestCase):
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
