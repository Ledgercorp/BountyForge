"""Offline rootfs provenance checks on synthetic files only; no execution."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bountyforge.rootfs_provenance import (
    RootfsProvenanceRejected, inventory_rootfs, verify_rootfs_pin,
)


class RootfsProvenanceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'owned-rootfs'
        folders = ['usr/bin', 'usr/lib/python3.13', 'lib/x86_64-linux-gnu',
                   'lib64', 'work', 'tmp']
        self.path.mkdir(mode=0o700)
        for path in folders:
            (self.path / path).mkdir(parents=True, exist_ok=True, mode=0o700)
        self.python = self.path / 'usr/bin/python3.13'
        self.runner = self.path / 'usr/bin/bf-safe-python'
        self.lib = self.path / 'lib/x86_64-linux-gnu/libc.so.6'
        self.interpreter = self.path / 'usr/lib/python3.13/unittest.py'
        self.linker = self.path / 'lib64/ld-linux-x86-64.so.2'
        for p, data in (
            (self.python, b'owned ELF python 3.13'),
            (self.runner, b'owned safe runner canary'),
            (self.lib, b'owned libc bytes'),
            (self.interpreter, b'owned stdlib bytes'),
            (self.linker, b'owned loader bytes'),
        ):
            p.write_bytes(data)
            p.chmod(0o500 if p in (self.python, self.runner) else 0o400)
        for child in sorted((p for p in self.path.rglob('*') if p.is_dir()),
                            key=lambda p: len(p.parts), reverse=True):
            child.chmod(0o700 if child.parts[-1] in ('work', 'tmp') else 0o500)

    def test_offline_builder_marks_all_runtime_roots_nonwritable(self):
        builder = (Path(__file__).resolve().parents[1] /
                   'isolation/build_rootfs.sh').read_text()
        self.assertIn('chmod -R a-w "$root/usr" "$root/lib" "$root/lib64"', builder)

    def test_hash_is_stable_and_requires_external_exact_pin(self):
        report = inventory_rootfs(self.path)
        self.assertEqual(report['kind'], 'rootfs_file_provenance_inventory')
        self.assertEqual(report['file_count'], 5)
        self.assertEqual(len(report['tree_sha256']), 64)
        self.assertFalse(report['execution_authorized'])
        self.assertFalse(report['rootfs_execution_admitted'])
        self.assertFalse(report['producer_identity_verified'])
        self.assertNotIn('owned ELF', str(report))
        self.assertEqual(report['tree_sha256'], inventory_rootfs(self.path)['tree_sha256'])
        pinned = verify_rootfs_pin(self.path, report['tree_sha256'])
        self.assertTrue(pinned['digest_matches_pin'])
        self.assertFalse(pinned['rootfs_execution_admitted'])

    def test_wrong_or_malformed_pin_fails(self):
        for digest in ('0' * 64, '', 'x'*64, 'F'*64, None, True):
            with self.subTest(digest=digest), self.assertRaises(RootfsProvenanceRejected):
                verify_rootfs_pin(self.path, digest)

    def test_modified_runtime_or_stdlib_fails_independent_pin(self):
        expected = inventory_rootfs(self.path)['tree_sha256']
        for file in (self.python, self.runner, self.lib, self.interpreter):
            old = file.read_bytes()
            file.chmod(0o700)
            file.write_bytes(old + b' changed')
            file.chmod(0o500 if file in (self.python, self.runner) else 0o400)
            with self.subTest(file=file), self.assertRaises(RootfsProvenanceRejected):
                verify_rootfs_pin(self.path, expected)
            file.chmod(0o700)
            file.write_bytes(old)
            file.chmod(0o500 if file in (self.python, self.runner) else 0o400)

    def test_extra_file_and_empty_directory_change_digest(self):
        expected = inventory_rootfs(self.path)['tree_sha256']
        extra = self.path / 'usr/lib/python3.13/extra.py'
        extra.parent.chmod(0o700)
        extra.write_bytes(b'pass\n')
        extra.chmod(0o400)
        extra.parent.chmod(0o500)
        with self.assertRaises(RootfsProvenanceRejected):
            verify_rootfs_pin(self.path, expected)
        extra.parent.chmod(0o700)
        extra.unlink()
        (self.path / 'usr/lib/python3.13/extra-empty').mkdir(mode=0o500)
        extra.parent.chmod(0o500)
        with self.assertRaises(RootfsProvenanceRejected):
            verify_rootfs_pin(self.path, expected)

    def test_symlinks_fifo_and_hardlinks_are_rejected(self):
        sibling = Path(self.path.parent) / 'sibling-lib'
        sibling.write_bytes(self.lib.read_bytes())
        linked = self.path / 'usr/lib/python3.13/escaped'
        linked.parent.chmod(0o700)
        linked.symlink_to(sibling)
        linked.parent.chmod(0o500)
        with self.assertRaises(RootfsProvenanceRejected):
            inventory_rootfs(self.path)
        linked.parent.chmod(0o700)
        linked.unlink()
        os.link(self.lib, linked)
        linked.parent.chmod(0o500)
        with self.assertRaises(RootfsProvenanceRejected):
            inventory_rootfs(self.path)
        linked.parent.chmod(0o700)
        linked.unlink()
        os.mkfifo(linked, mode=0o600)
        linked.parent.chmod(0o500)
        with self.assertRaises(RootfsProvenanceRejected):
            inventory_rootfs(self.path)

    def test_writable_runtime_binary_or_library_rejected(self):
        for p in (self.python, self.lib, self.interpreter):
            original = p.stat().st_mode & 0o777
            p.chmod(original | 0o200)
            with self.subTest(file=p), self.assertRaises(RootfsProvenanceRejected):
                inventory_rootfs(self.path)
            p.chmod(original)

    def test_missing_runtime_entries_and_executable_bit_rejected(self):
        self.runner.chmod(0o400)
        with self.assertRaises(RootfsProvenanceRejected):
            inventory_rootfs(self.path)
        self.runner.chmod(0o500)
        self.python.parent.chmod(0o700)
        self.python.unlink()
        self.python.parent.chmod(0o500)
        with self.assertRaises(RootfsProvenanceRejected):
            inventory_rootfs(self.path)

    def test_symlink_root_and_ancestor_swap_denied(self):
        pointer = Path(self.path.parent) / 'pointer'
        pointer.symlink_to(self.path, target_is_directory=True)
        with self.assertRaises(RootfsProvenanceRejected):
            inventory_rootfs(pointer)
        previous = os.open
        parent = self.path.parent
        staging = parent / 'staging'
        moved = parent / 'relocated-staging'
        staging.mkdir(mode=0o700)
        self.path.rename(staging / 'owned-rootfs')
        replaced = [False]
        def swap(name, flags, *args, **kwargs):
            if not replaced[0] and str(name) == 'staging' and 'dir_fd' in kwargs:
                replaced[0] = True
                staging.rename(moved)
                staging.symlink_to(moved, target_is_directory=True)
            return previous(name, flags, *args, **kwargs)
        try:
            with patch('bountyforge.rootfs_provenance.os.open', side_effect=swap):
                with self.assertRaises(RootfsProvenanceRejected):
                    inventory_rootfs(staging / 'owned-rootfs')
            self.assertTrue(replaced[0])
        finally:
            if staging.is_symlink():
                staging.unlink()
            if moved.exists():
                moved.rename(staging)
            (staging / 'owned-rootfs').rename(self.path)
            staging.rmdir()

    def test_inventory_does_not_execute_or_import_runtime_contents(self):
        with patch('subprocess.Popen', side_effect=AssertionError('must not execute')):
            with patch('subprocess.run', side_effect=AssertionError('must not execute')):
                with patch('builtins.exec', side_effect=AssertionError('must not execute')):
                    self.assertEqual(inventory_rootfs(self.path)['file_count'], 5)

    def test_missing_required_layout_and_unknown_top_level_rejected(self):
        root = self.path
        (root / 'unexpected').mkdir(mode=0o700)
        with self.assertRaises(RootfsProvenanceRejected):
            inventory_rootfs(root)
        (root / 'unexpected').rmdir()
        (root / 'work').rmdir()
        with self.assertRaises(RootfsProvenanceRejected):
            inventory_rootfs(root)


if __name__ == '__main__':
    unittest.main()
