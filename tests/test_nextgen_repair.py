"""Offline contract tests, never evidence of model repair accuracy."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bountyforge.model_profiles import profile_spec,DEFAULT_PROFILE
from bountyforge.local_model_runtime import LocalRuntime,enforce_limits
from tests import test_model_profiles as helpers


class NextgenTests(unittest.TestCase):
    def test_new_profiles_are_exact_experimental_assets_not_a_new_default(self):
        self.assertEqual(DEFAULT_PROFILE,'QWEN_1_5B')
        for name,size in [('QWEN35_4B',2740937888),('GRANITE42_3B',2244011552)]:
            spec=profile_spec(name)
            self.assertTrue(spec['experimental']);self.assertEqual(spec['bytes'],size)
            self.assertEqual(spec['runtime_sha256'],profile_spec()['runtime_sha256'])
            self.assertTrue(spec['thinking_disabled'])

    def test_named_envelope_has_hard_bounds_and_legacy_is_unchanged(self):
        from bountyforge.inference_envelopes import envelope_spec
        self.assertEqual(envelope_spec()['cpu_seconds'],180)
        self.assertEqual(envelope_spec()['request_seconds'],45)
        runtime=LocalRuntime('QWEN35_4B',resource_envelope='NEXTGEN_TRIAL')
        self.assertEqual(runtime.measurement['cpu_limit_seconds'],600)
        self.assertEqual(runtime.measurement['wall_limit_seconds'],240)
        with self.assertRaises(ValueError):LocalRuntime('QWEN35_4B',resource_envelope='unlimited')
        with patch('bountyforge.local_model_runtime.resource.setrlimit') as limit:enforce_limits('NEXTGEN_TRIAL')
        self.assertIn(600,[c.args[1][0] for c in limit.call_args_list])

    def test_queue_preserves_every_explicit_profile_in_task_and_restart(self):
        from bountyforge.owned_repair_queue import OwnedRepairQueue
        with tempfile.TemporaryDirectory() as d:
            helper=helpers.ProfileSelectionTests()
            queue=OwnedRepairQueue(Path(d)/'private/q.sqlite3',service_factory=helper.service)
            for profile in ('QWEN35_4B','GRANITE42_3B'):
                queue.create(profile.lower(),'QWEN_LOCAL',['weighted-mix'],model_profile=profile)
                job=queue.claim(profile.lower())
                self.assertEqual(job['task']['model_profile'],profile)
                queue.stop(profile.lower())

    def test_nextgen_transport_disables_thinking_but_never_strips_model_output(self):
        from bountyforge.nextgen_repair import TrialStatementModel
        model=TrialStatementModel(timeout_seconds=45)
        self.assertEqual(model.timeout_seconds,75);self.assertEqual(model.repair_completion_tokens,256)
        with patch('bountyforge.profiled_qwen.ProfiledStatementModel._post_native',return_value={'prompt':'assistant<think></think>'}) as post:
            model._post_native('/apply-template',{'messages':[]})
            self.assertEqual(post.call_args.args[1]['chat_template_kwargs'],{'enable_thinking':False})
        with patch('bountyforge.profiled_qwen.ProfiledStatementModel._post_native',return_value={'prompt':'assistant<think>'}):
            with self.assertRaisesRegex(RuntimeError,'THINKING_TEMPLATE'):model._post_native('/apply-template',{'messages':[]})

    def test_dependency_map_is_bounded_read_only_metadata_and_does_not_run_source(self):
        from bountyforge.nextgen_repair import dependency_map
        source='def alpha(x):\n    return beta(x)\ndef beta(x):\n    return gamma(x)\ndef gamma(x):\n    return x\ndef unrelated():\n    raise RuntimeError()\n'
        result=dependency_map(source,'alpha')
        self.assertEqual([x['symbol'] for x in result],['alpha','beta','gamma'])
        self.assertTrue(all(x['editable'] is (x['symbol']=='alpha') for x in result))
        self.assertNotIn('unrelated',json.dumps(result))

    def test_new_models_unavailable_never_dispatch_or_fall_back(self):
        helper=helpers.ProfileSelectionTests()
        for profile in ('QWEN35_4B','GRANITE42_3B'):
            service=helper.service();task=service.prepare('weighted-mix','QWEN_LOCAL',model_profile=profile)
            with patch('bountyforge.repair_engines.qwen_availability',return_value=False):
                result=service.run_qwen(task['task_id'],0)
            self.assertEqual(result['model_calls'],0);self.assertEqual(result['model_profile'],profile)

    def test_larger_output_budget_is_opt_in_and_not_accepted_by_legacy_adapter(self):
        from bountyforge.profiled_qwen import ProfiledStatementModel
        model=ProfiledStatementModel()
        with self.assertRaises(ValueError):model.complete_line('x','{}',max_tokens=256)
        from bountyforge.nextgen_repair import TrialStatementModel
        with self.assertRaises(ValueError):TrialStatementModel(timeout_seconds=120)

    def test_free_host_gate_blocks_before_queue_download_or_inference(self):
        from scripts import nextgen_comparison as comparison
        with tempfile.TemporaryDirectory() as d,patch.dict(comparison.os.environ,{},clear=True), \
             patch.object(comparison,'LocalRuntime') as runtime,patch.object(comparison,'OwnedRepairQueue') as queue:
            output=Path(d)/'report.json'
            self.assertEqual(comparison.main(['--experiment-sha256','0'*64,'--output',str(output)]),1)
            runtime.assert_not_called();queue.assert_not_called()
            report=json.loads(output.read_bytes())
            self.assertIsNone(report['independent_accuracy']);self.assertEqual(report['models'],[])

    def test_original_frozen_evidence_remains_verifiable(self):
        from bountyforge.model_comparison_evidence import load_record,summarize
        from bountyforge.repair_engines import ROOT,digest
        for run in (40007714754,40009784193,40012667306,40014549114):
            raw=(ROOT/f'evidence/phase15/comparison_{run}.json').read_bytes()
            record=load_record(raw,digest(raw))
            self.assertEqual(sum(r['verified_repairs'] for r in summarize(record)['models']),0)

