"""Explicit two-request Qwen experiment through the Phase16 output bridge.

Not a native SDK provider or a new engine. The fixed exposed owned case is
developmental. No reference patch, customer input, API credential or fallback.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import time

ROOT=Path(__file__).resolve().parent
EXPERIMENT=ROOT/'phase19/owned_qwen_experiment.json'
EXPERIMENT_SHA='9cbba663265a33043949f3e477d838f12791a7acfeb3d11233c73776a4b0db34'
SDK_RECEIPT=ROOT/'evidence/phase19/github-sdk-40040762452.json'


def validate_experiment(raw):
    if hashlib.sha256(raw).hexdigest()!=EXPERIMENT_SHA:raise ValueError('FROZEN_EXPERIMENT_CHANGED')
    return json.loads(raw)


def validate_sdk_receipt(record):
    from bountyforge.repair_engines import receipt_hash
    from phase19_sdk_acceptance import validate_audit
    from phase17_isolation import validate_observation
    from phase19_native_binding import BINDING_SHA,CARRIER_SHA
    if record.get('receipt_sha256')!=receipt_hash(record):raise ValueError('SDK_RECEIPT_HASH_REJECTED')
    if (record.get('kind')!='PHASE19_MODEL_FREE_SDK_ACCEPTANCE' or record.get('status')!='PASSED'
            or any(record.get(k) is not True for k in ('initialize_confirmed','shutdown_confirmed','container_absent_after_cleanup'))
            or record.get('exit_code')!=0 or record.get('model_requests')!=0):
        raise ValueError('SDK_RUNTIME_NOT_VERIFIED')
    validate_audit(record.get('runtime_audit'))
    validate_observation(json.dumps(record.get('boundary')))
    native=record.get('native_cache',{})
    if native.get('binding_sha256')!=BINDING_SHA or native.get('carrier_sha256')!=CARRIER_SHA:
        raise ValueError('SDK_NATIVE_IDENTITY_REJECTED')


def validate_capacity(cpus,memory_kib,disk_bytes):
    if cpus<2 or memory_kib<3*1024**2 or disk_bytes<2*1024**3:
        raise ValueError('LOCAL_CAPACITY_UNAVAILABLE')


def run(enabled=False):
    if enabled is not True:raise ValueError('EXPLICIT_OWNED_MODEL_EXPERIMENT_REQUIRED')
    from bountyforge.phase8_evaluation import require_credential_free_host
    require_credential_free_host()
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        raise ValueError('LINUX_X64_REQUIRED')
    config=validate_experiment(EXPERIMENT.read_bytes())
    sdk=json.loads(SDK_RECEIPT.read_text());validate_sdk_receipt(sdk)
    memory=int(next(r.split()[1] for r in Path('/proc/meminfo').read_text().splitlines() if r.startswith('MemAvailable:')))
    cpus=os.cpu_count() or 0;disk=shutil.disk_usage(Path.home()).free
    validate_capacity(cpus,memory,disk)
    from bountyforge.local_model_runtime import LocalRuntime
    from bountyforge.profiled_qwen import ProfiledStatementModel
    from bountyforge.repair_engines import RepairService,qwen_availability,receipt_hash
    from bountyforge.repair_intelligence import compact_model_prompt,revision_proposal
    from bountyforge.statements import SYSTEM
    from deepseek_owned_bridge import verify_owned_harness_response
    from deepseek_harness_handoff import HarnessHandoffRejected
    began=time.monotonic()
    # CODEX_AGENT here is the bridge's existing session-submission capability,
    # not an authorship claim. Neither Codex nor the native SDK generates edits.
    service=RepairService();task=service.prepare(config['case_id'],'CODEX_AGENT')
    for key in ('source_sha256','tests_sha256'):
        if task[key]!=config[key]:raise ValueError('FROZEN_OWNED_TASK_CHANGED')
    record={'kind':config['kind'],'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,
        'experiment_sha256':EXPERIMENT_SHA,'sdk_acceptance_receipt_sha256':sdk['receipt_sha256'],
        'candidate_author':'QWEN_LOCAL','model_profile':config['model_profile'],
        'native_sdk_model_requests':0,'codex_generated_candidates':0,
        'submission_capability':'CODEX_AGENT','submission_capability_is_authorship_attestation':False,
        'task':task,'calls':[],'additional_spending_usd':0,'paid_fallback':False,
        'commercial_admission':'NOT_ADMITTED','customer_execution_authorized':False,'delivery_authorized':False,
        'capacity_before_inference':{'cpus':cpus,'available_memory_kib':memory,'disk_free_bytes':disk}}
    previous=None
    with LocalRuntime(config['model_profile'],threads=config['threads']) as runtime:
        if not qwen_availability(config['model_profile']):raise RuntimeError('PINNED_QWEN_ENDPOINT_UNAVAILABLE')
        model=ProfiledStatementModel(timeout_seconds=config['request_seconds'])
        for _ in range(config['maximum_requests']):
            prompt=compact_model_prompt(task,previous)
            call={'prompt':json.loads(prompt),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
            record['calls'].append(call);started=time.monotonic()
            try:
                response=model.complete_line(SYSTEM,prompt,max_tokens=config['maximum_output_tokens_per_request'])
            except (RuntimeError,OSError,ValueError):
                call.update(error='LOCAL_INFERENCE_UNAVAILABLE',metadata=copy.deepcopy(model.last_call),seconds=round(time.monotonic()-started,3))
                break
            call.update(response=response,response_sha256=hashlib.sha256(response.encode()).hexdigest(),
                metadata=copy.deepcopy(model.last_call),seconds=round(time.monotonic()-started,3))
            effective,retained=revision_proposal(previous,response)
            call.update(effective_proposal=effective,retained_anchors=retained)
            try:
                wrapped=verify_owned_harness_response(service,task,effective,allow_owned_verification=True)
            except HarnessHandoffRejected as exc:
                call['handoff_rejection']=str(exc)
                previous={'proposal':response,'outcome':'SOURCE_REJECTED','diagnostic':str(exc)}
                continue
            call['verification']=wrapped
            previous=wrapped['owned_verifier_receipt']
            if previous['state']!='REVISION_REQUIRED':break
            task=copy.deepcopy(service._get(task['task_id'],previous['revision'],'CODEX_AGENT')['public'])
    record['runtime']=runtime.measurement
    receipts=[c['verification']['owned_verifier_receipt'] for c in record['calls'] if 'verification' in c]
    record.update(model_requests=sum((c.get('metadata') or {}).get('completion_requests',0) for c in record['calls']),
        valid_candidates=sum('candidate_sha256' in r for r in receipts),
        independently_verified_owned_repairs=int(any(r['independently_verified'] is True for r in receipts)),
        status='COMPLETED' if record['calls'] and not record['calls'][-1].get('error') else 'INFERENCE_BLOCKED',
        elapsed_seconds=round(time.monotonic()-began,3))
    for field in ('prompt_tokens','completion_tokens'):
        values=[(c.get('metadata') or {}).get(field) for c in record['calls']]
        record[field]=sum(values) if values and all(type(v) is int for v in values) else None
    record['receipt_sha256']=receipt_hash(record)
    return record


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admit-owned-model-experiment',action='store_true')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    if not args.admit_owned_model_experiment:parser.error('Explicit owned model experiment admission required')
    result=run(args.admit_owned_model_experiment)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('status','model_requests','valid_candidates','independently_verified_owned_repairs')}))
    return 0 if result['status']=='COMPLETED' else 1


if __name__=='__main__':raise SystemExit(main())
