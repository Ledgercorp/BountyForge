import tempfile
import shutil
import subprocess
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
        original=Path(__file__).resolve().parents[1]/'benchmarks/phase4/tasks/459'
        shutil.copytree(original,self.root,dirs_exist_ok=True)

    def test_forged_marker_does_not_admit_arbitrary_code(self):
        (self.root/'strutils.py').write_text('raise RuntimeError("outside curated source")\n')
        with self.assertRaises(CuratedSandboxUnavailable):
            verify_curated(self.root)

    def test_tests_cannot_be_replaced(self):
        (self.root/'tests/test_regression.py').write_text('print("OK")\n')
        with self.assertRaises(CuratedSandboxUnavailable):
            verify_curated(self.root)

    def test_unexpected_file_cannot_execute_at_python_startup(self):
        (self.root/'sitecustomize.py').write_text('pass\n')
        with self.assertRaises(CuratedSandboxUnavailable):
            verify_curated(self.root)

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
    def test_cleanup_does_not_confuse_daemon_outage_with_absence(self):
        from bountyforge.curated_docker import _cleanup
        unavailable=subprocess.CompletedProcess([],1,stdout='',stderr='Cannot connect to the Docker daemon')
        with patch('bountyforge.curated_docker.subprocess.run',return_value=unavailable):
            with self.assertRaises(CuratedSandboxUnavailable):
                _cleanup('bf-curated-test',{})

    def pressure_results(self, pid=None, cpu=None):
        return [
            {'passed':True,'output':'BOUNTYFORGE_CURATED_BOUNDARY_OK'},
            {'timeout':True}, {'returncode':137}, {'error':'output_budget'},
            pid or {'passed':True,'output':'{"pid_pressure_enforced":true,"pid_denial_events":1}'},
            cpu or {'passed':True,'output':'{"cpu_pressure_enforced":true,"cpu_throttled_periods":10}'},
        ]

    def test_failed_pid_pressure_blocks_admission(self):
        results=self.pressure_results(pid={'passed':False,'output':'PID exhaustion was not denied'})
        with patch('bountyforge.curated_docker.shutil.which',return_value='/usr/bin/docker'), \
                patch('bountyforge.curated_docker._execute',side_effect=results):
            with self.assertRaisesRegex(CuratedSandboxUnavailable,'PID pressure restriction failed'):
                verify_runtime_boundary(self.root)

    def test_successful_process_without_pressure_proof_blocks_admission(self):
        results=self.pressure_results(cpu={'passed':True,'output':'{}'})
        with patch('bountyforge.curated_docker.shutil.which',return_value='/usr/bin/docker'), \
                patch('bountyforge.curated_docker._execute',side_effect=results):
            with self.assertRaisesRegex(CuratedSandboxUnavailable,'CPU pressure evidence missing'):
                verify_runtime_boundary(self.root)

    def test_pressure_measurements_are_preserved(self):
        with patch('bountyforge.curated_docker.shutil.which',return_value='/usr/bin/docker'), \
                patch('bountyforge.curated_docker._execute',side_effect=self.pressure_results()):
            proof=verify_runtime_boundary(self.root)
        self.assertTrue(proof['pid_pressure_enforced'])
        self.assertTrue(proof['cpu_pressure_enforced'])
        self.assertEqual(proof['pid_denial_events'],1)
        self.assertEqual(proof['cpu_throttled_periods'],10)
        self.assertFalse(proof['untrusted_execution_certified'])

if __name__=='__main__':
    unittest.main()
