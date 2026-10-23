"""Restore the owned-only BountyForge MCP in an authorized Linux Codex session.

No secrets are read, copied, persisted or passed to the MCP subprocess.
Nothing runs on the Mac, connects to customers or deploys a remote endpoint.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

NAME = "bountyforge"
ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "bountyforge" / "mcp_server.py"
TIMEOUT = 25


class BootstrapBlocked(RuntimeError):
    """A sanitized, fail-closed setup or verification failure."""


def desired():
    if sys.platform != "linux" or not SERVER.is_file():
        raise BootstrapBlocked("Linux trusted checkout with MCP source required")
    if not Path(sys.executable).is_absolute():
        raise BootstrapBlocked("Absolute trusted Python required")
    # Use -I and explicit trusted-module path. The child gets PATH only.
    # repr() quotes the checkout path without allowing shell interpolation.
    code = ("import sys;sys.path.insert(0," + repr(str(ROOT)) +
            ");from bountyforge.mcp_server import main;raise SystemExit(main())")
    return ["env", "-i", "PATH=/usr/bin:/bin", sys.executable,
            "-I", "-c", code]


def _codex(*args):
    if not shutil.which("codex"):
        raise BootstrapBlocked("Codex CLI is unavailable on this host")
    try:
        p = subprocess.run(["codex", *args], cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise BootstrapBlocked("Codex MCP operation unavailable") from None
    if p.returncode != 0 or len(p.stdout) > 65536:
        raise BootstrapBlocked("Codex MCP operation failed") from None
    return p.stdout


def _entries():
    try:
        data = json.loads(_codex("mcp", "list", "--json"))
    except (ValueError, UnicodeError):
        raise BootstrapBlocked("Codex MCP inventory unreadable") from None
    if isinstance(data, list):
        result = data
    elif type(data) is dict and type(data.get("servers")) is list:
        result = data["servers"]
    else:
        raise BootstrapBlocked("Unrecognized Codex MCP inventory")
    if not all(type(row) is dict for row in result):
        raise BootstrapBlocked("Unrecognized Codex MCP inventory")
    return [row for row in result if row.get("name") == NAME]


def _matches(entry, command):
    transport = entry.get("transport")
    if type(transport) is dict:
        info = transport
        mode = info.get("type")
    else:
        info = entry
        mode = transport if isinstance(transport, str) else "stdio"
    if mode != "stdio":
        return False
    if entry.get("enabled") is not True:
        return False
    args = info.get("args")
    if info.get("command") != command[0] or type(args) is not list:
        return False
    return args == command[1:]


def register(*, check_only=False):
    args = desired()
    found = _entries()
    if len(found) > 1:
        raise BootstrapBlocked("Ambiguous BountyForge MCP registration")
    if found:
        if not _matches(found[0], args):
            # Never overwrite a different owner/server, even by accident.
            raise BootstrapBlocked("Conflicting or stale MCP registration; manual review needed")
        return "ALREADY_REGISTERED"
    if check_only:
        raise BootstrapBlocked("BountyForge MCP is not registered")
    _codex("mcp", "add", NAME, "--", *args)
    confirmed = _entries()
    if len(confirmed) != 1 or not _matches(confirmed[0], args):
        raise BootstrapBlocked("Registration not confirmed by Codex")
    return "REGISTERED_THIS_SESSION"


def verify_client():
    # This existing harness actually calls through Codex app-server's MCP
    # client; a direct Python invocation is not a verified Codex connection.
    try:
        p = subprocess.run(
            [sys.executable, "-m", "scripts.codex_mcp_acceptance"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise BootstrapBlocked("Codex client acceptance unavailable") from None
    if p.returncode or len(p.stdout) > 65536:
        raise BootstrapBlocked("Codex client acceptance failed") from None
    try:
        result = json.loads(p.stdout)
    except (ValueError, UnicodeError):
        raise BootstrapBlocked("Codex client evidence malformed") from None
    if (type(result) is not dict or result.get("valid_calls") != "5/5"
            or result.get("authorization_refusals") != 5
            or result.get("mcp_process_environment_names") != ["PATH"]
            or result.get("model_turns_started") != 0
            or result.get("inference_calls") != 0
            or result.get("app_server_exit") != 0):
        raise BootstrapBlocked("Codex client evidence did not meet acceptance policy")
    return "VERIFIED_THIS_SESSION"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Restore owner-private Codex MCP session")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--register", action="store_true")
    modes.add_argument("--check", action="store_true")
    parser.add_argument("--verify", action="store_true",
                        help="Run real Codex app-server Black Box calls (register only)")
    opts = parser.parse_args(argv)
    if opts.verify and not opts.register:
        parser.error("--verify requires --register")
    try:
        state = register(check_only=opts.check)
        verification = verify_client() if opts.verify else "NOT_RUN"
        print(json.dumps({
            "kind": "bountyforge_codex_session_bootstrap",
            "registration": state, "client_acceptance": verification,
            "persistent_across_codex_cloud_sessions": False,
            "private_execution_admitted": False,
            "commercial_launch_authorized": False,
            "mcp_process_allowed_environment": ["PATH"],
            "new_infrastructure_spending_usd": 0,
        }, sort_keys=True))
        return 0
    except BootstrapBlocked:
        # Never reveal CLI config, provider secrets or arbitrary paths in logs.
        print(json.dumps({"kind": "bountyforge_codex_session_bootstrap",
                          "status": "BLOCKED", "private_execution_admitted": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
