import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
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
