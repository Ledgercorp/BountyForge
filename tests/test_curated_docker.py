import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bountyforge.curated_docker import (
    IMAGE, MARKER, CuratedSandboxUnavailable,
    _args, verify_curated, run_curated, verify_runtime_boundary,
)

class CuratedDockerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/MARKER).write_text('459')
        (self.root/'strutils.py').write_text('def f():\n    return 1\n')
        (self.root/'tests').mkdir()
        (self.root/'tests'/'test_regression.py').write_text(
            'import unittest\nclass T(unittest.TestCase):\n'
            ' def test_f(self): self.assertTrue(True)\n')

    def test_curated_marker(self):
        self.assertEqual(verify_curated(self.root),self.root.resolve())
        (self.root/MARKER).write_text('arbitrary')
        with self.assertRaises(CuratedSandboxUnavailable):
            verify_curated(self.root)

    def test_symlink_rejected(self):
        (self.root/'evil').symlink_to('/etc/passwd')
        with self.assertRaises(CuratedSandboxUnavailable):
            verify_curated(self.root)

    def test_missing_docker_fails_closed(self):
        with patch('bountyforge.curated_docker.shutil.which',return_value=None):
            with self.assertRaises(CuratedSandboxUnavailable):
                run_curated(self.root)
            with self.assertRaises(CuratedSandboxUnavailable):
                verify_runtime_boundary(self.root)

    def test_exact_docker_flags(self):
        args=_args(self.root,'bf-curated-test')
        flags=' '.join(args)
        for value in ('--network none','--read-only','--cap-drop ALL',
                      '--security-opt no-new-privileges','--user 65534:65534',
                      '--pull never','--pids-limit 64','readonly'):
            self.assertIn(value,flags)
        self.assertIn(IMAGE,args)
        self.assertNotIn('/var/run/docker.sock',flags)
        self.assertNotIn('GITHUB_TOKEN',flags)

    def test_unbounded_timeout_denied(self):
        with self.assertRaises(ValueError):
            run_curated(self.root,timeout=200)

if __name__=='__main__':
    unittest.main()
