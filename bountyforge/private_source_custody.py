"""Private, non-executable custody snapshot of an owned/signed review.

Never executes source, imports it, sends it to models, signs a customer contract,
or authorizes delivery. No production storage or customer source is configured.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from bountyforge.private_source_inventory import (
    PrivateSourceRejected, _DIR, _NOFOLLOW, _open_private_root,
    _inventory_tree, _read_regular, _parse_and_verify_stdlib,
    inspect_recorded_private_scope
)
from bountyforge.paid_scope_review import PaidScopeReview, _approval_shape, _canonical

_RECEIPT = 'snapshot.json'
_FLAGS = os.O_CREAT | os.O_EXCL | os.O_WRONLY | _NOFOLLOW


def _read_pair(root, payload):
    source_path, test_path = payload['source_path'], payload['test_path']
    fd = _open_private_root(root)
    try:
        _inventory_tree(fd, expected_files={source_path, test_path})
        source = _read_regular(fd, source_path.split('/'))
        tests = _read_regular(fd, test_path.split('/'))
    finally:
        os.close(fd)
    _parse_and_verify_stdlib(source, source_path)
    _parse_and_verify_stdlib(tests, test_path)
    if not (hmac.compare_digest(hashlib.sha256(source).hexdigest(), payload['source_sha256'])
            and hmac.compare_digest(hashlib.sha256(tests).hexdigest(), payload['tests_sha256'])):
        raise PrivateSourceRejected('Private custody bytes do not match approved scope')
    return source, tests


def _manifest(payload, source, tests):
    return {
        'schema': 1,
        'kind': 'private_review_custody_receipt',
        'scope_sha256': hashlib.sha256(_canonical(payload)).hexdigest(),
        'source_path': payload['source_path'],
        'source_sha256': hashlib.sha256(source).hexdigest(),
        'source_bytes': len(source),
        'test_path': payload['test_path'],
        'tests_sha256': hashlib.sha256(tests).hexdigest(),
        'test_bytes': len(tests),
        'execution_authorized': False,
        'delivery_authorized': False,
    }


def _write_file(root_fd, relative, data):
    current = os.dup(root_fd)
    try:
        for component in relative.split('/')[:-1]:
            try:
                os.mkdir(component, 0o700, dir_fd=current)
            except FileExistsError:
                pass
            child = os.open(component, _DIR, dir_fd=current)
            os.close(current)
            current = child
            st = os.fstat(current)
            if st.st_uid != os.getuid() or st.st_mode & 0o077:
                raise PrivateSourceRejected('Custody directory permissions rejected')
        fd = os.open(relative.split('/')[-1], _FLAGS, 0o600, dir_fd=current)
        try:
            os.fchmod(fd, 0o600)
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise PrivateSourceRejected('Custody write did not advance')
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(current)
    finally:
        os.close(current)


def _write_snapshot(vault_fd, pending, payload, source, tests):
    os.mkdir(pending, 0o700, dir_fd=vault_fd)
    snapshot_fd = os.open(pending, _DIR, dir_fd=vault_fd)
    try:
        _write_file(snapshot_fd, payload['source_path'], source)
        _write_file(snapshot_fd, payload['test_path'], tests)
        raw = _canonical(_manifest(payload, source, tests))
        _write_file(snapshot_fd, _RECEIPT, raw)
        os.fsync(snapshot_fd)
    finally:
        os.close(snapshot_fd)
    os.fsync(vault_fd)
    return hashlib.sha256(raw).hexdigest()


def _remove_pending(vault_fd, pending, paths):
    """Best-effort bounded cleanup; never chase links from the private vault."""
    try:
        root_fd = os.open(pending, _DIR, dir_fd=vault_fd)
    except FileNotFoundError:
        return
    try:
        for relative in list(paths) + [_RECEIPT]:
            current = os.dup(root_fd)
            try:
                for component in relative.split('/')[:-1]:
                    child = os.open(component, _DIR, dir_fd=current)
                    os.close(current)
                    current = child
                try:
                    os.unlink(relative.split('/')[-1], dir_fd=current)
                except FileNotFoundError:
                    pass
            except FileNotFoundError:
                pass
            finally:
                os.close(current)
        dirs = sorted({('/'.join(p.split('/')[:i]))
                       for p in paths for i in range(1, len(p.split('/')))},
                      key=lambda p: (-p.count('/'), -len(p)))
        for subpath in dirs:
            current = os.dup(root_fd)
            try:
                pieces = subpath.split('/')
                for component in pieces[:-1]:
                    child = os.open(component, _DIR, dir_fd=current)
                    os.close(current)
                    current = child
                try:
                    os.rmdir(pieces[-1], dir_fd=current)
                except FileNotFoundError:
                    pass
            except FileNotFoundError:
                pass
            finally:
                os.close(current)
    finally:
        os.close(root_fd)
    os.rmdir(pending, dir_fd=vault_fd)


def verify_private_snapshot(snapshot_root, approval_payload):
    """Verify an inert sealed copy against externally trusted scope digests."""
    try:
        payload = _approval_shape({'payload': approval_payload, 'signature': '0' * 64})
        root = Path(snapshot_root)
        import re
        if re.fullmatch(r'sealed-[0-9a-f]{32}', root.name) is None:
            raise PrivateSourceRejected('Only completed custody snapshots can be verified')
        fd = _open_private_root(root)
        try:
            _inventory_tree(fd, expected_files={payload['source_path'],
                                                payload['test_path'], _RECEIPT})
            source = _read_regular(fd, payload['source_path'].split('/'))
            tests = _read_regular(fd, payload['test_path'].split('/'))
            raw = _read_regular(fd, [_RECEIPT])
        finally:
            os.close(fd)
        _parse_and_verify_stdlib(source, payload['source_path'])
        _parse_and_verify_stdlib(tests, payload['test_path'])
        expected = _canonical(_manifest(payload, source, tests))
        if (not hmac.compare_digest(hashlib.sha256(source).hexdigest(), payload['source_sha256'])
                or not hmac.compare_digest(hashlib.sha256(tests).hexdigest(), payload['tests_sha256'])
                or not hmac.compare_digest(raw, expected)):
            raise PrivateSourceRejected('Custody receipt or private bytes changed')
        return {
            'kind': 'private_custody_snapshot_verified',
            'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
            'source_sha256': payload['source_sha256'],
            'tests_sha256': payload['tests_sha256'],
            'hashes_verified': True,
            'execution_authorized': False,
            'delivery_authorized': False,
            'source_accepted': False,
            'model_sharing_verified': False,
            'fresh_payment_verified': False,
            'private_worker_admitted': False
        }
    except PrivateSourceRejected:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise PrivateSourceRejected('Private custody snapshot verification unavailable') from None


def create_review_snapshot(source_root, vault_root, review, session, *, token,
                           expected_fence, now):
    """Persist an inert private copy only while a trusted signed review lease lives.

    Never exports the file bytes or uses them for execution/inference. No actual
    owner/customer approvals, payment freshness or deployment are inferred.
    """
    try:
        if type(review) is not PaidScopeReview:
            raise PrivateSourceRejected('Trusted private review journal required')
        source_path = Path(source_root)
        vault_path = Path(vault_root)
        if (not source_path.is_absolute() or not vault_path.is_absolute()
                or source_path == vault_path
                or source_path.is_relative_to(vault_path)
                or vault_path.is_relative_to(source_path)):
            raise PrivateSourceRejected('Source and private vault must be separate')
        state, revision = review._read()
        if revision is None:
            raise PrivateSourceRejected('Missing durable review revision')
        # This read-only function checks the HMAC, lease, historical review,
        # exact source and test bytes and a stable review revision.
        inspection = inspect_recorded_private_scope(
            source_root, review, session, token=token,
            expected_fence=expected_fence, now=now)
        state_now, revision_now = review._read()
        if revision_now != revision:
            raise PrivateSourceRejected('Review changed before custody capture')
        plan = review._plan(state_now, session)
        payload = _approval_shape(plan['approval'])
        source, tests = _read_pair(source_root, payload)
        if (not hmac.compare_digest(hashlib.sha256(source).hexdigest(), inspection['source_sha256'])
                or not hmac.compare_digest(hashlib.sha256(tests).hexdigest(), inspection['tests_sha256'])):
            raise PrivateSourceRejected('Reviewed source changed before custody')
        vault_fd = _open_private_root(vault_root)
        try:
            ident = secrets.token_hex(16)
            pending = '.pending-' + ident
            complete = 'sealed-' + ident
            wrote = False
            try:
                digest = _write_snapshot(vault_fd, pending, payload, source, tests)
                # Refuse revoked/expired leases and concurrent journal writes
                # before publishing the newly captured private snapshot.
                again = inspect_recorded_private_scope(
                    source_root, review, session, token=token,
                    expected_fence=expected_fence, now=now)
                _, revision_after = review._read()
                if (revision_after != revision
                        or again['source_sha256'] != payload['source_sha256']
                        or again['tests_sha256'] != payload['tests_sha256']):
                    raise PrivateSourceRejected('Review changed during custody capture')
                try:
                    os.stat(complete, dir_fd=vault_fd, follow_symlinks=False)
                    raise PrivateSourceRejected('Custody destination collision')
                except FileNotFoundError:
                    pass
                os.rename(pending, complete, src_dir_fd=vault_fd, dst_dir_fd=vault_fd)
                wrote = True
                os.fsync(vault_fd)
                return {
                    'kind': 'private_custody_snapshot',
                    'snapshot_name': complete,
                    'snapshot_sha256': digest,
                    'source_sha256': payload['source_sha256'],
                    'tests_sha256': payload['tests_sha256'],
                    'execution_authorized': False,
                    'source_accepted': False,
                    'delivery_authorized': False,
                    'model_sharing_verified': False,
                    'fresh_payment_verified': False,
                    'private_worker_admitted': False
                }
            finally:
                if not wrote:
                    try:
                        _remove_pending(vault_fd, pending, (payload['source_path'],
                                                            payload['test_path']))
                    except OSError:
                        # Never publish a partially constructed custody copy.
                        # Remnant .pending-* is not a valid sealed snapshot.
                        pass
        finally:
            os.close(vault_fd)
    except PrivateSourceRejected:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise PrivateSourceRejected('Private custody capture unavailable') from None
