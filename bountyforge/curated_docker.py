"""Digest-pinned Docker boundary for ONLY five curated Boltons historical excerpts.

This is not certification for executing arbitrary untrusted third-party repositories.
"""
from __future__ import annotations
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

IMAGE = 'python@sha256:8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590'
MARKER = '.bountyforge-curated-boltons'
APPROVED_IDS = frozenset({'454', '459', '460', '475', '524'})
MAX_FILES, MAX_BYTES, LOG_BYTES = 15, 400_000, 6000

class CuratedSandboxUnavailable(RuntimeError):
    pass

def verify_curated(root: Path) -> Path:
    if Path(root).is_symlink():
        raise CuratedSandboxUnavailable('Symlinked source root')
    root = Path(root).resolve(strict=True)
    marker = root / MARKER
    if (not root.is_dir() or not marker.is_file() or marker.is_symlink()
            or marker.read_text() not in APPROVED_IDS):
        raise CuratedSandboxUnavailable('Missing trusted curated task marker')
    if not (root / 'tests').is_dir():
        raise CuratedSandboxUnavailable('Missing deterministic tests')
    count = size = 0
    for path in root.rglob('*'):
        if path.is_symlink():
            raise CuratedSandboxUnavailable('Source symlinks rejected')
        if any(part in {'.git','.github','.env','.venv','__pycache__','node_modules'}
               for part in path.relative_to(root).parts):
            raise CuratedSandboxUnavailable('Disallowed source tree content')
        if path.is_file():
            stat = path.stat()
            if stat.st_nlink != 1:
                raise CuratedSandboxUnavailable('Hardlinked source rejected')
            count += 1
            size += stat.st_size
            if count > MAX_FILES or size > MAX_BYTES:
                raise CuratedSandboxUnavailable('Source budget exceeded')
        elif not path.is_dir():
            raise CuratedSandboxUnavailable('Special filesystem object rejected')
    return root

def _args(root: Path, name: str) -> list[str]:
    return [
        'docker','run','--rm','--name',name,'--pull','never',
        '--network','none','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--pids-limit','64',
        '--memory','256m','--cpus','1','--user','65534:65534',
        '--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=64m',
        '--mount',f'type=bind,src={root},dst=/workspace,readonly',
        '--workdir','/workspace','--env','HOME=/tmp',
        '--env','PYTHONPATH=/workspace','--env','PYTHONDONTWRITEBYTECODE=1',
        IMAGE,'python','-B','-m','unittest','discover','-s','tests','-q',
    ]

def _cleanup(name: str, env: dict) -> None:
    try:
        subprocess.run(['docker','rm','-f',name],env=env,stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,timeout=5,check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass

def run_curated(root: Path, timeout: int = 12) -> dict:
    if not 2 <= timeout <= 20:
        raise ValueError('Curated timeout must be bounded')
    root = verify_curated(root)
    if shutil.which('docker') is None:
        raise CuratedSandboxUnavailable('Docker unavailable; refuse execution')
    name = 'bf-curated-' + uuid.uuid4().hex[:16]
    env = {'PATH':'/usr/local/bin:/usr/bin:/bin', 'HOME':'/nonexistent'}
    started = time.monotonic()
    with tempfile.TemporaryFile() as stream:
        try:
            child = subprocess.Popen(_args(root,name),stdin=subprocess.DEVNULL,
                                     stdout=stream,stderr=subprocess.STDOUT,
                                     env=env,start_new_session=True)
            try:
                child.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid,signal.SIGKILL)
                child.wait()
            stream.seek(0)
            output = stream.read(LOG_BYTES).decode('utf-8','replace')
            passed = (child.returncode == 0 and not timed_out
                      and re.search(r'Ran [1-9][0-9]* tests?',output) is not None
                      and output.rstrip().endswith('OK'))
            return {'passed':passed,'returncode':child.returncode,
                    'timeout':timed_out,'elapsed_seconds':round(time.monotonic()-started,3),
                    'output':output,
                    'sandbox':'digest_pinned_docker_no_network_read_only_no_privileges',
                    'untrusted_execution_certified':False}
        except OSError as exc:
            raise CuratedSandboxUnavailable('Docker launch unavailable: '+type(exc).__name__) from exc
        finally:
            _cleanup(name,env)

def verify_runtime_boundary(root: Path) -> dict:
    """Run trusted inline negative tests before admitting curated excerpts."""
    root = verify_curated(root)
    if shutil.which('docker') is None:
        raise CuratedSandboxUnavailable('Docker unavailable for boundary probe')
    name = 'bf-curated-probe-' + uuid.uuid4().hex[:12]
    smoke = """import os, pathlib, socket
assert os.geteuid()==65534, 'wrong UID'
for key in ('GITHUB_TOKEN','GH_TOKEN','OPENAI_API_KEY','ANTHROPIC_API_KEY'):
    assert key not in os.environ, 'credential inherited'
assert not pathlib.Path('/home/runner').exists(), 'host home mounted'
try:
    socket.create_connection(('1.1.1.1',443),timeout=1)
except OSError:
    pass
else:
    raise AssertionError('network available')
for name in ('/workspace/bf-write-probe','/bf-root-write-probe'):
    try:
        pathlib.Path(name).write_text('unsafe')
    except OSError:
        pass
    else:
        raise AssertionError('writable sandbox: '+name)
print('BOUNTYFORGE_CURATED_BOUNDARY_OK')
"""
    command = _args(root,name)
    command = command[:command.index(IMAGE)+1] + ['python','-c',smoke]
    env = {'PATH':'/usr/local/bin:/usr/bin:/bin', 'HOME':'/nonexistent'}
    try:
        result = subprocess.run(command,stdin=subprocess.DEVNULL,
                                capture_output=True,text=True,timeout=20,env=env)
        if result.returncode != 0 or 'BOUNTYFORGE_CURATED_BOUNDARY_OK' not in result.stdout:
            raise CuratedSandboxUnavailable('Container boundary probe failed: '+result.stderr[-240:])
        return {'network_denied':True,'source_writes_denied':True,
                'root_writes_denied':True,'secrets_absent':True,
                'uid_unprivileged':True,'image_digest':IMAGE.split('@')[1],
                'untrusted_execution_certified':False}
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise CuratedSandboxUnavailable('Container probe unavailable: '+type(exc).__name__) from exc
    finally:
        _cleanup(name,env)
