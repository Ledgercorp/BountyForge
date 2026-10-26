"""Offline audit of the frozen metadata preparation; grants no execution authority."""
import hashlib
import json
from pathlib import Path
from bountyforge.evaluation_control import test_ids
from bountyforge.repair_engines import encoded,receipt_hash,strict_json

ROOT=Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    contract=strict_json((root/'evidence/phase23-25/evaluation-contract.json').read_bytes())
    path=root/'evidence/phase23-25/historical-registry.json';raw=path.read_bytes();registry=strict_json(raw)
    if hashlib.sha256(raw).hexdigest()!=contract['historical_registry_sha256']:
        raise ValueError('FROZEN_REGISTRY_CHANGED')
    for name,expected in contract['frozen_files'].items():
        if name not in ('bountyforge/evaluation_control.py','scripts/prepare_historical_registry.py','scripts/verify_historical_registry.py'):
            raise ValueError('UNEXPECTED_PREPARATION_FILE')
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:raise ValueError('FROZEN_PREPARATION_CHANGED')
    if (registry['receipt_sha256']!=receipt_hash(registry) or registry['accuracy'] is not None
            or registry['functional_baselines_executed']!=0 or registry['actual_inference_requests']!=0
            or registry['paid_requests_authorized']!=0 or registry['independently_unseen'] is not False
            or registry['upstream_code_executed'] is not False or registry['reference_material_persisted'] is not False
            or registry['commercial_admission']!='NOT_ADMITTED' or contract['paid_requests_authorized']!=0):
        raise ValueError('PREPARATION_ONLY_DENIAL_CHANGED')
    tasks=registry['tasks'];identities=set();repos=set()
    fields={'base_commit','contamination_warnings','execution_admitted','expected_failing_tests','independently_unseen',
            'instance_id','metadata_observation_sha256','problem_sha256','reference_material_persisted','repo',
            'required_regressions','source_license','test_identity_sha256'}
    for task in tasks:
        fail=test_ids(task['expected_failing_tests']);passed=test_ids(task['required_regressions'])
        if (set(task)!=fields or task['instance_id'] in identities or set(fail)&set(passed)
                or task['test_identity_sha256']!=hashlib.sha256(encoded({'fail':fail,'pass':passed})).hexdigest()
                or task['execution_admitted'] is not False or task['independently_unseen'] is not False
                or task['reference_material_persisted'] is not False or task['source_license']['file_and_dependency_rights_admitted'] is not False):
            raise ValueError('TASK_IDENTITY_OR_ADMISSION_CHANGED')
        identities.add(task['instance_id']);repos.add(task['repo'])
    if len(tasks)!=contract['task_count'] or registry['task_count']!=len(tasks) or sorted(repos)!=registry['repos']:
        raise ValueError('INCOMPLETE_FROZEN_TASK_SET')
    return {'kind':'PHASE23_OFFLINE_PREPARATION_AUDIT','status':'PASSED','tasks':len(tasks),'repositories':len(repos),
            'functional_baselines_run':0,'inference_requests':0,'execution_admitted':False,'unseen_accuracy':None}


if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
