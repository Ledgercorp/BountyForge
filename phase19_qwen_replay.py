"""Replay the exact recorded Qwen candidate on another credential-free host.

No inference, new repair claim, customer input, model asset or SDK is required.
"""
import argparse
import json
from pathlib import Path
from phase19_qwen_handoff import ROOT,EXPERIMENT,validate_experiment

ORIGIN=ROOT/'evidence/phase19/qwen-owned-handoff.json'
ORIGIN_SHA='d72a3a937c9595bee9f2c656cb238f20e23b4d1d0254cf0de6f08224f2c411ec'


def validate_origin(record):
    from bountyforge.repair_engines import receipt_hash
    if record.get('receipt_sha256')!=ORIGIN_SHA or receipt_hash(record)!=ORIGIN_SHA:
        raise ValueError('RECORDED_MODEL_ORIGIN_REJECTED')
    return record['calls'][0]


def replay(enabled=False):
    if enabled is not True:raise ValueError('EXPLICIT_RECORDED_OWNED_REPLAY_REQUIRED')
    from bountyforge.phase8_evaluation import require_credential_free_host
    require_credential_free_host()
    config=validate_experiment(EXPERIMENT.read_bytes())
    origin=json.loads(ORIGIN.read_text());call=validate_origin(origin)
    from bountyforge.repair_engines import RepairService,receipt_hash
    from deepseek_owned_bridge import verify_owned_harness_response
    service=RepairService();task=service.prepare(config['case_id'],'CODEX_AGENT')
    if any(task[k]!=config[k] for k in ('source_sha256','tests_sha256')):
        raise ValueError('FROZEN_REPLAY_TASK_CHANGED')
    verified=verify_owned_harness_response(service,task,call['effective_proposal'],allow_owned_verification=True)
    receipt=verified['owned_verifier_receipt']
    same=receipt.get('candidate_sha256')==call['verification']['owned_verifier_receipt']['candidate_sha256']
    result={'kind':'PHASE19_RECORDED_MODEL_CANDIDATE_REPLAY',
        'status':'PASSED' if same and receipt['independently_verified'] else 'REPLAY_FAILED',
        'origin_receipt_sha256':ORIGIN_SHA,'model_response_sha256':call['response_sha256'],
        'candidate_author':'QWEN_LOCAL','same_candidate_sha256':same,'new_model_requests':0,
        'new_model_generated_repairs':0,'replay_of_existing_developmental_result':True,
        'verification':verified,'commercial_admission':'NOT_ADMITTED','additional_spending_usd':0}
    result['receipt_sha256']=receipt_hash(result)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--admit-recorded-owned-replay',action='store_true');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    if not args.admit_recorded_owned_replay:p.error('Explicit owned replay admission required')
    result=replay(True);args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':result['status'],'new_model_requests':0,'new_model_generated_repairs':0}))
    return 0 if result['status']=='PASSED' else 1


if __name__=='__main__':raise SystemExit(main())
