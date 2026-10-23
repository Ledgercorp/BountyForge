"""Offline contract tests for Phase 17 external Docker isolation admission."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from phase17_isolation import (
    IMAGE, IMAGE_PIN, IsolationUnavailable, PROBE, REQUIRED,
    docker_command, host_gate, main, validate_observation,
)


class Phase17IsolationTests(unittest.TestCase):
    def test_existing_verifier_image_is_exact(self):
        self.assertEqual(IMAGE, IMAGE_PIN)
        self.assertRegex(IMAGE, r"^python@sha256:[0-9a-f]{64}$")

    def test_probe_is_syntax_valid_and_has_no_provider(self):
        compile(PROBE, "phase17_inert_probe", "exec")
        self.assertNotIn("DeepSeekHarness(", PROBE)
        self.assertNotIn("GROQ_API_KEY", PROBE)

    def test_explicit_command_flag_required(self):
        self.assertEqual(main([]), 2)

    def test_authorized_public_linux_gate(self):
        allowed = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "Ledgercorp/BountyForge",
            "RUNNER_OS": "Linux",
            "RUNNER_ARCH": "X64",
            "BOUNTYFORGE_PHASE17_PROBE_ACK": "1",
        }
        host_gate(allowed, linux=True)
        for key in allowed:
            wrong = dict(allowed)
            wrong[key] = "untrusted"
            with self.subTest(key=key), self.assertRaises(IsolationUnavailable):
                host_gate(wrong, linux=True)
        with self.assertRaises(IsolationUnavailable):
            host_gate(allowed, linux=False)

    def test_fixed_docker_container_constraints(self):
        with tempfile.TemporaryDirectory() as directory:
            cmd = docker_command("/usr/bin/docker", Path(directory), "bf-p17-" + "a" * 16)
        flags = cmd[3:-6]
        for expected in (
            "--pull=never", "--network=none", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit=32",
            "--memory=192m", "--memory-swap=192m", "--cpus=1",
            "--user=65534:65534", "--cgroupns=private", "--ipc=none",
        ):
            self.assertIn(expected, cmd, expected)
        self.assertEqual(cmd.count("--mount=type=bind,source="+directory+",target=/workspace,readonly"), 1)
        self.assertEqual(cmd[-6:], [IMAGE, "python", "-I", "-B", "-c", PROBE])
        self.assertFalse(any("GITHUB_TOKEN" in value or "DOCKER_HOST" in value for value in cmd))
        self.assertFalse(any("network=host" in value for value in cmd))
        self.assertFalse(any("/var/run/docker.sock" in value for value in cmd if value.startswith("--mount")))

    def test_no_unbounded_docker_argv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(IsolationUnavailable):
                docker_command("docker", root, "bf-p17-"+ "a"*16)
            with self.assertRaises(IsolationUnavailable):
                docker_command("/usr/bin/python", root, "bf-p17-"+ "a"*16)
            with self.assertRaises(IsolationUnavailable):
                docker_command("/usr/bin/docker", Path("relative"), "bf-p17-"+ "a"*16)
            with self.assertRaises(IsolationUnavailable):
                docker_command("/usr/bin/docker", root, "not-a-valid-name")
            (root/"redirect").symlink_to(root)
            with self.assertRaises(IsolationUnavailable):
                docker_command("/usr/bin/docker", root/"redirect", "bf-p17-"+ "a"*16)

    def test_proof_requires_every_boolean(self):
        payload = {"schema": 1, **{k: True for k in REQUIRED}}
        self.assertEqual(validate_observation(json.dumps(payload)), payload)
        for key in REQUIRED:
            changed = dict(payload)
            changed[key] = False
            with self.subTest(key=key), self.assertRaises(IsolationUnavailable):
                validate_observation(json.dumps(changed))
        changed = dict(payload)
        changed["extra"] = True
        with self.assertRaises(IsolationUnavailable):
            validate_observation(json.dumps(changed))
        changed = dict(payload)
        changed.pop("seccomp_enabled")
        with self.assertRaises(IsolationUnavailable):
            validate_observation(json.dumps(changed))

    def test_malformed_receipts_fail_closed(self):
        for bad in ("", "{", "[]", "NaN", "0", "x"*5100):
            with self.subTest(bad=bad[:30]), self.assertRaises(IsolationUnavailable):
                validate_observation(bad)

    def test_probe_privilege_assumptions_are_explicit(self):
        self.assertIn("os.geteuid()==65534", PROBE)
        self.assertIn("NoNewPrivs", PROBE)
        self.assertIn("CapEff", PROBE)
        self.assertIn("Seccomp", PROBE)
        self.assertIn("socket.if_nameindex()", PROBE)
        self.assertIn("pids.max", PROBE)
        self.assertIn("cpu.max", PROBE)
        self.assertIn("memory.max", PROBE)


if __name__ == "__main__":
    unittest.main()
