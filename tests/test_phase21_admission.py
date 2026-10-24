import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import signal


class QualityRunAdmissionTests(unittest.TestCase):
    def module(self):
        try:import phase21_runner
        except ImportError:self.fail('Frozen owned comparison admission is missing')
        return phase21_runner

    def test_crash_reserved_arm_cannot_get_another_two_requests(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'claims';history=Path(temp)/'results'
            m.claim('cache-refresh','SDK_DIAG',root=root,history=history)
            with self.assertRaisesRegex(ValueError,'ALREADY_RESERVED'):
                m.claim('cache-refresh','SDK_DIAG',root=root,history=history)
            self.assertEqual(len(list(root.glob('*.claim'))),1)
            with self.assertRaises(ValueError):m.claim('../../etc','SDK_DIAG',root=root,history=history)

    def test_recorded_arm_prevents_new_requests_after_private_claim_store_is_lost(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'claims';history=Path(temp)/'results';history.mkdir()
            (history/'cache-refresh--SDK_DIAG.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'RECORDED_ARM_CLOSED'):
                m.claim('cache-refresh','SDK_DIAG',root=root,history=history)
            self.assertFalse(root.exists())

    def test_cli_requires_explicit_pinned_experiment_and_cannot_execute_customer_source(self):
        self.module();root=Path(__file__).resolve().parents[1]
        for args in ([],['--execute-customer','/tmp/customer'],['--admit-owned-evaluation']):
            r=subprocess.run([sys.executable,'-B','-m','phase21_runner',*args],cwd=root,capture_output=True,timeout=5)
            self.assertEqual(r.returncode,2)

    def test_capacity_uses_cgroup_headroom_instead_of_larger_host_memory(self):
        m=self.module();gib=1024**3
        with self.assertRaisesRegex(ValueError,'CAPACITY'):
            m.admit_capacity('200000 100000',8*gib,5*gib,3*gib)
        with self.assertRaisesRegex(ValueError,'CAPACITY'):
            m.admit_capacity('100000 100000',8*gib,2*gib,3*gib)
        self.assertTrue(m.admit_capacity('200000 100000',8*gib,2*gib,3*gib)['admitted'])

    def test_operator_termination_runs_finally_cleanup_and_preserves_a_reserved_budget(self):
        self.module();root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            marker=Path(temp)/'cleaned'
            claimroot=Path(temp)/'claims';history=Path(temp)/'history'
            code="from phase21_runner import install_stop_handler,claim; import signal,pathlib; install_stop_handler(); claim('cache-refresh','SDK_DIAG',root=pathlib.Path("+repr(str(claimroot))+"),history=pathlib.Path("+repr(str(history))+")); print('READY',flush=True)\ntry:signal.pause()\nfinally:pathlib.Path("+repr(str(marker))+").write_text('cleanup')"
            child=subprocess.Popen([sys.executable,'-B','-c',code],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(),'READY')
                child.send_signal(signal.SIGTERM);child.wait(timeout=5)
                self.assertEqual(child.returncode,143)
                self.assertEqual(marker.read_text(),'cleanup')
                with self.assertRaisesRegex(ValueError,'ALREADY_RESERVED'):
                    self.module().claim('cache-refresh','SDK_DIAG',root=claimroot,history=history)
            finally:
                if child.poll() is None:child.kill();child.wait(timeout=5)
                child.stdout.close();child.stderr.close()
