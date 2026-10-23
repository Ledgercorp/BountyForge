"""Inactive, fixed owned patch package. No customer input or general executor."""
import difflib
import hashlib
import os
from pathlib import Path
import stat

from bountyforge.phase7_owned_demo import (
    SOURCE, PATCHED, canonical, replay, require_private_directory, SyntheticBlocked,
)

NOTICE = 'owned-only; not a live offer'
PACKAGE_NAME = 'owned-review-package'
MAX_FILE_BYTES = 32768
MAX_PACKAGE_BYTES = 65536


class PackageBlocked(ValueError):
    """An owned-only package boundary or integrity check failed."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


INSTRUCTIONS = b'''OWNED-ONLY; NOT A LIVE OFFER. Launch and delivery remain disabled.
This is the manually authored Phase7 owned arithmetic repair, not an AI patch.
Only the exact owned fixture ran in the local deterministic four-vector replay.
No customer environment, dependencies, test suite, deployment, or integration ran.

Future customer-run review instructions (no commands selected or executed here):
1. Keep a customer-controlled backup and isolated review checkout.
2. Confirm the before SHA-256 matches the intended original file exactly.
3. Inspect the full unified diff and after SHA-256; decline mismatched scope.
4. Have the customer apply the reviewed diff in their own environment.
5. Have the customer choose and run their existing trusted tests and review all
   results, dependencies, runtime differences, edge cases, and security behavior.
6. Customer decides whether to keep or revert the patch. No deployment is made.
These steps describe a future review workflow; they do not authorize intake,
execution, disclosure to a model provider, delivery, a guarantee, or a sale.
'''


def _expected_files():
    patch = ''.join(difflib.unified_diff(
        SOURCE.decode().splitlines(keepends=True), PATCHED.decode().splitlines(keepends=True),
        fromfile='a/owned_total.py', tofile='b/owned_total.py', lineterm='\n')).encode()
    files = {'owned_before.py': SOURCE, 'owned_after.py': PATCHED,
             'repair.patch': patch, 'REVIEW.txt': INSTRUCTIONS}
    review = {
        'schema': 1, 'kind': 'inactive_owned_python_patch_review', 'notice': NOTICE,
        'owned_only': True, 'live_offer': False, 'launch_enabled': False,
        'delivery_enabled': False, 'customer_intake_enabled': False,
        'authorship': 'manually_authored_phase7_owned_repair',
        'before_sha256': _sha(SOURCE), 'after_sha256': _sha(PATCHED),
        'diff_sha256': _sha(patch), 'model_calls': 0, 'customer_data_received': False,
        'verification': {'owned_replay': replay(SOURCE, PATCHED),
                         'customer_environment_tested': False,
                         'customer_tests_run': False, 'ai_repair_evaluated': False,
                         'limits': ['Exact owned arithmetic fixture only; four deterministic vectors.',
                                    'No customer code, tests, dependencies, environment, or integration verified.',
                                    'No guarantee of correctness, security, or generalization.']},
        'future_scope': {
            'supported': ['Python: one small file and one function, standard library only.',
                          'Deterministic minimal reproduction with explicitly authorized rights.'],
            'unsupported': ['Arbitrary customer execution or customer-selected commands.',
                            'Multi-file/dependency/network/secret/data access, nondeterministic failures.',
                            'Production deployment, security certification, guarantees.'],
            'required_before_any_future_intake': [
                'Explicit ownership or permission to review and modify submitted code.',
                'Separate explicit permission for model sharing naming provider, scope and retention.',
                'Owner approval of privacy, deletion, failure/refund terms and launch controls.'],
        },
        'policy': {
            'status': 'proposal_for_owner_review_not_a_contract',
            'privacy': 'No customer intake or sharing now. Future intake must minimize data and exclude secrets.',
            'retention': 'No customer data stored. Owned local artifacts persist until owner deletes them; no timer exists.',
            'deletion': 'Owner may remove this owned package locally; no remote copies or secure-erasure guarantee.',
            'future_retention': 'Proposal only: delete submitted source and derived packages within 7 days of completion or rejection, or earlier on verified request; agree backup and provider deletion limits before intake. No automatic retention/deletion system is implemented.',
            'failure_refund': 'Proposal only: reject unsupported scope before acceptance; disclose failed verification without a verified claim; refund unfulfilled accepted work in full, subject to owner-reviewed terms before any sale. No sale, charge, payment or refund occurs now.',
        },
        'files': {name: {'sha256': _sha(raw), 'bytes': len(raw)} for name, raw in files.items()},
    }
    files['review.json'] = canonical(review) + b'\n'
    if any(len(raw) > MAX_FILE_BYTES for raw in files.values()) or sum(map(len, files.values())) > MAX_PACKAGE_BYTES:
        raise PackageBlocked('Owned package size limit exceeded')
    return files


def _open_private_directory(directory):
    """Walk without following links; anchor all later operations to an fd."""
    path = Path(directory)
    fd = None
    try:
        require_private_directory(path)
        if '..' in path.parts:
            raise PackageBlocked('Noncanonical directory')
        fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PackageBlocked('Private directory required')
        result, fd = fd, None
        return result
    except (OSError, SyntheticBlocked):
        raise PackageBlocked('Private absolute owned directory required') from None
    finally:
        if fd is not None:
            os.close(fd)


def _receipt(files):
    return {'schema': 1, 'kind': 'inactive_owned_package_receipt', 'notice': NOTICE,
            'owned_only': True, 'live_offer': False, 'launch_enabled': False,
            'delivery_enabled': False, 'customer_environment_tested': False,
            'review_sha256': _sha(files['review.json']),
            'file_count': len(files), 'total_bytes': sum(map(len, files.values()))}


def build_owned_package(output_directory):
    """Write only fixed owned fixture bytes; no source, commands or authority input."""
    files = _expected_files()
    parent_fd = _open_private_directory(output_directory)
    package_fd = None
    created = []
    made_directory = False
    try:
        os.mkdir(PACKAGE_NAME, mode=0o700, dir_fd=parent_fd)
        made_directory = True
        package_fd = os.open(PACKAGE_NAME, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        for name, raw in files.items():
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=package_fd)
            created.append(name)
            try:
                view = memoryview(raw)
                while view:
                    count = os.write(fd, view)
                    if count <= 0:
                        raise PackageBlocked('Owned package write failed')
                    view = view[count:]
                os.fsync(fd)
            finally:
                os.close(fd)
        os.fsync(package_fd)
        os.fsync(parent_fd)
    except (OSError, PackageBlocked):
        if package_fd is not None:
            for name in created:
                os.unlink(name, dir_fd=package_fd)
        if made_directory:
            os.rmdir(PACKAGE_NAME, dir_fd=parent_fd)
        raise PackageBlocked('Owned package unavailable; existing packages are never overwritten') from None
    finally:
        if package_fd is not None:
            os.close(package_fd)
        os.close(parent_fd)
    return _receipt(files)


def verify_owned_package(package_directory):
    """Bounded comparison to fixed owned content, not a trust or delivery token."""
    expected = _expected_files()
    directory_fd = _open_private_directory(package_directory)
    try:
        if set(os.listdir(directory_fd)) != set(expected):
            raise PackageBlocked('Owned package file set changed')
        for name, raw in expected.items():
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
            try:
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or info.st_nlink != 1 or info.st_mode & 0o077
                        or info.st_size > MAX_FILE_BYTES):
                    raise PackageBlocked('Owned package file not private regular bounded content')
                actual = bytearray()
                while len(actual) <= MAX_FILE_BYTES:
                    chunk = os.read(fd, MAX_FILE_BYTES + 1 - len(actual))
                    if not chunk:
                        break
                    actual.extend(chunk)
                if bytes(actual) != raw:
                    raise PackageBlocked('Owned package content changed')
            finally:
                os.close(fd)
    except OSError:
        raise PackageBlocked('Owned package unavailable') from None
    finally:
        os.close(directory_fd)
    return _receipt(expected)
