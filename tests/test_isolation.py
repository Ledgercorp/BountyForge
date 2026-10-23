import tempfile
import os
import unittest
from pathlib import Path
from bountyforge.isolation import launch, preflight, SandboxUnavailable

ROOTFS=Path(os.environ.get('BOUNTYFORGE_TEST_ROOTFS','/nonexistent-bountyforge-rootfs'))
LAUNCHER=Path(__file__).resolve().parents[1]/'isolation'/'launcher.sh'

@unittest.skipUnless((ROOTFS/'usr/bin/bf-safe-python').is_file(),'Linux namespace rootfs not provisioned; run isolation/build_rootfs.sh before sandbox acceptance')
class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'tests').mkdir()
        (self.root/'target.py').write_text('def f(): return 1\n')
    def test_isolation_probes(self):
        (self.root/'tests/test_probe.py').write_text('''import os,socket,unittest
class T(unittest.TestCase):
 def test_no_host(self):
  self.assertFalse(os.path.exists('/mnt/data'))
  self.assertFalse(os.path.exists('/proc/self/environ'))
 def test_no_net(self):
  with self.assertRaises(PermissionError): socket.socket()
 def test_no_fork(self):
  with self.assertRaises(PermissionError): os.fork()
''')
        r=launch(self.root,ROOTFS,LAUNCHER)
        self.assertEqual(r['status'],'pass',r)
        self.assertEqual(r['untrusted_execution_certified'],False)
    def test_failing_test_is_failure(self):
        (self.root/'tests/test_bad.py').write_text('import unittest\nclass T(unittest.TestCase):\n def test_bad(self): self.assertEqual(1,2)\n')
        r=launch(self.root,ROOTFS,LAUNCHER)
        self.assertEqual(r['status'],'fail')
    def test_rootfs_is_read_only_including_owner_chmod(self):
        # This canary belongs solely to the temporary trusted rootfs. A dropped
        # capability set alone does not stop its mapped owner changing modes.
        canary = ROOTFS/'tmp/bf-owned-readonly-canary'
        canary.write_text('owned rootfs canary')
        canary.chmod(0o444)
        self.addCleanup(lambda: canary.unlink(missing_ok=True))
        (self.root/'tests/test_readonly.py').write_text('''import os,unittest
class T(unittest.TestCase):
 def test_rootfs_write_and_chmod_denied(self):
  with self.assertRaises(OSError): os.chmod('/tmp/bf-owned-readonly-canary',0o644)
  with self.assertRaises(OSError):
   with open('/tmp/bf-owned-readonly-canary','w') as f: f.write('changed')
''')
        r=launch(self.root,ROOTFS,LAUNCHER)
        self.assertEqual(r['status'],'pass',r)
        self.assertEqual(canary.read_text(),'owned rootfs canary')
    def test_timeout_is_failure(self):
        (self.root/'tests/test_hang.py').write_text('import unittest,time\nclass T(unittest.TestCase):\n def test_hang(self): time.sleep(20)\n')
        r=launch(self.root,ROOTFS,LAUNCHER,timeout_seconds=2)
        self.assertEqual(r['status'],'fail')
        self.assertTrue(r['timeout'])
    def test_symlinks_blocked(self):
        (self.root/'tests/escape.py').symlink_to('/etc/passwd')
        with self.assertRaises(SandboxUnavailable): preflight(self.root)
    def test_named_secret_tree_blocked(self):
        (self.root/'.env').write_text('secret')
        with self.assertRaises(SandboxUnavailable): preflight(self.root)
    def test_runner_missing_or_invalid(self):
        with self.assertRaises(SandboxUnavailable): launch(self.root,self.root,LAUNCHER)
    def test_invalid_time_bound(self):
        with self.assertRaises(ValueError): launch(self.root,ROOTFS,LAUNCHER,timeout_seconds=3600)

if __name__=='__main__': unittest.main()
