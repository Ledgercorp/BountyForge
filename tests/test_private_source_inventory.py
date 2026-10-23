"""Offline-only private byte/custody preflight. Never runs supplied Python."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bountyforge.private_source_inventory import inspect_private_source, PrivateSourceRejected


class PrivateSourceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'customer-private'
        self.root.mkdir(mode=0o700)
        self.src = self.root / 'module.py'
        self.test_dir = self.root / 'tests'
        self.test_dir.mkdir(mode=0o700)
        self.test = self.test_dir / 'test_regression.py'
        self.src.write_text('def add(x):\n    return x + 1\n')
        self.test.write_text('import unittest\n\nclass Case(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(1, 1)\n')
        self.src.chmod(0o600)
        self.test.chmod(0o600)
        self.approval = {
            'schema': 1, 'session_sha256': 'a' * 64,
            'source_path': 'module.py',
            'source_sha256': hashlib.sha256(self.src.read_bytes()).hexdigest(),
            'test_path': 'tests/test_regression.py',
            'tests_sha256': hashlib.sha256(self.test.read_bytes()).hexdigest(),
            'dependency_policy': 'stdlib_only_v1',
            'source_access_receipt_sha256': 'b' * 64,
            'model_sharing_receipt_sha256': 'c' * 64,
            'owner_approval_id': 'd' * 32, 'expires_at': 1999999999
        }

    def inspect(self):
        return inspect_private_source(self.root, self.approval)

    def test_exact_files_and_bytes_produce_review_only_digest_evidence(self):
        result = self.inspect()
        self.assertEqual(result['kind'], 'private_source_digest_inspection')
        self.assertEqual(result['source_sha256'], self.approval['source_sha256'])
        self.assertEqual(result['tests_sha256'], self.approval['tests_sha256'])
        self.assertEqual(result['source_path'], 'module.py')
        self.assertEqual(result['file_count'], 2)
        for flag in ('execution_authorized', 'delivery_authorized', 'source_accepted',
                     'rights_verified', 'model_sharing_verified', 'dependency_admitted',
                     'private_worker_admitted'):
            self.assertIs(result[flag], False)
        self.assertNotIn('return x', str(result))
        self.assertNotIn('source_access_receipt_sha256', str(result))

    def test_source_and_test_hash_mismatches_are_terminal(self):
        for field in ('source_sha256', 'tests_sha256'):
            with self.subTest(field=field):
                item = dict(self.approval)
                item[field] = 'f' * 64
                with self.assertRaises(PrivateSourceRejected):
                    inspect_private_source(self.root, item)
        self.assertEqual(self.inspect()['file_count'], 2)

    def test_source_and_test_symlinks_are_rejected_even_when_content_matches(self):
        outside = Path(self.tmp.name) / 'external.py'
        outside.write_bytes(self.src.read_bytes())
        self.src.unlink()
        self.src.symlink_to(outside)
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()
        self.src.unlink()
        self.src.write_text('def add(x):\n    return x + 1\n')
        self.src.chmod(0o600)
        self.test.unlink()
        self.test.symlink_to(outside)
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()

    def test_intermediate_and_root_directory_symlinks_rejected(self):
        (self.root / 'src').mkdir(mode=0o700)
        (self.root / 'src' / 'module.py').write_bytes(self.src.read_bytes())
        (self.root / 'src' / 'module.py').chmod(0o600)
        self.src.unlink()
        self.approval['source_path'] = 'src/module.py'
        parent = Path(self.tmp.name) / 'parent-src'
        (self.root / 'src').rename(parent)
        (self.root / 'src').symlink_to(parent, target_is_directory=True)
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()
        linked = Path(self.tmp.name) / 'linked-root'
        linked.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(PrivateSourceRejected):
            inspect_private_source(linked, self.approval)

    def test_ancestor_symlink_swap_during_open_cannot_redirect_staged_tree(self):
        staging = Path(self.tmp.name) / 'staging'
        staging.mkdir(mode=0o700)
        self.root.rename(staging / 'customer-private')
        self.root = staging / 'customer-private'
        relocated = Path(self.tmp.name) / 'relocated-staging'
        original_open = os.open
        swapped = [False]
        def swap_on_open(name, flags, *args, **kwargs):
            if not swapped[0] and (str(name) == str(self.root) or (str(name) == 'staging' and 'dir_fd' in kwargs)):
                swapped[0] = True
                staging.rename(relocated)
                staging.symlink_to(relocated, target_is_directory=True)
            return original_open(name, flags, *args, **kwargs)
        with patch('bountyforge.private_source_inventory.os.open', side_effect=swap_on_open):
            with self.assertRaises(PrivateSourceRejected):
                self.inspect()
        self.assertTrue(swapped[0], 'Test must reproduce the ancestor swap')

    def test_unapproved_extra_file_and_hidden_artifact_rejected(self):
        extra = self.root / 'requirements.txt'
        extra.write_text('requests\n')
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()
        extra.unlink()
        extra = self.root / '.secrets'
        extra.write_text('private')
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()

    def test_unapproved_hardlink_rejected(self):
        outside = Path(self.tmp.name) / 'linked-module.py'
        os.link(self.src, outside)
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()

    def test_permissive_file_or_directory_and_wrong_root_rejected(self):
        self.src.chmod(0o644)
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()
        self.src.chmod(0o600)
        self.test_dir.chmod(0o755)
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()
        self.test_dir.chmod(0o700)
        self.root.chmod(0o755)
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()

    def test_invalid_syntax_nonstdlib_and_dynamic_import_rejected_without_execution(self):
        cases = [
            b'def broken(:\n',
            b'import requests\n',
            b'from . import something\n',
            b'__import__("os")\n',
            b'importlib.import_module("os")\n',
            b'print("\\x00")\x00',
        ]
        for source in cases:
            with self.subTest(source=source[:30]):
                self.src.write_bytes(source)
                self.approval['source_sha256'] = hashlib.sha256(source).hexdigest()
                with patch('builtins.exec', side_effect=AssertionError('must never execute')):
                    with self.assertRaises(PrivateSourceRejected):
                        self.inspect()

    def test_size_and_scope_rejections(self):
        data = b'#' + b'x' * 131073 + b'\n'
        self.src.write_bytes(data)
        self.approval['source_sha256'] = hashlib.sha256(data).hexdigest()
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()
        self.src.write_text('pass\n')
        item = dict(self.approval, source_path='../module.py')
        with self.assertRaises(PrivateSourceRejected):
            inspect_private_source(self.root, item)
        item = dict(self.approval, dependency_policy='pip_install')
        with self.assertRaises(PrivateSourceRejected):
            inspect_private_source(self.root, item)
        item = dict(self.approval, execution_authorized=True)
        with self.assertRaises(PrivateSourceRejected):
            inspect_private_source(self.root, item)


if __name__ == '__main__':
    unittest.main()
