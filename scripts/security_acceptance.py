"""Machine-readable results for the owner's sixteen operational failure scenarios.

Tests inject scripted model faults; this report is NOT a real-Qwen benchmark.
Live Docker denial probes and hosted real-model acceptance are separate evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import subprocess
import unittest
from pathlib import Path

SCENARIOS = (
 ('successful_synthetic_repair','tests.test_auto_scope.AutoScopeTests.test_end_to_end_controlled_auto_repair','scripted_model'),
 ('incorrect_model_output','tests.test_worker.WorkerTests.test_bad_patch_cannot_pass','scripted_model'),
 ('model_timeout','tests.test_operational_controls.OperationalControls.test_model_timeout_stops_after_one_request','injected_timeout'),
 ('model_server_unavailable','tests.test_worker.WorkerTests.test_model_unavailable','injected_unavailability'),
 ('ambiguous_source_target','tests.test_auto_scope.AutoScopeTests.test_ambiguous_source_fails_closed','owned_fixture'),
 ('invalid_patch','tests.test_lineedit.LineEditTests.test_invalid_python_rejected','validator'),
 ('unapproved_file_modification','tests.test_worker.WorkerTests.test_forged_test_patch_denied','scripted_model'),
 ('regression_failure','tests.test_operational_controls.OperationalControls.test_partial_repair_fails_related_regression','owned_fixture'),
 ('duplicate_opportunity','tests.test_durable.DurableTests.test_discoveries_deduplicate_without_execution_authority','independent_state_readers'),
 ('expired_queue_lease','tests.test_queue.QueueTests.test_lease_recovery','expired_timestamp_injection'),
 ('missing_funding_verification','tests.test_qualification.QualificationTests.test_good_facts_do_not_authorize_submission','qualification_gate'),
 ('missing_ai_authorization','tests.test_opportunities.OpportunityTests.test_missing_ai_policy_blocks','qualification_gate'),
 ('unsafe_test_environment','tests.test_curated_docker.CuratedDockerTests.test_missing_docker_fails_closed','missing_runtime_injection'),
 ('evidence_tampering','tests.test_autonomy.AutonomyTests.test_digest_rejects_modified_valid_record','tampered_evidence'),
 ('resource_budget_exhaustion','tests.test_operational_controls.OperationalControls.test_model_attempt_budget_exhaustion','scripted_model'),
 ('interrupted_workflow_recovery','tests.test_durable.DurableTests.test_interrupted_job_recovers_and_old_completion_is_rejected','new_ledger_instance'),
)


def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv)
 results=[]
 for name,test,mechanism in SCENARIOS:
  suite=unittest.defaultTestLoader.loadTestsFromName(test)
  stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=0).run(suite)
  passed=result.wasSuccessful() and result.testsRun==1 and not result.skipped
  results.append({'scenario':name,'test':test,'mechanism':mechanism,'passed':passed,
                  'tests_run':result.testsRun,'failure_count':len(result.failures),'error_count':len(result.errors)})
 report={'kind':'scripted_operational_fault_acceptance','revision':os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         'scenarios':results,'passed':sum(x['passed'] for x in results),'total':len(results),
         'real_qwen_test':False,'external_submissions':0,'paid_inference':False}
 raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode()
 envelope={'record':report,'record_sha256':hashlib.sha256(raw).hexdigest()}
 with args.output.open('x') as f: json.dump(envelope,f,indent=2);f.write('\n')
 print('Operational failure scenarios:',report['passed'],'/',report['total'])
 return 0 if all(x['passed'] for x in results) else 1

if __name__=='__main__': raise SystemExit(main())
