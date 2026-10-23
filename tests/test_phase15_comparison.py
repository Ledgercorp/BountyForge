import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import phase15_model_comparison as comparison


class ComparisonAdmissionTests(unittest.TestCase):
    def test_no_resource_probe_queue_or_inference_without_free_host_gate(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(comparison.os.environ,{},clear=True), \
             patch.object(comparison,'LocalRuntime') as runtime,patch.object(comparison,'OwnedRepairQueue') as queue:
            output=Path(d)/'report.json'
            self.assertEqual(comparison.main(['--experiment-sha256','0'*64,'--output',str(output)]),1)
            runtime.assert_not_called();queue.assert_not_called()
            report=json.loads(output.read_bytes())
            self.assertEqual(report['models'],[]);self.assertFalse(report['default_replaced'])
            self.assertIsNone(report['independent_accuracy'])

    def test_resource_prompt_has_no_fake_failure_or_solution_and_uses_unchanged_budget(self):
        raw=comparison.resource_prompt();task=json.loads(raw)
        self.assertLessEqual(len(raw.encode()),3600);self.assertGreaterEqual(len(raw.encode()),3300)
        self.assertEqual(task['failure_feedback']['failing_tests'],[])
        self.assertNotIn('reference',task);self.assertNotIn('tests',task)
        self.assertIn('RESOURCE_PROBE',task['failure_feedback']['classification'])
