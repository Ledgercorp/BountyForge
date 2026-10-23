"""No Docker or inference: validate the trusted bridge call boundaries with fakes."""
import copy
import sys
import types
import unittest
from unittest.mock import patch

from deepseek_owned_bridge import verify_owned_harness_response
from deepseek_harness_handoff import HarnessHandoffRejected
from test_deepseek_handoff import TASK

RESPONSE = '{"changes":[{"line":7,"new":"return x + 1"}]}'


class FakeRejected(ValueError):
    pass


class FakeRepairService:
    def __init__(self, task=None):
        self.task = copy.deepcopy(TASK if task is None else task)
        self.calls = 0
        self.block = False

    def _get(self, task_id, revision, engine):
        if self.block or task_id != self.task['task_id'] or revision != self.task['revision'] or engine != 'CODEX_AGENT':
            raise FakeRejected('STALE_CAPABILITY')
        return {'public': self.task}

    def submit(self, task_id, revision, proposal):
        self.calls += 1
        return {'independently_verified': False, 'outcome': 'TEST_FAILED', 'state': 'REVISION_REQUIRED',
                'task_id': task_id, 'revision': revision+1, 'proposal': proposal}


class HarnessOwnedBridgeTests(unittest.TestCase):
    def setUp(self):
        self.mod = types.ModuleType('bountyforge.repair_engines')
        self.mod.RepairService = FakeRepairService
        self.mod.RepairRejected = FakeRejected

    def invoke(self, service=None, task=None, output=RESPONSE, enabled=True):
        service = FakeRepairService() if service is None else service
        task = copy.deepcopy(TASK) if task is None else task
        with patch.dict(sys.modules, {'bountyforge.repair_engines': self.mod}):
            return verify_owned_harness_response(
                service, task, output, allow_owned_verification=enabled)

    def test_disabled_by_default(self):
        service=FakeRepairService()
        with self.assertRaisesRegex(HarnessHandoffRejected, 'EXPLICIT_OWNED'):
            self.invoke(service=service, enabled=False)
        self.assertEqual(service.calls, 0)

    def test_trusted_service_only(self):
        with self.assertRaisesRegex(HarnessHandoffRejected, 'TRUSTED_REPAIR'):
            self.invoke(service=object())

    def test_sends_valid_candidate_once(self):
        service=FakeRepairService()
        result=self.invoke(service=service)
        self.assertEqual(service.calls, 1)
        self.assertEqual(result['owned_verifier_receipt']['state'], 'REVISION_REQUIRED')
        self.assertFalse(result['independently_verified_owned_development'])
        self.assertFalse(result['delivery_authorized'])
        self.assertEqual(result['candidate_origin'], 'UNATTESTED_EXTERNAL_HARNESS_OUTPUT')

    def test_rejects_changed_live_identity(self):
        service=FakeRepairService()
        task=copy.deepcopy(TASK)
        service.task['source']+=' altered'
        with self.assertRaisesRegex(HarnessHandoffRejected, 'IDENTITY_CHANGED'):
            self.invoke(service=service,task=task)
        self.assertEqual(service.calls,0)

    def test_rejects_stale_capability(self):
        service=FakeRepairService();service.block=True
        with self.assertRaisesRegex(HarnessHandoffRejected, 'LIVE_OWNED_SESSION'):
            self.invoke(service=service)
        self.assertEqual(service.calls,0)

    def test_rejects_unbounded_response_before_submit(self):
        service=FakeRepairService()
        with self.assertRaises(HarnessHandoffRejected):
            self.invoke(service=service,output='{"changes":[],"command":"sh"}')
        self.assertEqual(service.calls,0)

    def test_rejects_forged_prepared_task(self):
        service=FakeRepairService()
        task=copy.deepcopy(TASK);task['tests_sha256']='d'*64
        with self.assertRaisesRegex(HarnessHandoffRejected, 'IDENTITY_CHANGED'):
            self.invoke(service=service,task=task)
        self.assertEqual(service.calls,0)

    def test_revision_required_is_valid_second_attempt(self):
        service=FakeRepairService();service.task['state']='REVISION_REQUIRED';service.task['revision']=1
        result=self.invoke(service=service,task=copy.deepcopy(service.task))
        self.assertEqual(service.calls,1)
        self.assertEqual(result['handoff']['revision'],1)


if __name__ == '__main__':
    unittest.main()
