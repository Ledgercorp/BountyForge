"""Unconditional configuration rejection; never starts a namespace or target."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bountyforge.isolation import launch, SandboxUnavailable


class IsolationPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / 'source'; self.source.mkdir()
        (self.source / 'tests').mkdir()
        self.rootfs = self.base / 'rootfs'
        (self.rootfs / 'usr/bin').mkdir(parents=True)
        for name in ('bf-safe-python', 'python3.13'):
            (self.rootfs / 'usr/bin' / name).write_text('UNIT_ONLY')
        self.launcher = self.base / 'launcher.sh'; self.launcher.write_text('# UNIT_ONLY\n')

    def test_source_root_symlink_is_rejected_before_canonicalization(self):
        link = self.base / 'linked-source'; link.symlink_to(self.source, target_is_directory=True)
        with patch('bountyforge.isolation.subprocess.Popen', side_effect=AssertionError('Must not execute')):
            with self.assertRaises(SandboxUnavailable):
                launch(link, self.rootfs, self.launcher)

    def test_launcher_symlink_is_rejected_before_canonicalization(self):
        link = self.base / 'linked-launcher'; link.symlink_to(self.launcher)
        with patch('bountyforge.isolation.subprocess.Popen', side_effect=AssertionError('Must not execute')):
            with self.assertRaises(SandboxUnavailable):
                launch(self.source, self.rootfs, link)

    def test_timeout_requires_bounded_integer_seconds(self):
        for timeout in (True, False, 2.5, '3', None):
            with self.subTest(timeout=timeout), patch('bountyforge.isolation.subprocess.Popen', side_effect=AssertionError('Must not execute')):
                with self.assertRaises(ValueError):
                    launch(self.source, self.rootfs, self.launcher, timeout_seconds=timeout)
