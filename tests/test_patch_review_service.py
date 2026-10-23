"""Owned package integrity and actual CLI refusal boundaries."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bountyforge.patch_review_service import (
    PackageBlocked, build_owned_package, verify_owned_package,
)
from bountyforge.phase7_owned_demo import SOURCE, PATCHED

REPO = Path(__file__).resolve().parents[1]


class PatchReviewServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / 'private'
        self.output.mkdir(mode=0o700)

    def run_cli(self, *arguments, stdin=b''):
        return subprocess.run([sys.executable, '-m', 'scripts.patch_review_service', *arguments], input=stdin,
                              capture_output=True, cwd=REPO, timeout=10)

    def test_owned_package_is_honest_private_and_verifiable(self):
        receipt = build_owned_package(self.output)
        package = self.output / 'owned-review-package'
        self.assertEqual(verify_owned_package(package), receipt)
        self.assertEqual(receipt['review_sha256'], hashlib.sha256((package / 'review.json').read_bytes()).hexdigest())
        review = json.loads((package / 'review.json').read_bytes())
        self.assertEqual((package / 'owned_before.py').read_bytes(), SOURCE)
        self.assertEqual((package / 'owned_after.py').read_bytes(), PATCHED)
        self.assertIn(b'-    return a - b\n+    return a + b\n', (package / 'repair.patch').read_bytes())
        self.assertEqual(review['authorship'], 'manually_authored_phase7_owned_repair')
        self.assertFalse(review['verification']['customer_environment_tested'])
        self.assertEqual(review['verification']['owned_replay']['vectors'], 4)
        self.assertTrue(review['owned_only'])
        for field in ('launch_enabled', 'delivery_enabled', 'live_offer', 'customer_intake_enabled'):
            self.assertIs(review[field], False)
        self.assertEqual(stat.S_IMODE(package.stat().st_mode), 0o700)
        for path in package.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertLess(sum(p.stat().st_size for p in package.iterdir()), 65536)

    def test_diff_applies_to_exact_owned_before(self):
        build_owned_package(self.output)
        package = self.output / 'owned-review-package'
        lines = (package / 'repair.patch').read_text().splitlines(keepends=True)[3:]
        before = ''.join(line[1:] for line in lines if line[0] in ' -').encode()
        after = ''.join(line[1:] for line in lines if line[0] in ' +').encode()
        self.assertEqual(before, SOURCE)
        self.assertEqual(after, PATCHED)

    def test_any_file_corruption_or_extra_file_is_rejected(self):
        build_owned_package(self.output)
        package = self.output / 'owned-review-package'
        for path in package.iterdir():
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.assertRaises(PackageBlocked):
                verify_owned_package(package)
            path.write_bytes(original)
        (package / 'unexpected').write_bytes(b'')
        with self.assertRaises(PackageBlocked):
            verify_owned_package(package)

    def test_manifest_cannot_assert_customer_or_model_verification(self):
        build_owned_package(self.output)
        package = self.output / 'owned-review-package'
        path = package / 'review.json'
        review = json.loads(path.read_bytes())
        review['verification']['customer_environment_tested'] = True
        path.write_text(json.dumps(review))
        with self.assertRaises(PackageBlocked):
            verify_owned_package(package)

    def test_existing_package_never_overwritten(self):
        first = build_owned_package(self.output)
        with self.assertRaises(PackageBlocked):
            build_owned_package(self.output)
        self.assertEqual(verify_owned_package(self.output / 'owned-review-package'), first)

    def test_insecure_relative_and_symlink_directories_refused(self):
        self.output.chmod(0o755)
        with self.assertRaises(PackageBlocked):
            build_owned_package(self.output)
        self.output.chmod(0o700)
        link = self.root / 'link'
        link.symlink_to(self.output, target_is_directory=True)
        for directory in (link, Path('.'), self.root / 'missing'):
            with self.assertRaises(PackageBlocked):
                build_owned_package(directory)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_symlink_ancestor_refused(self):
        link = self.root / 'link'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(PackageBlocked):
            build_owned_package(link / 'private')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_verifier_rejects_symlink_hardlink_and_public_files(self):
        build_owned_package(self.output)
        package = self.output / 'owned-review-package'
        path = package / 'repair.patch'
        raw = path.read_bytes()
        path.chmod(0o644)
        with self.assertRaises(PackageBlocked):
            verify_owned_package(package)
        path.chmod(0o600)
        os.link(path, self.root / 'hardlink')
        with self.assertRaises(PackageBlocked):
            verify_owned_package(package)
        (self.root / 'hardlink').unlink()
        path.unlink()
        outside = self.root / 'outside'
        outside.write_bytes(raw)
        path.symlink_to(outside)
        with self.assertRaises(PackageBlocked):
            verify_owned_package(package)

    def test_bounded_reader_rejects_oversized_file_and_fifo(self):
        build_owned_package(self.output)
        package = self.output / 'owned-review-package'
        path = package / 'repair.patch'
        path.write_bytes(b'x' * 32769)
        with self.assertRaises(PackageBlocked):
            verify_owned_package(package)
        path.unlink()
        os.mkfifo(path, mode=0o600)
        with self.assertRaises(PackageBlocked):
            verify_owned_package(package)

    def test_failed_write_removes_only_its_new_package(self):
        sentinel = self.output / 'owner-file'
        sentinel.write_bytes(b'preserve')
        with patch('bountyforge.patch_review_service.os.write', side_effect=OSError('disk full')):
            with self.assertRaises(PackageBlocked):
                build_owned_package(self.output)
        self.assertEqual(list(self.output.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_cli_success_has_owned_only_disabled_receipt(self):
        result = self.run_cli('--owned-only-package', '--output-dir', str(self.output))
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt['owned_only'])
        self.assertFalse(receipt['live_offer'])
        self.assertFalse(receipt['delivery_enabled'])
        self.assertEqual(receipt, verify_owned_package(self.output / 'owned-review-package'))

    def test_cli_unknown_customer_and_deceptive_arguments_write_nothing(self):
        for extra in ('--source', '--customer-path', '--execute', '--launch', '--deliver',
                      '--customer-environment-tested', '--model-generated', '--output-d',
                      '--source=customer.py'):
            with self.subTest(extra=extra):
                result = self.run_cli('--owned-only-package', '--output-dir', str(self.output), extra, 'anything')
                self.assertEqual(result.returncode, 2)
                self.assertIn(b'owned-only; not a live offer', result.stderr)
                self.assertEqual(list(self.output.iterdir()), [])

    def test_cli_missing_mode_or_output_and_help_write_nothing(self):
        for args in ((), ('--owned-only-package',), ('--output-dir', str(self.output)), ('--help',)):
            result = self.run_cli(*args)
            self.assertIn(result.returncode, (0, 2))
            self.assertIn(b'owned-only; not a live offer', result.stdout + result.stderr)
            self.assertEqual(list(self.output.iterdir()), [])

    def test_cli_duplicate_oversized_and_invalid_output_write_nothing(self):
        normal = ['--owned-only-package', '--output-dir', str(self.output)]
        cases = [normal + ['--owned-only-package'],
                 normal + ['--output-dir', str(self.output)],
                 normal + ['x' * 5000],
                 ['--owned-only-package', '--output-dir', 'relative-customer.py']]
        for args in cases:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'owned-only; not a live offer', result.stderr)
            self.assertEqual(list(self.output.iterdir()), [])

    def test_direct_script_process_boundary(self):
        for args in (['--help'], ['--customer-source', 'customer.py']):
            result = subprocess.run(
                [sys.executable, str(REPO / 'scripts' / 'patch_review_service.py'), *args],
                input=b'', capture_output=True, cwd=self.root, timeout=10)
            self.assertIn(result.returncode, (0, 2))
            self.assertIn(b'owned-only; not a live offer', result.stdout + result.stderr)
            self.assertNotIn(b'Traceback', result.stderr)
            self.assertEqual(list(self.output.iterdir()), [])

    def test_cli_rejects_nonempty_and_oversized_stdin_before_writes(self):
        for data in (b'customer code', b'\n', b'x' * 100000):
            result = self.run_cli('--owned-only-package', '--output-dir', str(self.output), stdin=data)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'owned-only; not a live offer', result.stderr)
            self.assertEqual(list(self.output.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
