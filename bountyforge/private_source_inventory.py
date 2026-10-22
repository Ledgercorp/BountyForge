"""Read-only inspection of two precisely authorized private Python files.

This is a file-identity preflight, not consent, signature, payment, sandbox or
customer-execution admission. Source bytes never leave this function, and no
supplied code or imports are executed.
"""
from __future__ import annotations

import ast
import hashlib
import hmac
import os
import stat
import sys
from pathlib import Path

from bountyforge.paid_scope_review import _approval_shape

MAX_FILE_BYTES = 131072
_NOFOLLOW = os.O_NOFOLLOW | os.O_CLOEXEC
_DIR = os.O_RDONLY | os.O_DIRECTORY | _NOFOLLOW
_FILE = os.O_RDONLY | os.O_NONBLOCK | _NOFOLLOW


class PrivateSourceRejected(ValueError):
    """The private staging tree cannot be used even for scope review."""


def _private_stat(info, *, directory: bool):
    correct_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if (not correct_type or info.st_uid != os.getuid() or info.st_mode & 0o077
            or (not directory and info.st_nlink != 1)):
        raise PrivateSourceRejected('Private staged file identity or permissions rejected')


def _open_private_root(path):
    if not isinstance(path, (str, os.PathLike)):
        raise PrivateSourceRejected('Private staging path invalid')
    root = Path(path)
    if not root.is_absolute() or '..' in root.parts:
        raise PrivateSourceRejected('Private staging path must be absolute')
    # Refuse symlinked parents before opening the private staging directory.
    for component in list(reversed(root.parents)) + [root]:
        if stat.S_ISLNK(component.lstat().st_mode):
            raise PrivateSourceRejected('Symlink ancestor prohibited')
    checkout = Path(__file__).resolve().parents[1]
    if root == checkout or root.is_relative_to(checkout):
        raise PrivateSourceRejected('Private staged source cannot live in public checkout')
    existing = root.lstat()
    _private_stat(existing, directory=True)
    descriptor = os.open(root, _DIR)
    current = os.fstat(descriptor)
    if (existing.st_ino, existing.st_dev) != (current.st_ino, current.st_dev):
        os.close(descriptor)
        raise PrivateSourceRejected('Private staging root changed')
    _private_stat(current, directory=True)
    return descriptor


def _read_regular(fd, path_parts):
    current = os.dup(fd)
    try:
        for name in path_parts[:-1]:
            next_fd = os.open(name, _DIR, dir_fd=current)
            os.close(current)
            current = next_fd
            _private_stat(os.fstat(current), directory=True)
        leaf = os.open(path_parts[-1], _FILE, dir_fd=current)
        try:
            details = os.fstat(leaf)
            _private_stat(details, directory=False)
            if details.st_size < 1 or details.st_size > MAX_FILE_BYTES:
                raise PrivateSourceRejected('Private input size rejected')
            chunks = []
            length = 0
            while True:
                chunk = os.read(leaf, min(16384, MAX_FILE_BYTES + 1 - length))
                if not chunk:
                    break
                chunks.append(chunk)
                length += len(chunk)
                if length > MAX_FILE_BYTES:
                    raise PrivateSourceRejected('Private input exceeds byte budget')
            final = os.fstat(leaf)
            if (details.st_ino, details.st_dev, details.st_size,
                    details.st_mtime_ns, details.st_ctime_ns) != (
                    final.st_ino, final.st_dev, final.st_size,
                    final.st_mtime_ns, final.st_ctime_ns):
                raise PrivateSourceRejected('Private file changed during inspection')
            return b''.join(chunks)
        finally:
            os.close(leaf)
    finally:
        os.close(current)


def _inventory_tree(directory_fd, *, expected_files):
    allowed_dirs = set()
    for path in expected_files:
        elements = path.split('/')
        for idx in range(1, len(elements)):
            allowed_dirs.add('/'.join(elements[:idx]))
    seen = set()
    def scan(fd, prefix=''):
        for name in os.listdir(fd):
            relative = prefix + name
            if relative in allowed_dirs:
                nested_fd = os.open(name, _DIR, dir_fd=fd)
                try:
                    _private_stat(os.fstat(nested_fd), directory=True)
                    scan(nested_fd, relative + '/')
                finally:
                    os.close(nested_fd)
            elif relative in expected_files:
                # File permissions/links checked independently on open.
                seen.add(relative)
            else:
                raise PrivateSourceRejected('Unapproved private staging entry')
    scan(directory_fd)
    if seen != expected_files:
        raise PrivateSourceRejected('Approved private file missing')


def _parse_and_verify_stdlib(data, filename):
    try:
        source = data.decode('utf-8', 'strict')
        if '\x00' in source:
            raise PrivateSourceRejected('NUL in private Python source')
        syntax = ast.parse(source, filename=filename)
    except (SyntaxError, UnicodeError, ValueError) as exc:
        raise PrivateSourceRejected('Private Python syntax or encoding rejected') from None
    for node in ast.walk(syntax):
        modules = []
        if isinstance(node, ast.Import):
            modules.extend(x.name for x in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0:
                raise PrivateSourceRejected('Relative dependency not admitted')
            modules.append(node.module or '')
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ('__import__', 'eval', 'exec', 'compile'):
                raise PrivateSourceRejected('Dynamic source/dependency operation not admitted')
            if (isinstance(node.func, ast.Attribute) and
                    node.func.attr == 'import_module'):
                raise PrivateSourceRejected('Dynamic module loading not admitted')
        if any(module.split('.')[0] not in sys.stdlib_module_names for module in modules):
            raise PrivateSourceRejected('Non-stdlib declared dependency not admitted')
    return len(data)


def inspect_private_source(root, approval_payload):
    """Check *bytes* against an owner-scope payload, returning hashes only.

    Important: the caller must separately authenticate the approval, customer
    rights/consent and fresh payment. Returned evidence is NEVER a capability
    to run, send, save or publish private files. Reopen/revalidate at execution.
    """
    try:
        approved = _approval_shape({'payload': approval_payload,
                                    'signature': '0' * 64})
        # _approval_shape only checks metadata shape, not HMAC identity.
        source_path = approved['source_path']
        test_path = approved['test_path']
        allowed = {source_path, test_path}
        if len(allowed) != 2:
            raise PrivateSourceRejected('Approved paths must be distinct')
        root_fd = _open_private_root(root)
        try:
            _inventory_tree(root_fd, expected_files=allowed)
            source = _read_regular(root_fd, source_path.split('/'))
            tests = _read_regular(root_fd, test_path.split('/'))
        finally:
            os.close(root_fd)
        _parse_and_verify_stdlib(source, source_path)
        _parse_and_verify_stdlib(tests, test_path)
        source_hash = hashlib.sha256(source).hexdigest()
        tests_hash = hashlib.sha256(tests).hexdigest()
        if not (hmac.compare_digest(source_hash, approved['source_sha256'])
                and hmac.compare_digest(tests_hash, approved['tests_sha256'])):
            raise PrivateSourceRejected('Private source hashes do not match approved scope')
        return {
            'schema': 1, 'kind': 'private_source_digest_inspection',
            'source_path': source_path, 'test_path': test_path,
            'source_sha256': source_hash, 'tests_sha256': tests_hash,
            'file_count': 2,
            'source_bytes': len(source), 'test_bytes': len(tests),
            'execution_authorized': False, 'delivery_authorized': False,
            'source_accepted': False, 'rights_verified': False,
            'model_sharing_verified': False, 'dependency_admitted': False,
            'private_worker_admitted': False,
        }
    except PrivateSourceRejected:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise PrivateSourceRejected('Private source inspection unavailable') from None
