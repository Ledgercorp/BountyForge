import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import phase14_model_profile as probe


class ProfileGateTests(unittest.TestCase):
    def test_no_asset_read_process_or_inference_without_host_gate(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(probe.os.environ,{},clear=True), \
             patch.object(probe,'file_digest') as digest,patch.object(probe.subprocess,'Popen') as process:
            path=Path(d)/'report.json'
            self.assertEqual(probe.main(['--output',str(path)]),1)
            digest.assert_not_called();process.assert_not_called()
            result=json.loads(path.read_bytes())
            self.assertEqual(result['model_calls'],0);self.assertTrue(result['server_stopped'])
            self.assertFalse(result['repair_accuracy_measured']);self.assertFalse(result['default_model_replaced'])
