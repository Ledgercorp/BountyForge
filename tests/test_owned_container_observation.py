"""Offline test the bounded, source-free observation path."""
import subprocess
import unittest
from unittest.mock import patch
from scripts import observe_owned_container as worker
from bountyforge.curated_docker import IMAGE
from bountyforge.private_boundary_review import CONTROLS

def proof():
    return {**{k:True for k in CONTROLS}, 'image_digest':IMAGE.split('@',1)[1],
            'untrusted_execution_certified':False,'pid_current_at_denial':64,
            'pid_denial_events':2,'probe_threads':51,'cpu_throttled_periods':2,
            'cpu_pressure_wall_seconds':3.0,'cpu_pressure_used_seconds':2.8}

class ControlledObservationTests(unittest.TestCase):
    def test_missing_docker_fails_closed(self):
        with patch.object(worker.shutil,'which',return_value=None):
            with patch.object(worker.subprocess,'run') as run:
                out=worker.probe_owned_boundary()
        run.assert_not_called()
        self.assertEqual(out['reason'],'docker_unavailable')
        self.assertFalse(out['private_execution_admitted'])
    def test_pull_failure_reports_only_safe_reason(self):
        with patch.object(worker.shutil,'which',return_value='/usr/bin/docker'), \
             patch.object(worker.subprocess,'run',return_value=subprocess.CompletedProcess([],1)):
            out=worker.probe_owned_boundary()
        self.assertEqual(out['reason'],'pinned_image_unavailable')
        self.assertFalse(out['customer_source_executed'])
    def test_owned_fixture_pressure_proof_never_admits_private_data(self):
        with patch.object(worker.shutil,'which',return_value='/usr/bin/docker'), \
             patch.object(worker.subprocess,'run',return_value=subprocess.CompletedProcess([],0)), \
             patch.object(worker.shutil,'copytree',side_effect=lambda src,dst,**kw:dst.mkdir(parents=True)), \
             patch.object(worker,'verify_runtime_boundary',return_value=proof()):
            out=worker.probe_owned_boundary()
        self.assertEqual(out['result'],'observed')
        self.assertEqual(out['controls_verified'],20)
        self.assertFalse(out['private_execution_admitted'])
        self.assertFalse(out['private_custody_bound_to_runtime'])
    def test_bad_probes_do_not_expose_exception_text(self):
        with patch.object(worker.shutil,'which',return_value='/usr/bin/docker'), \
             patch.object(worker.subprocess,'run',return_value=subprocess.CompletedProcess([],0)), \
             patch.object(worker.shutil,'copytree',side_effect=lambda src,dst,**kw:dst.mkdir(parents=True)), \
             patch.object(worker,'verify_runtime_boundary',
                          side_effect=worker.CuratedSandboxUnavailable('Bearer secret')):
            out=worker.probe_owned_boundary()
        self.assertEqual(out['result'],'blocked')
        self.assertNotIn('Bearer',str(out))
if __name__=='__main__': unittest.main()
