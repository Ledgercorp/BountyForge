from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class QualityReplayBoundaryTests(unittest.TestCase):
    def test_vocabulary_qa_never_runs_without_explicit_model_free_admission(self):
        try:from phase21_wire_qa import run
        except ImportError:self.fail('Model-free vocabulary QA admission is missing')
        with self.assertRaisesRegex(ValueError,'EXPLICIT_VOCABULARY'):run()

    def test_replay_is_explicit_and_cannot_launch_a_model_as_fallback(self):
        try:from phase21_replay import replay
        except ImportError:self.fail('Explicit recorded-only quality replay is missing')
        with self.assertRaisesRegex(ValueError,'EXPLICIT_RECORDED'):replay()

    def test_process_boundary_rejects_unknown_customer_execution_without_an_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'unauthorized.json'
            r=subprocess.run([sys.executable,'-B','-m','phase21_replay','--output',str(output),'--execute-customer'],
                cwd=Path(__file__).resolve().parents[1],capture_output=True,timeout=5)
            self.assertEqual(r.returncode,2)
            self.assertFalse(output.exists())
