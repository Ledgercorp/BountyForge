import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import phase13_qwen_contract_canary as canary


class CanaryAdmissionTests(unittest.TestCase):
    def test_real_qwen_receipts_meet_the_shared_queue_integrity_contract(self):
        from bountyforge.owned_repair_queue import valid_success
        path=Path(__file__).resolve().parents[1]/'evidence/phase13/qwen_contract_39947581082.json'
        raw=path.read_bytes()
        from bountyforge.repair_engines import digest
        self.assertEqual(digest(raw),'73eaeabbfc8de3777e594aa1e661be448ddb3a799da7fae8f219459422f960df')
        report=json.loads(raw)
        self.assertEqual(report['model_calls'],2)
        self.assertFalse(report['independent_evaluation'])
        self.assertEqual(len(report['experiments']),2)
        for experiment in report['experiments']:
            receipt=experiment['result']['verification_receipt']
            self.assertTrue(valid_success(receipt,'optional-setting','QWEN_LOCAL'))
            self.assertFalse(valid_success(receipt,'optional-setting','CODEX_AGENT'))

    def test_no_inference_outside_explicit_public_host_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.json'
            with patch.dict(canary.os.environ,{},clear=True),patch.object(canary,'RepairService') as service:
                self.assertEqual(canary.main(['--output',str(path)]),1)
                service.assert_not_called()
            result=json.loads(path.read_text())
            self.assertEqual(result['status'],'BLOCKED')
            self.assertEqual(result['experiments'],[])
            self.assertFalse(result['independent_evaluation'])
            self.assertEqual(result['max_model_calls'],4)
