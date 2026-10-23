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
        return {
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
