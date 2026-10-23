import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import phase13_qwen_contract_canary as canary


class CanaryAdmissionTests(unittest.TestCase):
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
