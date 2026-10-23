import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import phase14_qwen_session as session


class QwenAdmissionTests(unittest.TestCase):
    def test_no_runtime_or_queue_without_free_execution_gate(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'report.json'
            with patch.dict(session.os.environ,{},clear=True),patch.object(session,'OwnedRepairQueue') as queue:
                self.assertEqual(session.main(['--output',str(path)]),1)
                queue.assert_not_called()
            report=json.loads(path.read_bytes())
            self.assertEqual(report['jobs'],[]);self.assertEqual(report['max_model_calls'],6)
            self.assertFalse(report['independent_evaluation'])
