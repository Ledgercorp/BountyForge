"""Digest-pinned Docker boundary for ONLY five curated Boltons historical excerpts.

This is not certification for executing arbitrary untrusted third-party repositories.
"""
from __future__ import annotations
import os
import json
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

# Fixed, owned admission probes. Neither target source nor model text can select
# these commands. All pressure stays inside the same existing Docker budgets.
PID_PRESSURE = r"""import json, pathlib, threading
cgroup = pathlib.Path('/sys/fs/cgroup')
assert (cgroup/'pids.max').read_text().strip()=='64'
def events():
    return dict(line.split() for line in (cgroup/'pids.events').read_text().splitlines())
before = int(events()['max'])
stop = threading.Event()
threads = []
denied = False
try:
    # Sleeping threads consume PID slots without a fork bomb or busy loop.
    for _ in range(80):
        thread = threading.Thread(target=stop.wait, args=(5,))
        try:
            thread.start()
        except RuntimeError:
            denied = True
            break
        threads.append(thread)
    current = int((cgroup/'pids.current').read_text())
    increment = int(events()['max']) - before
    assert denied and increment > 0, 'PID exhaustion was not denied by cgroup'
    assert 1 <= current <= 64 and len(threads) < 80, 'PID bound exceeded'
finally:
    stop.set()
    for thread in threads:
        thread.join(timeout=1)
assert not any(thread.is_alive() for thread in threads), 'probe thread leaked'
print(json.dumps({'pid_pressure_enforced': True, 'pid_current_at_denial': current,
                  'pid_denial_events': increment, 'probe_threads': len(threads)}))
"""

CPU_PRESSURE = r"""import json, os, pathlib, time
cgroup = pathlib.Path('/sys/fs/cgroup')
quota, period = map(int, (cgroup/'cpu.max').read_text().split())
assert quota == period, 'CPU quota changed'
def stats():
    return dict((key,int(value)) for key,value in
                (line.split() for line in (cgroup/'cpu.stat').read_text().splitlines()))
before = stats()
start = time.monotonic()
deadline = start + 3
children = []
try:
    # Three finite CPU loops contend for the unchanged one-CPU quota.
    for _ in range(3):
        pid = os.fork()
        if pid == 0:
            while time.monotonic() < deadline:
                pass
            os._exit(0)
        children.append(pid)
finally:
    for pid in children:
        _, status = os.waitpid(pid, 0)
        assert os.waitstatus_to_exitcode(status)==0, 'CPU child failed'
elapsed = time.monotonic() - start
after = stats()
used = (after['usage_usec']-before['usage_usec'])/1_000_000
throttled = after['nr_throttled']-before['nr_throttled']
assert throttled > 0, 'CPU quota did not throttle competing work'
# The tolerance covers period-boundary credit and measurement overhead, not
# another CPU. A busy shared host may reduce usage; it cannot increase quota.
assert used <= elapsed*1.15 + 0.2, 'CPU usage exceeded one-CPU bound'
print(json.dumps({'cpu_pressure_enforced': True, 'cpu_pressure_wall_seconds': round(elapsed,3),
                  'cpu_pressure_used_seconds': round(used,3), 'cpu_throttled_periods': throttled}))
"""

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
    # A marker alone is forgeable. Admit exact trusted tests and source only;
    # changed source must replay through the shared scope/syntax validator.
    from bountyforge.curated_tasks import TASKS, RECEIPT, task_spec, replay
    from bountyforge.drafts import DraftRejected
    try:
        task_id = marker.read_text()
        task = task_spec(task_id)
        trusted = TASKS / task_id
        permitted = {task['file'], 'tests/test_regression.py', MARKER, RECEIPT}
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        if actual - permitted:
            raise CuratedSandboxUnavailable('Unexpected curated file')
        if (root/'tests/test_regression.py').read_bytes() != (trusted/'tests/test_regression.py').read_bytes():
            raise CuratedSandboxUnavailable('Historical acceptance tests changed')
        receipt = root / RECEIPT
        expected = replay(task_id, json.loads(receipt.read_text())) if receipt.exists() else (trusted/task['file']).read_text()
        if (root/task['file']).read_text() != expected:
            raise CuratedSandboxUnavailable('Source does not match validated curated proposal')
    except (OSError, ValueError, SyntaxError, TypeError, KeyError, DraftRejected) as exc:
        raise CuratedSandboxUnavailable('Curated provenance validation failed') from exc
    return root

def _args(root: Path, name: str) -> list[str]:
    return [
        'docker','run','--rm','--name',name,'--pull','never',
        '--network','none','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--pids-limit','64',
        '--memory','256m','--memory-swap','256m','--cpus','1','--user','65534:65534',
        '--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=64m',
        '--ulimit','fsize=1048576:1048576','--ulimit','nofile=64:64',
        '--ulimit','core=0:0','--log-driver','none',
        '--mount',f'type=bind,src={root},dst=/workspace,readonly',
        '--workdir','/workspace','--env','HOME=/tmp',
        '--env','PYTHONPATH=/workspace','--env','PYTHONDONTWRITEBYTECODE=1',
        IMAGE,'python','-B','-m','unittest','discover','-s','tests','-q',
    ]

def _cleanup(name: str, env: dict) -> None:
    try:
        subprocess.run(['docker','rm','-f',name],env=env,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                 timeout=5,check=False)
        # --rm can race an explicit removal after killing the CLI. Confirm
        # absence after the daemon finishes its bounded removal operation.
        deadline = time.monotonic() + 3
        while True:
            absent = subprocess.run(['docker','inspect',name],env=env,
                                    stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                                    timeout=5,check=False,text=True)
            if absent.returncode == 1 and ('No such object: '+name in absent.stderr
                                           or 'No such container: '+name in absent.stderr):
                break
            if absent.returncode != 0:
                raise CuratedSandboxUnavailable('Docker could not establish container absence')
            if time.monotonic() >= deadline:
                raise CuratedSandboxUnavailable('Container cleanup could not be verified')
            time.sleep(0.05)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CuratedSandboxUnavailable('Container cleanup unavailable') from exc


def _execute(root: Path, command: list[str] | None, timeout: int) -> dict:
    name = 'bf-curated-' + uuid.uuid4().hex[:16]
    env = {'PATH':'/usr/local/bin:/usr/bin:/bin', 'HOME':'/nonexistent'}
    args = _args(root, name)
    if command is not None:
        args = args[:args.index(IMAGE)+1] + command
    started = time.monotonic()
    with tempfile.TemporaryFile() as stream:
        try:
            child = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=stream,
                                     stderr=subprocess.STDOUT, env=env, start_new_session=True)
            reason = None
            while child.poll() is None:
                if time.monotonic() - started >= timeout:
                    reason = 'wall_clock_timeout'
                if os.fstat(stream.fileno()).st_size > LOG_BYTES:
                    reason = 'output_budget'
                if reason:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                time.sleep(0.03)
            child.wait(timeout=3)
            if os.fstat(stream.fileno()).st_size > LOG_BYTES:
                reason = 'output_budget'
            stream.seek(0)
            output = stream.read(LOG_BYTES).decode('utf-8','replace')
            return {'passed': child.returncode == 0 and reason is None,
                    'returncode': child.returncode, 'timeout': reason == 'wall_clock_timeout',
                    'error': reason, 'elapsed_seconds': round(time.monotonic()-started,3),
                    'output': output, 'untrusted_execution_certified': False,
                    'sandbox': 'digest_pinned_docker_no_network_read_only_no_privileges'}
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CuratedSandboxUnavailable('Docker execution unavailable: '+type(exc).__name__) from exc
        finally:
            _cleanup(name, env)


def run_curated(root: Path, timeout: int = 12) -> dict:
    if not 2 <= timeout <= 20:
        raise ValueError('Curated timeout must be bounded')
    root = verify_curated(root)
    if shutil.which('docker') is None:
        raise CuratedSandboxUnavailable('Docker unavailable; refuse execution')
    result = _execute(root, None, timeout)
    result['passed'] = (result['passed']
                        and re.search(r'Ran [1-9][0-9]* tests?', result['output']) is not None
                        and result['output'].rstrip().endswith('OK'))
    return result


def verify_runtime_boundary(root: Path, *, synthetic: bool = False) -> dict:
    """Trusted negative controls. Never execute task source during admission."""
    root = verify_synthetic(root) if synthetic else verify_curated(root)
    if shutil.which('docker') is None:
        raise CuratedSandboxUnavailable('Docker unavailable for boundary probe')
    smoke = r"""import errno, os, pathlib, socket, stat
assert os.geteuid()==65534, 'wrong UID'
for key in ('GITHUB_TOKEN','GH_TOKEN','OPENAI_API_KEY','ANTHROPIC_API_KEY','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY'):
    assert key not in os.environ, 'credential inherited'
assert not pathlib.Path('/home/runner').exists(), 'host home mounted'
assert not pathlib.Path('/var/run/docker.sock').exists(), 'Docker socket present'
status = pathlib.Path('/proc/self/status').read_text()
fields = dict(line.split(':',1) for line in status.splitlines() if ':' in line)
assert int(fields['CapEff'].strip(),16)==0, 'capabilities present'
assert fields['NoNewPrivs'].strip()=='1', 'privilege escalation permitted'
assert fields['Seccomp'].strip()=='2', 'seccomp missing'
cgroup = pathlib.Path('/sys/fs/cgroup')
assert int((cgroup/'memory.max').read_text())==268435456, 'memory limit absent'
assert (cgroup/'memory.swap.max').read_text().strip()=='0', 'swap enabled'
assert (cgroup/'pids.max').read_text().strip()=='64', 'PID limit absent'
quota, period = (cgroup/'cpu.max').read_text().split()
assert int(quota)==int(period), 'CPU quota absent'
for address in (('1.1.1.1',443), ('127.0.0.1',18080)):
    try:
        socket.create_connection(address,timeout=1)
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
assert os.statvfs('/tmp').f_blocks*os.statvfs('/tmp').f_frsize <= 64*1024*1024, 'tmpfs unbounded'
path = pathlib.Path('/tmp/bf-noexec')
path.write_text('#!/bin/sh\nexit 0\n')
path.chmod(0o755)
try:
    os.execv(str(path),[str(path)])
except OSError as exc:
    assert exc.errno==errno.EACCES, 'tmpfs execution not denied'
print('BOUNTYFORGE_CURATED_BOUNDARY_OK')
"""
    result = _execute(root, ['python','-I','-c',smoke], 20)
    if not result['passed'] or 'BOUNTYFORGE_CURATED_BOUNDARY_OK' not in result['output']:
        raise CuratedSandboxUnavailable('Boundary controls failed: '+result['output'][-400:])
    timeout = _execute(root, ['python','-I','-c','import time; time.sleep(30)'], 2)
    if not timeout['timeout']:
        raise CuratedSandboxUnavailable('Wall clock restriction failed')
    memory = _execute(root, ['python','-I','-c','x=bytearray(384*1024*1024)'], 10)
    if memory['returncode'] != 137:
        raise CuratedSandboxUnavailable('Memory exhaustion restriction failed')
    output = _execute(root, ['python','-I','-c','print("x"*20000)'], 10)
    if output['error'] != 'output_budget':
        raise CuratedSandboxUnavailable('Output budget restriction failed')
    pressure = {}
    for label, command in (('pid', PID_PRESSURE), ('cpu', CPU_PRESSURE)):
        result = _execute(root, ['python','-I','-c',command], 10)
        if not result['passed']:
            raise CuratedSandboxUnavailable(label.upper()+' pressure restriction failed: '+result['output'][-400:])
        try:
            observed = json.loads(result['output'])
            if observed.get(label+'_pressure_enforced') is not True:
                raise ValueError('missing pressure proof')
        except (ValueError, TypeError, AttributeError) as exc:
            raise CuratedSandboxUnavailable(label.upper()+' pressure evidence missing') from exc
        pressure.update(observed)
    return {'network_denied':True, 'loopback_inference_unreachable':True,
            'source_writes_denied':True,'root_writes_denied':True,'secrets_absent':True,
            'uid_unprivileged':True,'capabilities_empty':True,'no_new_privileges':True,
            'seccomp_active':True,'memory_limit_enforced':True,'swap_disabled':True,
            'cpu_quota_verified':True,'pid_limit_verified':True,'tmpfs_bounded_noexec':True,
            'wall_clock_enforced':True,'cleanup_verified':True,'output_bounded':True,
            'docker_socket_absent':True,'image_digest':IMAGE.split('@')[1],
            'untrusted_execution_certified':False, **pressure}


def verify_synthetic(root: Path) -> Path:
    """Admit only the fixed owned two-line fixture catalog and validated edits."""
    from bountyforge.worker import FIXTURE_MARKER
    from bountyforge.lineedit import stage_lines
    from bountyforge.drafts import DraftRejected
    import hashlib
    if Path(root).is_symlink(): raise CuratedSandboxUnavailable('Symlinked synthetic root')
    root=Path(root).resolve(strict=True)
    actual=set()
    for path in root.rglob('*'):
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            raise CuratedSandboxUnavailable('Unsafe synthetic object')
        if path.is_file():
            if path.stat().st_nlink!=1 or path.stat().st_size>12000:
                raise CuratedSandboxUnavailable('Unsafe synthetic source')
            actual.add(path.relative_to(root).as_posix())
    catalog=Path(__file__).resolve().parents[1]/'fixtures/controlled'
    for name in ('addition','multiply','increment'):
        trusted=catalog/name
        expected_files={p.relative_to(trusted).as_posix() for p in trusted.rglob('*') if p.is_file()}
        if actual!=expected_files:
            continue
        if any((root/name).read_bytes()!=(trusted/name).read_bytes() for name in expected_files-{'calc.py'}):
            continue
        if ((root/FIXTURE_MARKER).read_bytes()!=(trusted/FIXTURE_MARKER).read_bytes()
                or (root/'tests/test_calc.py').read_bytes()!=(trusted/'tests/test_calc.py').read_bytes()):
            continue
        original=(trusted/'calc.py').read_text();candidate=(root/'calc.py').read_text()
        if candidate==original: return root
        rows=candidate.splitlines(True);old=original.splitlines(True)
        if not rows or rows[0]!=old[0] or len(old)!=2: continue
        raw=json.dumps({'changes':[{'line':2,'new':''.join(rows[1:]).rstrip('\n')}]})
        try:
            staged=stage_lines(raw,trusted,'calc.py',[2],hashlib.sha256(original.encode()).hexdigest())
        except DraftRejected:
            continue
        if staged['files'][0]['content']==candidate: return root
    raise CuratedSandboxUnavailable('Not an admitted owned fixture or scoped candidate')


def run_synthetic(root: Path, timeout: int = 12) -> dict:
    if not 2<=timeout<=20: raise ValueError('Synthetic timeout must be bounded')
    root=verify_synthetic(root)
    if shutil.which('docker') is None: raise CuratedSandboxUnavailable('Docker unavailable')
    result=_execute(root,None,timeout)
    result['passed']=(result['passed'] and re.search(r'Ran [1-9][0-9]* tests?',result['output']) is not None
                      and result['output'].rstrip().endswith('OK'))
    return {**result,'exit_code':result['returncode'],'seconds':result['elapsed_seconds']}
