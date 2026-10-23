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
            self.assertEqual(report['jobs'],[]);self.assertEqual(report['max_model_calls'],8)
            self.assertEqual(report['max_repair_model_calls'],6)
            self.assertFalse(report['independent_evaluation'])

    def test_failed_full_contract_probe_blocks_all_repair_execution(self):
        env={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'Ledgercorp/BountyForge',
             'GITHUB_REF':'refs/heads/engineering/revenue-linux-scout-20261021',
             'RUNNER_OS':'Linux','RUNNER_ARCH':'X64','BOUNTYFORGE_PHASE14_QWEN_ACK':'true'}
        with tempfile.TemporaryDirectory() as d,patch.dict(session.os.environ,env,clear=True), \
             patch.object(session,'require_credential_free_host'),patch.object(session,'qwen_availability',return_value=True), \
             patch.object(session,'OwnedRepairQueue') as queue,patch.object(session,'NativeStatementModel') as factory:
            factory.return_value._complete_bounded_schema.side_effect=['{"probe":"bf14-verified-schema-01"}',
                '{"changes":[{"line":99,"new":"return value"}]}']
            factory.return_value.last_call={}
            path=Path(d)/'report.json'
            self.assertEqual(session.main(['--output',str(path)]),1);queue.assert_not_called()
            report=json.loads(path.read_bytes())
            self.assertEqual(report['model_calls'],2);self.assertEqual(report['jobs'],[])
            self.assertFalse(report['protocol_probes'][1]['enforced'])
