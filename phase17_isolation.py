"""Phase 17 model-free whole-process Docker admission probe.

This probe runs ONLY constant audited Python inside the existing digest-pinned
Docker image. It never installs or invokes DeepSeek Harness, a model, or a
customer workload. A pass establishes this runner's observed *probe* boundaries
on this host, not security certification of arbitrary hostile code.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from bountyforge.curated_docker import IMAGE

MEMORY_BYTES = 192 * 1024 * 1024
PIDS_LIMIT = 32
PROBE_TIMEOUT_SECONDS = 35
IMAGE_PIN = "python@sha256:8a00ecb83ed9d0864dfd102a1bdb2067dfa907ceb30bb86d09da9ee558b19590"
# IMAGE_PIN is verified against the existing curated verifier below; a
# mismatch fails closed instead of silently changing the permitted image.

PROBE = r"""
import json, os, pathlib, socket
p=pathlib.Path
status={}
for row in p('/proc/self/status').read_text().splitlines():
    if ':' in row:
        k,v=row.split(':',1)
        status[k]=v.strip()
def read(name):
    return p('/sys/fs/cgroup',name).read_text().strip()
names=[name for _,name in socket.if_nameindex()]
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.settimeout(1)
try:
    s.connect(('1.1.1.1',53))
    network_denied=False
except OSError:
    network_denied=True
finally:
    s.close()
def cannot_write(name):
    try:
        p(name).write_text('blocked')
    except OSError:
        return True
    return False
try:
    p('/tmp/bf-p17-probe').write_text('writable only in tmpfs')
    tmpfs_writable=p('/tmp/bf-p17-probe').read_text()=='writable only in tmpfs'
    p('/tmp/bf-p17-probe').unlink()
except OSError:
    tmpfs_writable=False
try:
    memory=int(read('memory.max'))
    pids=int(read('pids.max'))
    quota,period=map(int,read('cpu.max').split())
except (ValueError,OSError):
    memory,pids,quota,period=-1,-1,-1,0
print(json.dumps({
    'schema':1,
    'owned_canary_read':p('/workspace/owned.txt').read_text()=='owned-development-only\\n',
    'workspace_write_denied':cannot_write('/workspace/owned.txt'),
    'root_write_denied':cannot_write('/probe-host-escape'),
    'docker_socket_absent':not p('/var/run/docker.sock').exists(),
    'tmpfs_writable':tmpfs_writable,
    'nonloopback_network_absent':set(names)=={'lo'},
    'external_connect_denied':network_denied,
    'uid_unprivileged':os.geteuid()==65534,
    'capabilities_dropped':int(status.get('CapEff','-1'),16)==0,
    'no_new_privileges':status.get('NoNewPrivs')=='1',
    'seccomp_enabled':status.get('Seccomp')=='2',
    'memory_limit_enforced':0<memory<=201326592,
    'pids_limit_enforced':0<pids<=32,
    'cpu_limit_enforced':period>0 and 0<quota<=period,
},sort_keys=True))
"""

REQUIRED = (
    "owned_canary_read", "workspace_write_denied", "root_write_denied",
    "docker_socket_absent", "tmpfs_writable", "nonloopback_network_absent",
    "external_connect_denied", "uid_unprivileged", "capabilities_dropped",
    "no_new_privileges", "seccomp_enabled", "memory_limit_enforced",
    "pids_limit_enforced", "cpu_limit_enforced",
)


class IsolationUnavailable(RuntimeError):
    """Fail-closed model-free container boundary was not established."""


def host_gate(environ=None, *, linux=None):
    e = os.environ if environ is None else environ
    is_linux = platform.system() == "Linux" if linux is None else linux
    if not is_linux or any(e.get(k) != v for k, v in (
        ("GITHUB_ACTIONS", "true"),
        ("GITHUB_REPOSITORY", "Ledgercorp/BountyForge"),
        ("RUNNER_OS", "Linux"),
        ("RUNNER_ARCH", "X64"),
        ("BOUNTYFORGE_PHASE17_PROBE_ACK", "1"),
    )):
        raise IsolationUnavailable("STANDARD_PUBLIC_LINUX_RUNNER_REQUIRED")
    if IMAGE != IMAGE_PIN:
        raise IsolationUnavailable("VERIFIER_IMAGE_IDENTITY_CHANGED")


def docker_command(binary, workdir, name):
    if (type(binary) is not str or not binary.startswith("/")
            or Path(binary).name != "docker"
            or not isinstance(workdir, Path) or not workdir.is_absolute()
            or workdir.is_symlink() or not re.fullmatch(r"bf-p17-[0-9a-f]{16}", name)):
        raise IsolationUnavailable("INVALID_PROBE_CONFIGURATION")
    return [
        binary, "run", "--rm", "--pull=never", "--name=" + name,
        "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--security-opt=seccomp=builtin",
        "--pids-limit=32", "--memory=192m", "--memory-swap=192m",
        "--cpus=1", "--user=65534:65534", "--cgroupns=private", "--ipc=none",
        "--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777",
        "--mount=type=bind,source=" + str(workdir) + ",target=/workspace,readonly",
        "--workdir=/workspace", "--env=HOME=/tmp", "--env=PYTHONDONTWRITEBYTECODE=1",
        IMAGE, "python", "-I", "-B", "-c", PROBE,
    ]


def validate_observation(payload):
    if type(payload) is not str or len(payload.encode("utf-8")) > 5000:
        raise IsolationUnavailable("PROBE_RECEIPT_BUDGET")
    try:
        data = json.loads(payload)
    except (ValueError, TypeError):
        raise IsolationUnavailable("INVALID_PROBE_RECEIPT") from None
    if (type(data) is not dict or set(data) != {*REQUIRED, "schema"}
            or type(data["schema"]) is not int or data["schema"] != 1
            or any(data[k] is not True for k in REQUIRED)):
        raise IsolationUnavailable("PROBE_BOUNDARY_NOT_CONFIRMED")
    return {k: data[k] for k in ("schema", *REQUIRED)}


def run_probe():
    host_gate()
    docker = shutil.which("docker")
    if not docker or not os.path.isabs(docker):
        raise IsolationUnavailable("DOCKER_NOT_AVAILABLE")
    with tempfile.TemporaryDirectory(prefix="bountyforge-p17-") as temp:
        workdir = Path(temp)
        (workdir / "owned.txt").write_text("owned-development-only\n")
        os.chmod(workdir / "owned.txt", 0o644)
        os.chmod(workdir, 0o755)
        name = "bf-p17-" + uuid.uuid4().hex[:16]
        command = docker_command(docker, workdir, name)
        child = None
        timed_out = False
        try:
            child = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8",
                errors="replace", env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"},
                start_new_session=True)
            try:
                stdout, _ = child.communicate(timeout=PROBE_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                timed_out = True
                child.kill()
                child.communicate(timeout=5)
                raise IsolationUnavailable("PROBE_TIMED_OUT") from None
            if child.returncode != 0:
                raise IsolationUnavailable("PROBE_CONTAINER_FAILED")
            result = validate_observation(stdout.strip())
        except (OSError, subprocess.SubprocessError):
            raise IsolationUnavailable("DOCKER_PROBE_UNAVAILABLE") from None
        finally:
            if child is not None and child.poll() is None:
                child.kill()
                try:
                    child.communicate(timeout=5)
                except (subprocess.TimeoutExpired, OSError):
                    pass
            # Also remove a container whose client timed out or disconnected.
            # Fixed command and random internal container name, no source input.
            try:
                subprocess.run([docker, "rm", "-f", name], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=8, check=False, env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"})
            except (OSError, subprocess.SubprocessError):
                if timed_out:
                    raise IsolationUnavailable("PROBE_CLEANUP_UNCONFIRMED") from None
        return {
            "kind": "PHASE17_MODEL_FREE_DOCKER_BOUNDARY_PROBE",
            "image": IMAGE,
            "boundary": result,
            "actual_harness_sdk_executed": False,
            "model_calls": 0,
            "private_source_executed": False,
            "commercial_admission": "NOT_ADMITTED",
            "additional_spending_usd": 0,
        }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--admit-model-free-probe", action="store_true")
    args = p.parse_args(argv)
    if not args.admit_model_free_probe:
        print("EXPLICIT_MODEL_FREE_PROBE_REQUIRED", file=sys.stderr)
        return 2
    try:
        receipt = run_probe()
    except IsolationUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
