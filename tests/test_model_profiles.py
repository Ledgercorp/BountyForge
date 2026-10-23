"""Profile selection tests use fake observations, never model-performance evidence."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from tests import test_repair_engines as engine_tests
from bountyforge import repair_engines as api


class ProfileSelectionTests(unittest.TestCase):
    def service(self):
        helper=engine_tests.EngineContractTests();helper.setUp();return helper.service([False,False])

    def test_default_and_experimental_profile_are_explicitly_bound(self):
        default=self.service().prepare('weighted-mix','QWEN_LOCAL')
        larger=self.service().prepare('weighted-mix','QWEN_LOCAL',model_profile='QWEN_7B')
        self.assertEqual(default['model_profile'],'QWEN_1_5B')
        self.assertEqual(larger['model_profile'],'QWEN_7B')
        self.assertNotEqual(default['model_sha256'],larger['model_sha256'])

    def test_codex_is_not_a_local_model_profile_and_unknown_values_fail_before_execution(self):
        for engine,profile in [('CODEX_AGENT','QWEN_7B'),('QWEN_LOCAL','PAID'),('QWEN_LOCAL',{})]:
            service=self.service()
            with patch.object(service.verifier,'preflight') as sandbox:
                with self.assertRaises(ValueError):service.prepare('weighted-mix',engine,model_profile=profile)
                sandbox.assert_not_called()

    def test_unavailable_selected_model_cannot_fall_back_to_default(self):
        service=self.service();task=service.prepare('weighted-mix','QWEN_LOCAL',model_profile='QWEN_7B')
        with patch.object(api,'qwen_availability',return_value=False) as admission,patch.object(api,'LocalModel') as model:
            result=service.run_qwen(task['task_id'],0)
            admission.assert_called_once_with('QWEN_7B');model.assert_not_called()
        self.assertEqual(result['model_profile'],'QWEN_7B');self.assertEqual(result['model_calls'],0)
        self.assertFalse(result['paid_fallback'])

    def test_queue_profile_survives_release_restart_and_cannot_change_idempotent_batch(self):
        from bountyforge.owned_repair_queue import OwnedRepairQueue
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'private'/'state.sqlite3'
            queue=OwnedRepairQueue(path,service_factory=self.service)
            queue.create('profile','QWEN_LOCAL',['weighted-mix'],model_profile='QWEN_7B')
            with self.assertRaisesRegex(ValueError,'BATCH_ID_CONFLICT'):
                queue.create('profile','QWEN_LOCAL',['weighted-mix'],model_profile='QWEN_1_5B')
            job=queue.claim('profile');self.assertEqual(job['task']['model_profile'],'QWEN_7B')
            queue.release('profile',job['job_id'],job['lease_token'])
            restarted=OwnedRepairQueue(path,service_factory=self.service)
            job=restarted.claim('profile');self.assertEqual(job['task']['model_profile'],'QWEN_7B')
            restarted.stop('profile');self.assertEqual(queue.claim('profile')['outcome'],'STOPPED')

    def test_endpoint_identity_includes_model_context_and_one_stream(self):
        from bountyforge.model_profiles import endpoint_matches
        props={'model_path':'/fixed/model','total_slots':1,'default_generation_settings':{'n_ctx':2048}}
        self.assertTrue(endpoint_matches(props,'/fixed/model'))
        for bad in [[],{**props,'model_path':'/other/model'},{**props,'total_slots':2},
                    {**props,'default_generation_settings':{'n_ctx':4096}}]:
            self.assertFalse(endpoint_matches(bad,'/fixed/model'))

    def test_experimental_availability_does_not_mislabel_engine_when_default_is_unavailable(self):
        with patch.object(api,'qwen_availability',side_effect=lambda p:p=='QWEN_7B'):
            qwen=api.engine_inventory()[0]
        self.assertEqual(qwen['availability'],'AVAILABLE')
        self.assertEqual(qwen['default_model_profile'],'QWEN_1_5B')
        self.assertEqual(qwen['model_profiles'][0]['availability'],'PINNED_LOCAL_RUNTIME_UNAVAILABLE')
