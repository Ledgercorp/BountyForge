"""Opt-in Linux namespace + chroot + seccomp test runner, never used for GitHub writes.

Requires trusted, locally compiled bf-safe-python launcher from isolation/capdrop.c.
This is a preliminary isolation layer, NOT a third-party-code security certification.
"""
from __future__ import annotations
import hashlib
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

OUTPUT_LIMIT = 12000
MAX_FILES = 80
MAX_TOTAL_SOURCE = 3 * 1024 * 1024

class SandboxUnavailable(RuntimeError): pass


def preflight(source: Path) -> dict:
    """Return exact environmental blockers; fail closed on symlinks and secrets."""
    if Path(source).is_symlink(): raise SandboxUnavailable('Source root symlink prohibited')
    source=Path(source).resolve(strict=True)
    if not source.is_dir(): raise SandboxUnavailable('Not a directory')
    count, size = 0, 0
    for path in source.rglob('*'):
        if path.is_symlink(): raise SandboxUnavailable('Symlinks are prohibited')
        if any(c in {'.git','.env','.venv','node_modules','__pycache__'} for c in path.relative_to(source).parts):
            raise SandboxUnavailable('Hidden credentials, VCS or build tree found')
        if path.is_file():
            if path.stat().st_nlink > 1: raise SandboxUnavailable('Hardlinked source files prohibited')
            count+=1;size+=path.stat().st_size
            if count>MAX_FILES or size>MAX_TOTAL_SOURCE: raise SandboxUnavailable('Source budget exceeded')
        elif not path.is_dir(): raise SandboxUnavailable('Special filesystem nodes prohibited')
    if not (source/'tests').is_dir(): raise SandboxUnavailable('No tests directory')
    return {'files':count,'total_source_bytes':size}


def launch(source: Path, rootfs: Path, launcher: Path, timeout_seconds: int=25) -> dict:
    """No arbitrary commands, network, host VFS or package installs in guest."""
    if not 2<=timeout_seconds<=30: raise ValueError('bounded timeout required')
    source=Path(source).resolve(strict=True)
    rootfs=Path(rootfs).resolve(strict=True)
    launcher=Path(launcher).resolve(strict=True)
    inspection=preflight(source)
    if rootfs==source or rootfs.is_relative_to(source) or source.is_relative_to(rootfs):
        raise SandboxUnavailable('Source and rootfs must not contain one another')
    if not (rootfs/'usr/bin/bf-safe-python').is_file() or not (rootfs/'usr/bin/python3.13').is_file():
        raise SandboxUnavailable('Verified host-compatible rootfs is missing')
    if not shutil.which('unshare'): raise SandboxUnavailable('unshare utility missing')
    if launcher.is_symlink() or not launcher.is_file(): raise SandboxUnavailable('Trusted launcher absent')
    cmd=['unshare','-Urnmpf','--kill-child','/bin/sh',str(launcher),str(rootfs),str(source)]
    started=time.monotonic()
    with tempfile.TemporaryFile() as stdout:
        child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=stdout,stderr=subprocess.STDOUT,start_new_session=True,
                               env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LC_ALL':'C.UTF-8'})
        timed_out=False
        try: child.wait(timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out=True
            try: os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            child.wait()
        stdout.seek(0)
        output=stdout.read(OUTPUT_LIMIT).decode('utf-8','replace')
    return {'status':'pass' if child.returncode==0 and not timed_out and 'Ran ' in output and '\nOK' in output else 'fail',
            'exit_code':child.returncode,'timeout':timed_out,'seconds':round(time.monotonic()-started,3),
            'output':output,'source_preflight':inspection,'runner':'user+net+mount+pid namespaces, chroot, dropped capabilities, seccomp, tmpfs, rlimits',
            'untrusted_execution_certified':False}