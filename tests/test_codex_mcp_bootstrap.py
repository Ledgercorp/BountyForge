"""No-cost, credential-free Black Box of repeatable Codex MCP registration.

Uses a fake *Codex CLI process* only for bootstrap registration testing.
Actual Codex-client acceptance is provided by codex_mcp_acceptance.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import bootstrap_codex_mcp as bootstrap


class CodexBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bountyforge-bootstrap-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inventory = self.root / "mcp.json"
        stub = self.root / "codex"
        stub.write_text("#!" + sys.executable + "\n" + r'''
import json, os, pathlib, sys
args = sys.argv[1:]
path = pathlib.Path(os.environ["CODEX_STUB_STATE"])
state = json.loads(path.read_text()) if path.exists() else []
if args == ["mcp", "list", "--json"]:
    print(json.dumps(state))
elif len(args) >= 5 and args[:4] == ["mcp", "add", "bountyforge", "--"]:
    state.append({"name":"bountyforge", "enabled":True,
                  "transport":{"type":"stdio","command":args[4],"args":args[5:]}})
    path.write_text(json.dumps(state))
    print("Added")
else:
    raise SystemExit(2)
''')
        stub.chmod(0o700)
        self.envpatch = patch.dict(os.environ, {
            "PATH": str(self.root) + os.pathsep + os.environ.get("PATH", ""),
            "CODEX_STUB_STATE": str(self.inventory),
        })
        self.envpatch.start()
        self.addCleanup(self.envpatch.stop)

    def test_register_once_then_idempotent_for_same_checkout(self):
        self.assertEqual(bootstrap.register(), "REGISTERED_THIS_SESSION")
        state = json.loads(self.inventory.read_text())
        self.assertEqual(len(state), 1)
        argv = bootstrap.desired()
        self.assertEqual(state[0]["transport"]["command"], "env")
        self.assertEqual(state[0]["transport"]["args"], argv[1:])
        self.assertEqual(bootstrap.register(), "ALREADY_REGISTERED")
        self.assertEqual(len(json.loads(self.inventory.read_text())), 1)
        self.assertTrue(bootstrap.register(check_only=True))

    def test_check_mode_never_changes_configuration(self):
        with self.assertRaises(bootstrap.BootstrapBlocked):
            bootstrap.register(check_only=True)
        self.assertFalse(self.inventory.exists())

    def test_existing_foreign_registration_is_not_overwritten(self):
        self.inventory.write_text(json.dumps([{"name":"bountyforge", "enabled":True,
            "transport":{"type":"stdio","command":"sh","args":["-c","echo malicious"]}}]))
        original = self.inventory.read_bytes()
        with self.assertRaises(bootstrap.BootstrapBlocked):
            bootstrap.register()
        self.assertEqual(self.inventory.read_bytes(), original)

    def test_duplicate_or_disabled_registration_fails_closed(self):
        original = {"name":"bountyforge","enabled":True,"transport":{
            "type":"stdio","command":"env","args":bootstrap.desired()[1:]}}
        for candidate in ([original,original],[dict(original,enabled=False)],"INVALID"):
            self.inventory.write_text(
                json.dumps(candidate) if candidate!="INVALID" else "not json")
            with self.assertRaises(bootstrap.BootstrapBlocked):
                bootstrap.register()

    def test_registered_child_has_isolated_environment_and_actual_mcp_response(self):
        argv = bootstrap.desired()
        input_data = b"".join(json.dumps(obj).encode()+b"\n" for obj in (
            {"jsonrpc":"2.0","id":1,"method":"initialize",
             "params":{"protocolVersion":"2025-11-25","capabilities":{},
                       "clientInfo":{"name":"bootstrap-blackbox","version":"1"}}},
            {"jsonrpc":"2.0","method":"notifications/initialized"},
            {"jsonrpc":"2.0","id":2,"method":"tools/list"},
        ))
        p = subprocess.run(argv,cwd=bootstrap.ROOT, input=input_data,
            capture_output=True,timeout=10,env={"PATH":"/usr/bin:/bin",
            "STRIPE_SECRET_KEY":"never-copy-me","GITHUB_TOKEN":"never-copy-me"})
        self.assertEqual(p.returncode, 0, p.stderr[:300])
        self.assertNotIn(b"never-copy-me",p.stdout+p.stderr)
        records = [json.loads(x) for x in p.stdout.splitlines()]
        self.assertEqual(records[0]["result"]["serverInfo"]["name"],
                         "bountyforge-owned-review")
        self.assertEqual({t['name'] for t in records[1]['result']['tools']},{
            'bountyforge_status','list_owned_calibration','inspect_owned_calibration',
            'verify_owned_reference','preview_owned_review_package','list_repair_engines',
            'list_owned_repair_tasks','prepare_owned_repair','submit_owned_repair','run_owned_qwen',
            'create_owned_queue','claim_owned_queue','submit_owned_queue','run_owned_queue_qwen',
            'heartbeat_owned_queue','release_owned_queue','owned_queue_status','stop_owned_queue'})

    def test_cli_register_redacts_sensitive_details(self):
        previous = self.inventory.read_bytes() if self.inventory.exists() else None
        result = subprocess.run([sys.executable,"-m","scripts.bootstrap_codex_mcp",
            "--register"],cwd=bootstrap.ROOT,capture_output=True,timeout=12,
            env=dict(os.environ,STRIPE_SECRET_KEY="sentinel-DO-NOT-EMIT"))
        self.assertEqual(result.returncode,0, result.stderr[:200])
        record=json.loads(result.stdout)
        self.assertEqual(record["registration"],"REGISTERED_THIS_SESSION")
        self.assertFalse(record["persistent_across_codex_cloud_sessions"])
        self.assertFalse(record["commercial_launch_authorized"])
        self.assertNotIn(b"sentinel-DO-NOT-EMIT",result.stdout+result.stderr)

    def test_verify_client_acceptance_requires_real_proof_shape(self):
        approved={"valid_calls":"5/5","authorization_refusals":5,
                  "mcp_process_environment_names":["PATH"],
                  "model_turns_started":0,"inference_calls":0,
                  "app_server_exit":0}
        done=subprocess.CompletedProcess(args=[],returncode=0,
            stdout=json.dumps(approved).encode(),stderr=b"")
        with patch.object(bootstrap.subprocess,"run",return_value=done):
            self.assertEqual(bootstrap.verify_client(),"VERIFIED_THIS_SESSION")
        for override in ({"valid_calls":"4/5"},{"inference_calls":1},
                         {"mcp_process_environment_names":["PATH","GITHUB_TOKEN"]}):
            with patch.object(bootstrap.subprocess,"run",
                    return_value=subprocess.CompletedProcess(args=[],returncode=0,
                    stdout=json.dumps(dict(approved,**override)).encode(),stderr=b"")):
                with self.assertRaises(bootstrap.BootstrapBlocked):
                    bootstrap.verify_client()

    def test_non_linux_or_missing_codex_fails_without_registering(self):
        with patch.object(bootstrap.sys,"platform","darwin"):
            with self.assertRaises(bootstrap.BootstrapBlocked):
                bootstrap.register()
        with patch.object(bootstrap.shutil,"which",return_value=None):
            with self.assertRaises(bootstrap.BootstrapBlocked):
                bootstrap.register()
        self.assertFalse(self.inventory.exists())

if __name__ == "__main__":
    unittest.main()
