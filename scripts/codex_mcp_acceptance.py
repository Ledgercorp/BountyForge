"""Exercise BountyForge through the configured Codex MCP client.

This starts no Codex turn and makes no model request. It uses app-server MCP
discovery and tool-call methods, then checks recovery after process termination.
Run in a trusted checkout after registering the stdio server with Codex.
"""
from __future__ import annotations

import json
import os
import pathlib
import selectors
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED = {
    "bountyforge_status", "list_owned_calibration",
    "inspect_owned_calibration", "verify_owned_reference",
    "preview_owned_review_package",
    "list_repair_engines", "list_owned_repair_tasks", "prepare_owned_repair",
    "submit_owned_repair", "run_owned_qwen",
}


class CodexClient:
    def __init__(self, *, read_timeout=20) -> None:
        if sys.platform != "linux":
            raise RuntimeError("This process-boundary check requires Linux")
        self.process = subprocess.Popen(
            ["codex", "app-server", "--stdio"], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, bufsize=0,
        )
        self.selector = selectors.DefaultSelector()
        assert self.process.stdout and self.process.stdin
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = bytearray()
        self.read_timeout=read_timeout
        self.request_id = 0
        self.rpc("initialize", {"clientInfo": {
            "name": "bountyforge-phase9-blackbox", "version": "1"}})
        self.notify("initialized", {})

    def _read(self) -> dict:
        assert self.process.stdout
        deadline = time.monotonic() + self.read_timeout
        while time.monotonic() < deadline:
            if b"\n" in self.buffer:
                line, _, rest = self.buffer.partition(b"\n")
                self.buffer = bytearray(rest)
                return json.loads(line)
            if not self.selector.select(deadline - time.monotonic()):
                break
            data = os.read(self.process.stdout.fileno(), 65536)
            if not data:
                raise EOFError("Codex app-server stopped")
            self.buffer.extend(data)
        raise TimeoutError("Codex app-server response timed out")

    def rpc(self, method: str, params: dict) -> dict:
        assert self.process.stdin
        self.request_id += 1
        request_id = self.request_id
        self.process.stdin.write(json.dumps({
            "id": request_id, "method": method, "params": params,
        }).encode() + b"\n")
        while True:
            response = self._read()
            if response.get("id") == request_id:
                return response

    def notify(self, method: str, params: dict) -> None:
        assert self.process.stdin
        self.process.stdin.write(json.dumps({
            "method": method, "params": params,
        }).encode() + b"\n")

    def thread(self) -> str:
        response = self.rpc("thread/start", {
            "cwd": str(ROOT), "ephemeral": True, "approvalPolicy": "never",
        })
        if "error" in response:
            raise RuntimeError("Codex could not start an ephemeral acceptance thread")
        return response["result"]["thread"]["id"]

    def status(self, thread_id: str) -> dict:
        return self.rpc("mcpServerStatus/list", {
            "threadId": thread_id, "serverName": "bountyforge",
            "detail": "toolsAndAuthOnly",
        })

    def call(self, thread_id: str, name: str, arguments: dict) -> dict:
        return self.rpc("mcpServer/tool/call", {
            "threadId": thread_id, "server": "bountyforge", "tool": name,
            "arguments": arguments,
        })

    def stop(self) -> int:
        assert self.process.stdin
        self.process.stdin.close()
        self.process.wait(timeout=10)
        return self.process.returncode


def _payload(response: dict) -> dict:
    if "error" in response:
        raise RuntimeError("Codex MCP call failed")
    result = response["result"]
    if result.get("isError"):
        raise ValueError("BountyForge refused a tool call")
    return json.loads(result["content"][0]["text"])


def _mcp_processes() -> dict[int, dict]:
    """Read process ancestry and variable names, never environment values."""
    found = {}
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text()
            parent = int(stat[stat.rfind(")") + 2:].split()[1])
            command = (entry / "cmdline").read_bytes().split(b"\0")
            if not any(b"bountyforge.mcp_server" in arg for arg in command):
                continue
            names = {
                item.partition(b"=")[0].decode("ascii", errors="replace")
                for item in (entry / "environ").read_bytes().split(b"\0")
                if b"=" in item
            }
            found[int(entry.name)] = {"parent": parent, "environment_names": names}
        except (OSError, ValueError, IndexError):
            continue
    return found


def _owned_child(process_id: int) -> tuple[int, dict]:
    matches = [(pid, info) for pid, info in _mcp_processes().items()
               if info["parent"] == process_id]
    if len(matches) != 1:
        raise RuntimeError("Could not identify exactly one BountyForge MCP child")
    return matches[0]


def main() -> int:
    report = {
        "client": "Codex app-server",
        "model_turns_started": 0,
        "inference_calls": 0,
        "tool_calls": 0,
        "authorization_refusals": 0,
    }
    client = CodexClient()
    try:
        thread = client.thread()
        status = client.status(thread)
        servers = status.get("result", {}).get("data", [])
        matches = [item for item in servers if item["name"] == "bountyforge"]
        if (len(matches) != 1 or matches[0]["runtimeStatus"] != "connected"
                or set(matches[0]["tools"]) != EXPECTED):
            raise RuntimeError("Codex discovery did not return the exact owned tool inventory")
        report["discovered_tools"] = sorted(matches[0]["tools"])

        requests = {
            "bountyforge_status": {},
            "list_owned_calibration": {},
            "inspect_owned_calibration": {"case_id": "page-offset-boundary"},
            "verify_owned_reference": {"case_id": "page-offset-boundary"},
            "preview_owned_review_package": {},
        }
        outputs = {}
        for name, arguments in requests.items():
            outputs[name] = _payload(client.call(thread, name, arguments))
            report["tool_calls"] += 1

        system = outputs["bountyforge_status"]
        assert system["private_execution_admitted"] is False
        assert system["commercial_launch_authorized"] is False
        assert system["live_model_accuracy"] is None
        assert len(outputs["list_owned_calibration"]["cases"]) == 4
        defect = outputs["inspect_owned_calibration"]
        assert "start = number * size + 1" in defect["source"]
        assert defect["reference_solution_disclosed"] is False
        reference = outputs["verify_owned_reference"]
        assert reference["authorship"] == "preauthored_reference_only"
        assert reference["ai_generated_patch"] is False
        package = outputs["preview_owned_review_package"]
        assert package["preview_only"] is True and package["files_written"] == 0
        report["valid_calls"] = "5/5"

        rejected = [
            ("bountyforge_status", {"delivery_authorized": True}),
            ("inspect_owned_calibration", {"case_id": "../../secret"}),
            ("verify_owned_reference", {
                "case_id": "page-offset-boundary", "source": "customer"}),
            ("preview_owned_review_package", {"output_dir": "/tmp"}),
        ]
        for name, arguments in rejected:
            response = client.call(thread, name, arguments)
            if "result" not in response or response["result"].get("isError") is not True:
                raise AssertionError("Codex MCP accepted unauthorized arguments")
            report["authorization_refusals"] += 1
        response = client.call(thread, "execute_customer_code", {"command": "id"})
        if "error" not in response:
            raise AssertionError("Codex MCP exposed an unknown tool")
        report["authorization_refusals"] += 1

        pid, child = _owned_child(client.process.pid)
        leaked = {"GITHUB_TOKEN", "GH_TOKEN", "GROQ_API_KEY", "STRIPE_SECRET_KEY"}
        if child["environment_names"] & leaked:
            raise AssertionError("A credential variable reached the MCP process")
        if child["environment_names"] != {"PATH"}:
            raise AssertionError("MCP process environment exceeded its allowlist")
        report["mcp_process_environment_names"] = sorted(child["environment_names"])

        os.kill(pid, signal.SIGKILL)
        time.sleep(0.2)
        after_kill = client.status(thread).get("result", {}).get("data", [])
        report["status_after_controlled_termination"] = next(
            (item["runtimeStatus"] for item in after_kill
             if item["name"] == "bountyforge"), "absent")

        resumed_thread = client.thread()
        resumed = client.status(resumed_thread).get("result", {}).get("data", [])
        servers = [item for item in resumed if item["name"] == "bountyforge"]
        if len(servers) != 1 or servers[0]["runtimeStatus"] != "connected":
            raise RuntimeError("Codex did not reconnect the MCP server")
        _payload(client.call(resumed_thread, "bountyforge_status", {}))
        report["reconnection"] = "connected and invoked on a fresh Codex thread"
    finally:
        report["app_server_exit"] = client.stop()
    report["configuration_persists_across_sessions"] = False
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, EOFError, OSError, RuntimeError, TimeoutError, ValueError):
        # Do not print provider metadata or process command lines on failure.
        print(json.dumps({"acceptance": "failed", "details": "sanitized"}))
        raise SystemExit(1)
