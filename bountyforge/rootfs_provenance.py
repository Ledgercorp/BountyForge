"""Read-only rootfs provenance inventory, with externally pinned SHA-256.

Nothing in this module launches code, grants private execution privileges,
certifies a sandbox, or decides that a runtime is safe for customer source.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import stat
from pathlib import Path

_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_ENTRIES = 20000
_TOP = frozenset({'usr', 'lib', 'lib64', 'work', 'tmp'})
_REQUIRE_DIRS = frozenset({'usr', 'usr/bin', 'usr/lib', 'lib', 'lib64',
                           'work', 'tmp'})
_REQUIRE_FILES = frozenset({'usr/bin/bf-safe-python', 'usr/bin/python3.13'})
_PIN = re.compile(r'[0-9a-f]{64}\Z')


class RootfsProvenanceRejected(ValueError):
    """A candidate runtime cannot be independently pinned for review."""


def _component(name: str) -> None:
    if (not name or name in ('.', '..') or '/' in name or '\\' in name
            or len(name.encode('utf-8', errors='surrogatepass')) > 255
            or any(ord(char) < 32 or ord(char) == 127 for char in name)):
        raise RootfsProvenanceRejected('Unsupported rootfs entry name')


def _safe_dir(st, *, readonly: bool) -> None:
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
            or st.st_mode & (stat.S_ISUID | stat.S_ISGID)
            or st.st_mode & 0o022 or (readonly and st.st_mode & 0o200)):
        raise RootfsProvenanceRejected('Rootfs directory identity or write access rejected')


def _open_root(root):
    if not isinstance(root, (str, os.PathLike)):
        raise RootfsProvenanceRejected('Rootfs path invalid')
    path = Path(root)
    if not path.is_absolute() or '..' in path.parts:
        raise RootfsProvenanceRejected('Rootfs path must be absolute and canonical')
    current = os.open('/', _DIR)
    try:
        for name in path.parts[1:]:
            _component(name)
            following = os.open(name, _DIR, dir_fd=current)
            os.close(current)
            current = following
        _safe_dir(os.fstat(current), readonly=False)
        return current
    except BaseException:
        os.close(current)
        raise


def _hash_regular(parent_fd, name, before):
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
            or before.st_nlink != 1
            or before.st_mode & (stat.S_ISUID | stat.S_ISGID | 0o222)
            or not 0 < before.st_size <= MAX_FILE_BYTES):
        raise RootfsProvenanceRejected('Untrusted or writable runtime file')
    fd = os.open(name, _FILE, dir_fd=parent_fd)
    try:
        first = os.fstat(fd)
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
             before.st_ctime_ns, before.st_mode)
            != (first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns,
                first.st_ctime_ns, first.st_mode)):
            raise RootfsProvenanceRejected('Rootfs file changed before read')
        remaining = first.st_size
        digest = hashlib.sha256()
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                raise RootfsProvenanceRejected('Rootfs file shortened during read')
            digest.update(chunk)
            remaining -= len(chunk)
        # An append or concurrent content/mode replacement is not acceptable.
        if os.read(fd, 1):
            raise RootfsProvenanceRejected('Rootfs file grew during read')
        last = os.fstat(fd)
        if ((first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns,
             first.st_ctime_ns, first.st_mode)
            != (last.st_dev, last.st_ino, last.st_size, last.st_mtime_ns,
                last.st_ctime_ns, last.st_mode)):
            raise RootfsProvenanceRejected('Rootfs file changed during read')
        return digest.hexdigest()
    finally:
        os.close(fd)


def inventory_rootfs(root):
    """Hash an owner-owned nonwritable candidate rootfs, no execution.

    Repeated inventory validates current bytes only; it does not prevent
    later mutation, certify provenance, or prove sandbox policy/kernel safety.
    """
    try:
        fd = _open_root(root)
        try:
            entries = []
            files = set()
            directories = set()
            total_bytes = 0

            def visit(dirfd, prefix=''):
                nonlocal total_bytes
                if len(entries) > MAX_ENTRIES:
                    raise RootfsProvenanceRejected('Rootfs entry count exceeded')
                directory_before = os.fstat(dirfd)
                names = os.listdir(dirfd)
                if len(names) + len(entries) > MAX_ENTRIES:
                    raise RootfsProvenanceRejected('Rootfs entry count exceeded')
                for name in sorted(names):
                    _component(name)
                    relative = prefix + name
                    if not prefix and name not in _TOP:
                        raise RootfsProvenanceRejected('Unknown rootfs top-level entry')
                    info = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode):
                        _safe_dir(info, readonly=relative.split('/')[0] not in ('tmp','work'))
                        child = os.open(name, _DIR, dir_fd=dirfd)
                        try:
                            follow = os.fstat(child)
                            if ((info.st_dev, info.st_ino, info.st_mode)
                                != (follow.st_dev, follow.st_ino, follow.st_mode)):
                                raise RootfsProvenanceRejected('Rootfs directory changed')
                            directories.add(relative)
                            entries.append(['d', relative, info.st_mode & 0o777])
                            visit(child, relative + '/')
                            tail = os.fstat(child)
                            if ((follow.st_dev, follow.st_ino, follow.st_mode,
                                 follow.st_mtime_ns, follow.st_ctime_ns)
                                != (tail.st_dev, tail.st_ino, tail.st_mode,
                                    tail.st_mtime_ns, tail.st_ctime_ns)):
                                raise RootfsProvenanceRejected('Rootfs directory changed during scan')
                        finally:
                            os.close(child)
                    elif stat.S_ISREG(info.st_mode):
                        if relative.split('/')[0] in ('tmp','work'):
                            raise RootfsProvenanceRejected('Writable work directory contains rootfs input')
                        if relative in _REQUIRE_FILES and not info.st_mode & 0o111:
                            raise RootfsProvenanceRejected('Required trusted binary not executable')
                        total_bytes += info.st_size
                        if total_bytes > MAX_TOTAL_BYTES:
                            raise RootfsProvenanceRejected('Rootfs total bytes exceeded')
                        digest = _hash_regular(dirfd, name, info)
                        files.add(relative)
                        entries.append(['f', relative, info.st_mode & 0o777, info.st_size, digest])
                    else:
                        raise RootfsProvenanceRejected('Rootfs links and special nodes prohibited')
                    if len(entries) > MAX_ENTRIES:
                        raise RootfsProvenanceRejected('Rootfs entry count exceeded')
                directory_after = os.fstat(dirfd)
                if ((directory_before.st_dev, directory_before.st_ino,
                     directory_before.st_mode, directory_before.st_mtime_ns,
                     directory_before.st_ctime_ns)
                    != (directory_after.st_dev, directory_after.st_ino,
                        directory_after.st_mode, directory_after.st_mtime_ns,
                        directory_after.st_ctime_ns)):
                    raise RootfsProvenanceRejected('Rootfs directory modified during scan')

            visit(fd)
            if not _REQUIRE_DIRS.issubset(directories) or not _REQUIRE_FILES.issubset(files):
                raise RootfsProvenanceRejected('Required rootfs runtime files or directories missing')
            raw = json.dumps({'schema': 1, 'entries': sorted(entries)},
                             sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
            return {
                'kind': 'rootfs_file_provenance_inventory',
                'schema': 1, 'tree_sha256': hashlib.sha256(raw).hexdigest(),
                'file_count': len(files), 'directory_count': len(directories),
                'total_file_bytes': total_bytes,
                'producer_identity_verified': False,
                'kernel_isolation_verified': False,
                'rootfs_execution_admitted': False,
                'execution_authorized': False,
                'commercial_source_admitted': False,
            }
        finally:
            os.close(fd)
    except RootfsProvenanceRejected:
        raise
    except (OSError, TypeError, ValueError, OverflowError):
        raise RootfsProvenanceRejected('Rootfs inventory unavailable or untrusted') from None


def verify_rootfs_pin(root, expected_sha256):
    """Compare a fresh rootfs inventory against a caller's independent pin."""
    if not isinstance(expected_sha256, str) or not _PIN.fullmatch(expected_sha256):
        raise RootfsProvenanceRejected('Independently trusted rootfs pin required')
    evidence = inventory_rootfs(root)
    if not hmac.compare_digest(evidence['tree_sha256'], expected_sha256):
        raise RootfsProvenanceRejected('Runtime rootfs does not match independent pin')
    return {**evidence, 'digest_matches_pin': True,
            'producer_identity_verified': False,
            'rootfs_execution_admitted': False, 'execution_authorized': False}
