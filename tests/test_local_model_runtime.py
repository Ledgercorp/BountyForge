import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from unittest.mock import MagicMock
import time
from bountyforge.local_model_runtime import LocalRuntime,enforce_limits


class RuntimeBoundaryTests(unittest.TestCase):
    def test_bad_assets_never_start_a_process(self):
        with tempfile.TemporaryDirectory() as d,patch('bountyforge.local_model_runtime.require_credential_free_host'), \
             patch('pathlib.Path.home',return_value=Path(d)),patch('bountyforge.local_model_runtime.subprocess.Popen') as process:
            runtime=LocalRuntime('QWEN_7B')
            with self.assertRaises(ValueError):runtime.__enter__()
            process.assert_not_called();self.assertTrue(runtime.measurement['server_stopped'])

    def test_resource_limits_cannot_be_selected_by_caller(self):
        with patch('bountyforge.local_model_runtime.resource.setrlimit') as limit:enforce_limits()
        self.assertEqual(len(limit.call_args_list),4)
        self.assertIn(10*1024**3,[c.args[1][0] for c in limit.call_args_list])
        self.assertIn(180,[c.args[1][0] for c in limit.call_args_list])
        with self.assertRaises(ValueError):LocalRuntime('GROQ')

    def test_unexpected_process_exit_is_not_silently_recorded_as_normal_cleanup(self):
        runtime=LocalRuntime('QWEN_7B');runtime.child=Mock();runtime.child.poll.return_value=-9
        runtime.child.returncode=-9;runtime.started=time.monotonic()
        with patch.object(runtime,'_sample'):runtime.__exit__(None,None,None)
        self.assertTrue(runtime.measurement['unexpected_exit']);self.assertTrue(runtime.measurement['server_stopped'])
        runtime.child.terminate.assert_not_called()

    def test_owner_launcher_returns_failure_after_unexpected_server_exit(self):
        from scripts.local_inference import main
        factory=MagicMock();runtime=factory.return_value.__enter__.return_value
        runtime.child.poll.return_value=-9
        runtime.measurement={'server_stopped':True,'unexpected_exit':True,'wall_limit_reached':False}
        with patch('scripts.local_inference.LocalRuntime',factory):
            self.assertEqual(main(['--model-profile','QWEN_7B','--serve-seconds','1']),2)

    def test_parallelism_is_bounded_by_explicit_values_and_available_cpu(self):
        with self.assertRaises(ValueError):LocalRuntime('QWEN_7B',threads=8)
        with patch('bountyforge.local_model_runtime.os.cpu_count',return_value=2):
            with self.assertRaisesRegex(ValueError,'CPU_CAPACITY_UNAVAILABLE'):LocalRuntime('QWEN_7B',threads=4)
        with patch('bountyforge.local_model_runtime.os.cpu_count',return_value=4):
            runtime=LocalRuntime('QWEN_7B',threads=4)
        self.assertEqual(runtime.measurement['threads'],4)
        self.assertEqual(runtime.measurement['cpu_limit_seconds'],180)
