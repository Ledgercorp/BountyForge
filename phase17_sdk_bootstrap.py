"""Pinned, model-free native DeepSeek Harness runtime bootstrap in locked Docker.

Downloads are performed separately by the trusted CI job, *never installed or
executed on the host*. The exact published SDK and Linux native runtime wheels
are hash-checked. Only the native runtime payload is extracted into a disposable
directory and executed within the independently tested no-network container.
This invokes CLI --dump-default-config ONLY; no SDK agent turn, model, tool,
network request, credential or customer source is permitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import time
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile

from phase17_isolation import (
    IMAGE, IsolationUnavailable, PROBE_TIMEOUT_SECONDS, docker_command,
    host_gate,
)

RELEASE = "0.2.1rc2"
SDK_NAME = "deepseek_harness_sdk-0.2.1rc2-py3-none-any.whl"
SDK_SHA = "30fc72c67f20ff4b46c6952087ea596fc70c2692001aa372185a24f9866bdc46"
RUNTIME_NAME = "deepseek_harness_runtime_bin-0.2.1rc2-py3-none-manylinux_2_28_x86_64.whl"
RUNTIME_SHA = "0a0a4eb85a22cd9339972e6a5ced77a27ec791353a5b220e3e10b8cdbbdeca39"
RUNTIME_BIN = "deepseek_harness_runtime/runtime/deepseek-harness-sdk-runtime-linux-x64"
MAX_WHEEL_BYTES = 125_000_000
MAX_UNCOMPRESSED = 1_000_000_000
MAX_MEMBER_BYTES = 850_000_000
MAX_MEMBERS = 5_000


def _safe_wheel_file(path, digest):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_WHEEL_BYTES:
        raise IsolationUnavailable("PINNED_SDK_WHEEL_UNAVAILABLE")
    with path.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != digest:
        raise IsolationUnavailable("PINNED_SDK_WHEEL_SHA256_MISMATCH")


def extract_offline_runtime(wheel_dir, destination):
    """Hash-check both wheels; extract only native runtime without host execution."""
    if (not isinstance(wheel_dir, Path) or not wheel_dir.is_absolute()
            or wheel_dir.is_symlink() or not wheel_dir.is_dir()
            or not isinstance(destination, Path) or not destination.is_absolute()):
        raise IsolationUnavailable("SDK_WHEEL_DIR_REJECTED")
    files = list(wheel_dir.iterdir())
    if {p.name for p in files} != {SDK_NAME, RUNTIME_NAME}:
        raise IsolationUnavailable("EXACT_RELEASE_WHEELS_REQUIRED")
    _safe_wheel_file(wheel_dir / SDK_NAME, SDK_SHA)
    _safe_wheel_file(wheel_dir / RUNTIME_NAME, RUNTIME_SHA)
    if destination.exists():
        raise IsolationUnavailable("SDK_OUTPUT_MUST_BE_NEW")
    destination.mkdir(mode=0o755)
    total = 0
    expected = False
    try:
        with zipfile.ZipFile(wheel_dir / RUNTIME_NAME) as package:
            items = package.infolist()
            if not items or len(items) > MAX_MEMBERS:
                raise IsolationUnavailable("SDK_WHEEL_ARCHIVE_SCOPE")
            seen = set()
            for item in items:
                part = PurePosixPath(item.filename)
                if (item.filename in seen or "\\" in item.filename
                        or part.is_absolute() or ".." in part.parts
                        or item.filename.startswith("./")
                        or not item.filename.startswith("deepseek_harness_runtime/")
                        and not item.filename.startswith("deepseek_harness_runtime_bin-0.2.1rc2.dist-info/")):
                    raise IsolationUnavailable("SDK_WHEEL_MEMBER_REJECTED")
                seen.add(item.filename)
                mode = item.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise IsolationUnavailable("SDK_WHEEL_MEMBER_REJECTED")
                if (item.file_size > MAX_MEMBER_BYTES or item.file_size < 0
                        or total + item.file_size > MAX_UNCOMPRESSED):
                    raise IsolationUnavailable("SDK_WHEEL_CONTENT_BUDGET")
                total += item.file_size
                # Extract only the executable and its bundled sidecars/resources,
                # never dist-info scripts or other wheel-managed files.
                if not item.filename.startswith("deepseek_harness_runtime/"):
                    continue
                target = destination.joinpath(*part.parts)
                if item.is_dir():
                    target.mkdir(mode=0o755, parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                with package.open(item) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                if item.filename == RUNTIME_BIN or item.filename.endswith("-rg"):
                    target.chmod(0o555)
                else:
                    target.chmod(0o444)
                if item.filename == RUNTIME_BIN:
                    expected = True
    except (OSError, zipfile.BadZipFile, EOFError):
        raise IsolationUnavailable("SDK_WHEEL_EXTRACTION_FAILED") from None
    if not expected or not (destination / RUNTIME_BIN).is_file():
        raise IsolationUnavailable("SDK_NATIVE_RUNTIME_MISSING")
    return {
        "sdk_release": RELEASE,
        "sdk_wheel_sha256": SDK_SHA,
        "runtime_wheel_sha256": RUNTIME_SHA,
        "payload_uncompressed_bytes": total,
    }


def sdk_bootstrap_command(binary, workspace, container_name, native_root):
    cmd = docker_command(binary, workspace, container_name)
    if (not isinstance(native_root, Path) or not native_root.is_absolute()
            or native_root.is_symlink() or not (native_root / RUNTIME_BIN).is_file()):
        raise IsolationUnavailable("SDK_NATIVE_ROOT_REJECTED")
    # Preserve all Phase17 whole-process Docker restrictions, no model/secret
    # or network grant; only add a second read-only immutable SDK payload mount.
    cmd.insert(-6, "--mount=type=bind,source=" + str(native_root)
               + ",target=/opt/harness,readonly")
    cmd.insert(-6, "--env=DSH_HOME=/tmp/dsh-home")
    cmd[-6:] = [
        IMAGE, "/opt/harness/" + RUNTIME_BIN, "--profile", "sdk-minimal",
        "--dump-default-config",
    ]
    return cmd



DISABLED_TOOL_ROWS = (
    "persistent-bash", "persistent-pwsh", "terminal-bash", "terminal-pwsh",
    "tool-fs", "tool-working-directory", "mcp-resources",
)


def _profile_row(output, identity):
    """Find one composed final profile row, not a comment or overlay fragment."""
    lines = output.splitlines()
    starts = []
    for index, line in enumerate(lines):
        if re.match(r"^\s*-\s+id:\s+" + re.escape(identity) + r"\s*$", line):
            starts.append(index)
    if len(starts) != 1:
        raise IsolationUnavailable("SDK_PROFILE_ROW_IDENTITY_REJECTED")
    start = starts[0]
    depth = len(lines[start]) - len(lines[start].lstrip())
    stop = next((i for i in range(start + 1, len(lines))
                 if re.match(r"^\s*-\s+id:\s+", lines[i])
                 and len(lines[i]) - len(lines[i].lstrip()) <= depth), len(lines))
    return "\n".join(lines[start:stop])


def validate_hardened_profile(text):
    if type(text) is not str or len(text.encode("utf-8")) > 200_000:
        raise IsolationUnavailable("SDK_HARDENED_OUTPUT_BUDGET")
    if "sdk-jsonrpc-server" not in text:
        raise IsolationUnavailable("SDK_PROFILE_UNRECOGNIZED")
    for item in DISABLED_TOOL_ROWS:
        row = _profile_row(text, item)
        if not re.search(r"(?m)^\s+disabled:\s+true\s*$", row):
            raise IsolationUnavailable("SDK_TOOL_NOT_DISABLED")
    row = _profile_row(text, "session-log-deepseek")
    if not re.search(r"(?m)^\s+enabled:\s+false\s*$", row):
        raise IsolationUnavailable("SDK_SESSION_LOG_UPLOAD_NOT_DISABLED")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def inspect_hardened_profile(docker, workspace, native):
    """Inspect patched composition with a fresh *second* no-network container."""
    patch = Path(__file__).resolve().parent / "phase17/hardened-sdk-minimal.patch.yml"
    if patch.is_symlink() or not patch.is_file() or patch.stat().st_size > 4096:
        raise IsolationUnavailable("SDK_HARDENING_PATCH_UNAVAILABLE")
    raw = patch.read_bytes()
    if (b"- insert:" in raw or b"danger-full-access" in raw
            or any(("- id: " + name).encode() not in raw for name in (*DISABLED_TOOL_ROWS, "session-log-deepseek"))):
        raise IsolationUnavailable("SDK_HARDENING_PATCH_SCOPE_REJECTED")
    target = workspace / "hardened.patch.yml"
    target.write_bytes(raw)
    target.chmod(0o644)
    name = "bf-p17-" + uuid.uuid4().hex[:16]
    command = sdk_bootstrap_command(docker, workspace, name, native)
    command[-5:] = [
        IMAGE, "/opt/harness/" + RUNTIME_BIN, "--profile", "sdk-minimal",
        "--patch", "/workspace/hardened.patch.yml", "--dump-config",
    ]
    try:
        child = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, errors="replace",
            env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"},
            start_new_session=True)
    except OSError:
        raise IsolationUnavailable("SDK_HARDENED_CONTAINER_LAUNCH_FAILED") from None
    try:
        try:
            stdout, _ = child.communicate(timeout=PROBE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate(timeout=5)
            raise IsolationUnavailable("SDK_HARDENED_BOOTSTRAP_TIMED_OUT") from None
        if child.returncode != 0:
            raise IsolationUnavailable("SDK_HARDENED_COMPOSITION_FAILED")
        return validate_hardened_profile(stdout)
    except (OSError, subprocess.SubprocessError):
        raise IsolationUnavailable("SDK_HARDENED_BOOTSTRAP_UNAVAILABLE") from None
    finally:
        if child.poll() is None:
            child.kill()
            try:
                child.communicate(timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass
        try:
            subprocess.run([docker, "rm", "-f", name], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=8, check=False,
                           env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"})
        except (OSError, subprocess.SubprocessError):
            raise IsolationUnavailable("SDK_HARDENED_CLEANUP_UNCONFIRMED") from None



def _rpc_response(child, request_id, *, timeout=20):
    """Read one bounded newline-delimited RPC response without host side effects."""
    watcher = selectors.DefaultSelector()
    watcher.register(child.stdout, selectors.EVENT_READ)
    data = b""
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            events = watcher.select(timeout=min(0.5, deadline - time.monotonic()))
            if not events:
                if child.poll() is not None:
                    raise IsolationUnavailable("SDK_RPC_PROCESS_EXITED")
                continue
            chunk = os.read(child.stdout.fileno(), 4096)
            if not chunk:
                raise IsolationUnavailable("SDK_RPC_STREAM_CLOSED_EXIT_" + str(child.poll() if child.poll() is not None else "ACTIVE"))
            data += chunk
            if len(data) > 16384:
                raise IsolationUnavailable("SDK_RPC_RESPONSE_BUDGET")
            while b"\n" in data:
                line, data = data.split(b"\n", 1)
                try:
                    response = json.loads(line.decode("utf-8", "strict"))
                except (ValueError, UnicodeError):
                    raise IsolationUnavailable("SDK_RPC_MALFORMED_RESPONSE") from None
                if type(response) is not dict:
                    raise IsolationUnavailable("SDK_RPC_MALFORMED_RESPONSE")
                if response.get("id") == request_id:
                    if (response.get("jsonrpc") != "2.0" or "error" in response
                            or type(response.get("result")) is not dict):
                        raise IsolationUnavailable("SDK_RPC_INITIALIZE_REJECTED")
                    return response["result"]
                # Ignore only unrelated bounded server notifications with no
                # request id. Unknown response ids are never treated as proof.
                if response.get("id") is not None:
                    raise IsolationUnavailable("SDK_RPC_UNKNOWN_ID")
        raise IsolationUnavailable("SDK_RPC_INITIALIZE_TIMEOUT")
    finally:
        watcher.close()


def sanitized_boot_diagnostic(raw):
    """Only allowlisted structural failure signatures; never print runtime stderr."""
    if type(raw) is not bytes:
        raise IsolationUnavailable("SDK_DIAGNOSTIC_BYTES_REQUIRED")
    source = raw[:32768].decode("utf-8", "replace").lower()
    signatures = {
        "EROFS": r"\berofs\b|read.only file.system",
        "EACCES": r"\beacces\b|permission denied",
        "ENOSPC": r"\benospc\b|no space left",
        "ENOENT": r"\benoent\b|no such file or directory",
        "ENOMEM": r"\benomem\b|out of memory|heap out of memory",
        "BAD_MODULE": r"cannot find module|module not found|err_module_not_found",
        "NATIVE_BINDING_UNAVAILABLE": r"no usable native binding found",
        "OPAQUE_NATIVE_PRODUCT": r"native binding found for opaque",
        "BAD_EXEC": r"exec format error|permission denied.*exec",
        "BAD_INJECTION": r"inject(?:ion)?(?:s)? (?:not found|missing|required|unavailable)|missing(?: .{0,40})?service",
        "STARTUP_FATAL": r"fatal|boot failed|fail to (?:start|load)|startup failed",
        "INVALID_CONFIG": r"invalid config|schema validation|config validation",
        "UNKNOWN_PATCH": r"patch.*(?:not found|not matched|unknown)",
        "STDIN_EOF": r"stdin.*(?:end|eof|closed)",
        "NODE_EXCEPTION": r"uncaught exception|unhandled rejection|exception in",
        "RESOURCE": r"resource temporarily unavailable|process limit|pids\.max|memory\.max",
    }
    # Expose only published, non-secret, static upstream plugin identities.
    known = (
        "sdk-jsonrpc-server", "sdk-app-startup", "agent-loop", "agent",
        "working-directory", "session-projection", "session-checkpoint-policy",
        "sandbox-policy", "sandbox", "sessions", "llm-deepseek",
        "terminal-bash", "tool-working-directory", "mcp-resources",
    )
    # No inherited credentials exist inside this child. Never disclose raw
    # stderr anyway: scrub absolute paths, URL text, email addresses, control
    # bytes and long opaque tokens; retain a bounded diagnostic excerpt only.
    excerpts = []
    for line in source.splitlines()[:24]:
        if not line.strip():
            continue
        redacted = re.sub(r"https?://\S+|(?:/[^\s:'\"]+)+", "<path>", line)
        redacted = re.sub(r"\b\S+@\S+\.\S+\b", "<email>", redacted)
        redacted = re.sub(r"\b[A-Za-z0-9_+/=-]{40,}\b", "<opaque>", redacted)
        redacted = re.sub(r"[^a-z0-9 _.,:;(){}\[\]?!'\"-]", " ", redacted)
        redacted = re.sub(r"\s+", " ", redacted).strip()[:160]
        if redacted:
            excerpts.append(redacted)
        if len(excerpts) >= 12:
            break
    return {
        "kind": "PHASE18_SANITIZED_SDK_BOOT_DIAGNOSTIC",
        "signature": [k for k,p in signatures.items() if re.search(p, source)],
        "plugin_ids": [key for key in known if key in source],
        "redacted_excerpt": excerpts,
        "stderr_sha256": hashlib.sha256(raw[:32768]).hexdigest(),
        "stderr_bytes_captured": len(raw),
        "truncated": len(raw) > 32768,
        "raw_stderr_disclosed": False,
        "keys_supplied": False,
        "model_calls": 0,
    }


def confirm_hardened_sdk_server(docker, workspace, native):
    """Initialize and shut down the real offline SDK JSON-RPC server, no agent turn."""
    name = "bf-p17-" + uuid.uuid4().hex[:16]
    cmd = sdk_bootstrap_command(docker, workspace, name, native)
    cmd[-5:] = [
        IMAGE, "/opt/harness/" + RUNTIME_BIN, "--profile", "sdk-minimal",
        "--patch", "/workspace/hardened.patch.yml",
    ]
    # SDK JSON-RPC lives on newline-delimited stdio. Docker without -i closes
    # the container's stdin before the host can deliver initialize/shutdown.
    cmd.insert(cmd.index(IMAGE), "-i")
    try:
        child = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0,
            env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"},
            start_new_session=True)
    except OSError:
        raise IsolationUnavailable("SDK_SERVER_LAUNCH_FAILED") from None
    handshake_ok = False
    shutdown_ok = False
    try:
        initial = {
            "jsonrpc": "2.0", "id": "phase17-no-inference-init",
            "method": "initialize",
            "params": {
                "cwd": "/workspace", "provider": "deepseek-official",
                "model": "deepseek-v4-flash"
            },
        }
        child.stdin.write((json.dumps(initial, separators=(",", ":")) + "\n").encode())
        child.stdin.flush()
        result = _rpc_response(child, "phase17-no-inference-init")
        if "serverInfo" in result and type(result["serverInfo"]) is not dict:
            raise IsolationUnavailable("SDK_RPC_SERVER_INFO_INVALID")
        handshake_ok = True
        child.stdin.write((json.dumps({
            "jsonrpc": "2.0", "id": "phase17-shutdown",
            "method": "shutdown"
        }, separators=(",", ":")) + "\n").encode())
        child.stdin.flush()
        try:
            _rpc_response(child, "phase17-shutdown", timeout=8)
            shutdown_ok = True
        except IsolationUnavailable:
            # The server may close its stdio as part of shutdown. Do not
            # classify an unconfirmed response as successful termination.
            raise IsolationUnavailable("SDK_RPC_SHUTDOWN_UNCONFIRMED") from None
        try:
            child.stdin.close()
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            raise IsolationUnavailable("SDK_RPC_EXIT_UNCONFIRMED") from None
        if child.returncode != 0:
            raise IsolationUnavailable("SDK_RPC_EXIT_REJECTED")
    except IsolationUnavailable as failure:
        # Never echo the native runtime's stderr or host paths. Classify a
        # bounded local diagnostic from a child without provider credentials.
        category = "PROFILE"
        try:
            os.set_blocking(child.stderr.fileno(), False)
            detail = os.read(child.stderr.fileno(), 32768)
            diagnostic = sanitized_boot_diagnostic(detail)
            print(json.dumps(diagnostic, sort_keys=True), file=sys.stderr)
            if "NATIVE_BINDING_UNAVAILABLE" in diagnostic["signature"]:
                category = "NATIVE_BINDING"
            elif "EACCES" in diagnostic["signature"]:
                category = "PERMISSION"
            elif "EROFS" in diagnostic["signature"]:
                category = "READ_ONLY_FS"
            elif "ENOSPC" in diagnostic["signature"]:
                category = "NO_SPACE"
            elif "BAD_INJECTION" in diagnostic["signature"]:
                category = "DEPENDENCY"
            elif "ENOMEM" in diagnostic["signature"]:
                category = "MEMORY"
        except (OSError, ValueError):
            pass
        raise IsolationUnavailable(str(failure) + "_DIAGNOSTIC_" + category) from None
    except (OSError, BrokenPipeError, subprocess.SubprocessError):
        raise IsolationUnavailable("SDK_RPC_IO_UNAVAILABLE") from None
    finally:
        if child.poll() is None:
            child.kill()
            try:
                child.wait(timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass
        try:
            subprocess.run([docker, "rm", "-f", name], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=8, check=False,
                           env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"})
        except (OSError, subprocess.SubprocessError):
            raise IsolationUnavailable("SDK_RPC_CLEANUP_UNCONFIRMED") from None
    return {"initialize_confirmed": handshake_ok,
            "shutdown_confirmed": shutdown_ok,
            "model_requests": 0, "agent_turns": 0}


def run_bootstrap(wheel_dir):
    host_gate()
    docker = shutil.which("docker")
    if not docker or not os.path.isabs(docker):
        raise IsolationUnavailable("DOCKER_NOT_AVAILABLE")
    with tempfile.TemporaryDirectory(prefix="bountyforge-p17-sdk-") as temp:
        root = Path(temp)
        os.chmod(root, 0o755)
        native = root / "native"
        provenance = extract_offline_runtime(wheel_dir, native)
        workspace = root / "workspace"
        workspace.mkdir(mode=0o755)
        (workspace / "owned.txt").write_text("owned-development-only\n")
        (workspace / "owned.txt").chmod(0o644)
        name = "bf-p17-" + uuid.uuid4().hex[:16]
        command = sdk_bootstrap_command(docker, workspace, name, native)
        try:
            child = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, errors="replace",
                env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"},
                start_new_session=True,
            )
        except OSError:
            raise IsolationUnavailable("SDK_CONTAINER_LAUNCH_FAILED") from None
        try:
            try:
                output, _ = child.communicate(timeout=PROBE_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate(timeout=5)
                raise IsolationUnavailable("SDK_BOOTSTRAP_TIMED_OUT") from None
            if child.returncode != 0:
                raise IsolationUnavailable("SDK_BOOTSTRAP_REJECTED")
            if (len(output.encode("utf-8")) > 200_000
                    or "sdk-jsonrpc-server" not in output
                    or "persistent-bash" not in output
                    or "danger-full-access" not in output):
                raise IsolationUnavailable("SDK_PROFILE_UNRECOGNIZED")
            output_digest = hashlib.sha256(output.encode()).hexdigest()
        except (OSError, subprocess.SubprocessError):
            raise IsolationUnavailable("SDK_BOOTSTRAP_UNAVAILABLE") from None
        finally:
            if child.poll() is None:
                child.kill()
                try:
                    child.communicate(timeout=5)
                except (OSError, subprocess.SubprocessError):
                    pass
            try:
                subprocess.run([docker, "rm", "-f", name], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=8, check=False,
                               env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"})
            except (OSError, subprocess.SubprocessError):
                raise IsolationUnavailable("SDK_CONTAINER_CLEANUP_UNCONFIRMED") from None
        hardened_digest = inspect_hardened_profile(docker, workspace, native)
        try:
            sdk_session = confirm_hardened_sdk_server(docker, workspace, native)
            sdk_session["admission"] = "MODEL_FREE_RPC_INITIALIZED_ONLY"
        except IsolationUnavailable as exc:
            # Preserve precisely the observed, repeatable *profile startup*
            # refusal as a BLOCKER, not an admitted SDK session. Any other
            # transport, timeout, process or isolation failure remains red.
            expected = "SDK_RPC_STREAM_CLOSED_EXIT_1_DIAGNOSTIC_NATIVE_BINDING"
            if str(exc) != expected:
                raise
            sdk_session = {
                "admission": "SDK_RPC_PROFILE_STARTUP_BLOCKED",
                "failure_code": expected,
                "initialize_confirmed": False,
                "shutdown_confirmed": False,
                "model_requests": 0,
                "agent_turns": 0,
            }
        return {
            "sdk_model_free_rpc_session": sdk_session,
            "sdk_hardened_profile_sha256": hardened_digest,
            "hardened_profile_tools_disabled_by_composition": True,
            "hardened_session_log_uploads_disabled_by_composition": True,
            "hardened_agent_session_launched": False,
            "kind": "PHASE17_PINNED_SDK_NATIVE_BOOTSTRAP",
            "archive_provenance": provenance,
            "sdk_default_profile_sha256": output_digest,
            "runtime_invoked_inside_docker_only": True,
            "sdk_python_api_invoked": False,
            "agent_turns": 0,
            "model_calls": 0,
            "default_profile_unrestricted_shell_present": True,
            "private_source_executed": False,
            "commercial_admission": "NOT_ADMITTED",
            "additional_spending_usd": 0,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-directory", type=Path, required=True)
    parser.add_argument("--admit-model-free-bootstrap", action="store_true")
    args = parser.parse_args(argv)
    if not args.admit_model_free_bootstrap:
        print("EXPLICIT_MODEL_FREE_BOOTSTRAP_REQUIRED", file=sys.stderr)
        return 2
    try:
        result = run_bootstrap(args.wheel_directory)
    except IsolationUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
