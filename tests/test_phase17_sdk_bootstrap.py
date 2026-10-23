"""Non-executing SDK wheel provenance, extraction and Docker argv tests."""
import hashlib
import json
import os
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phase17_isolation import IMAGE, IsolationUnavailable
from phase17_sdk_bootstrap import (
    RUNTIME_BIN, RUNTIME_NAME, RUNTIME_SHA, SDK_NAME, SDK_SHA,
    extract_offline_runtime, main, sdk_bootstrap_command, validate_hardened_profile, _rpc_response, sanitized_boot_diagnostic,
)


class Phase17NativeSDKTests(unittest.TestCase):
    def test_release_is_exactly_pinned(self):
        self.assertRegex(SDK_SHA, r"^[0-9a-f]{64}$")
        self.assertRegex(RUNTIME_SHA, r"^[0-9a-f]{64}$")
        self.assertEqual(SDK_NAME, "deepseek_harness_sdk-0.2.1rc2-py3-none-any.whl")
        self.assertEqual(RUNTIME_NAME, "deepseek_harness_runtime_bin-0.2.1rc2-py3-none-manylinux_2_28_x86_64.whl")

    def test_requires_explicit_opt_in(self):
        self.assertEqual(main(["--wheel-directory", "/tmp/nonexistent"]), 2)

    def test_rejects_missing_and_wrong_release(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with self.assertRaisesRegex(IsolationUnavailable, "EXACT_RELEASE_WHEELS"):
                extract_offline_runtime(path, path / "out")
            (path / SDK_NAME).write_bytes(b"wrong")
            (path / RUNTIME_NAME).write_bytes(b"wrong")
            with self.assertRaisesRegex(IsolationUnavailable, "SHA256_MISMATCH"):
                extract_offline_runtime(path, path / "out")

    def test_rejects_relative_wheel_dir(self):
        with self.assertRaisesRegex(IsolationUnavailable, "SDK_WHEEL_DIR_REJECTED"):
            extract_offline_runtime(Path("relative"), Path("/tmp/new"))

    def test_no_native_sdk_execution_ever_on_host(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / RUNTIME_BIN).parent.mkdir(parents=True)
            (p / RUNTIME_BIN).write_bytes(b"not executed")
            args = sdk_bootstrap_command("/usr/bin/docker", p, "bf-p17-" + "a"*16, p)
        self.assertEqual(args[-5:], [
            IMAGE, "/opt/harness/" + RUNTIME_BIN, "--profile", "sdk-minimal",
            "--dump-default-config",
        ])
        self.assertIn("--network=none", args)
        self.assertIn("--read-only", args)
        self.assertIn("--cap-drop=ALL", args)
        self.assertIn("--pull=never", args)
        self.assertIn("--env=DSH_HOME=/tmp/dsh-home", args)
        self.assertFalse(any("api_key" in item.lower() for item in args))
        self.assertEqual(len([x for x in args if x.startswith("--mount=")]), 2)
        self.assertTrue(all("readonly" in x for x in args if x.startswith("--mount=")))


    def test_hardened_composition_requires_every_tool_disabled(self):
        from phase17_sdk_bootstrap import DISABLED_TOOL_ROWS
        parts = ["- id: sdk-jsonrpc-server", "  name: '@deepseek-ai/dsh-sdk-jsonrpc-server'"]
        for identity in DISABLED_TOOL_ROWS:
            parts.extend(["- id: " + identity, "  disabled: true"])
        parts.extend(["- id: session-log-deepseek", "  config:", "    enabled: false"])
        good = "\n".join(parts)
        self.assertRegex(validate_hardened_profile(good), r"^[a-f0-9]{64}$")
        for identity in DISABLED_TOOL_ROWS:
            with self.subTest(identity=identity), self.assertRaises(IsolationUnavailable):
                validate_hardened_profile(good.replace("- id: " + identity + "\n  disabled: true",
                                                       "- id: " + identity + "\n  disabled: false"))
        with self.assertRaisesRegex(IsolationUnavailable, "SDK_SESSION_LOG_UPLOAD"):
            validate_hardened_profile(good.replace("enabled: false", "enabled: true"))


    def test_sdk_rpc_exact_request_id_required(self):
        class FakeChild:
            def __init__(self, data):
                read_fd, write_fd = os.pipe()
                os.write(write_fd, data)
                os.close(write_fd)
                self.stdout = os.fdopen(read_fd, "rb")
            def poll(self):
                return None
        success = b'{"jsonrpc":"2.0","id":"phase17","result":{"serverInfo":{}}}\n'
        child = FakeChild(success)
        try:
            self.assertEqual(_rpc_response(child, "phase17", timeout=1), {"serverInfo": {}})
        finally:
            child.stdout.close()
        for invalid in (
            b'{"jsonrpc":"2.0","id":"phase17","error":{"code":-1}}\n',
            b'{"jsonrpc":"2.0","id":"wrong","result":{}}\n',
            b'not a json message\n',
        ):
            child = FakeChild(invalid)
            try:
                with self.assertRaises(IsolationUnavailable):
                    _rpc_response(child, "phase17", timeout=0.1)
            finally:
                child.stdout.close()

    def test_phase18_diagnostic_never_echoes_native_logs(self):
        sample = b"Cannot find module /tmp/private-key/foobar, ENOENT: no such file or directory\n"
        got = sanitized_boot_diagnostic(sample)
        self.assertIn("BAD_MODULE", got["signature"])
        self.assertIn("ENOENT", got["signature"])
        self.assertFalse(got["raw_stderr_disclosed"])
        self.assertNotIn("private-key", json.dumps(got))
        self.assertEqual(got["model_calls"], 0)
        self.assertEqual(got["stderr_bytes_captured"], len(sample))
        ids = sanitized_boot_diagnostic(
            b"required injection for sdk-jsonrpc-server: working-directory\n")["plugin_ids"]
        self.assertIn("sdk-jsonrpc-server", ids)
        self.assertIn("working-directory", ids)
        with self.assertRaises(IsolationUnavailable):
            sanitized_boot_diagnostic("not bytes")

    def test_sdk_root_must_be_known(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            with self.assertRaisesRegex(IsolationUnavailable, "SDK_NATIVE_ROOT_REJECTED"):
                sdk_bootstrap_command("/usr/bin/docker", p, "bf-p17-"+"a"*16, p)


if __name__ == "__main__":
    unittest.main()
