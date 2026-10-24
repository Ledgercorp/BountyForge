"""Replay hash-pinned recorded model candidates; no SDK or new inference."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ORIGINS={
    'chunk-count-native.json':'8be66779f8399b0fff483d610dfa127eb0838177b559a476a935603b5fcb6e2d',
    'optional-setting-external.json':'ab4d933b86ee30a020ff584aa4da50834f0d3e0e370fab9cd0f83e5dfd225c3e',
    'reading-groups-native.json':'669924c01bfe160109e12f4286c2804407e609556532dc7afb02c87d973dfc60',
}


def validate_origin(filename,record):
    from bountyforge.repair_engines import receipt_hash
    if filename not in ORIGINS or record.get('receipt_sha256')!=ORIGINS[filename] or receipt_hash(record)!=ORIGINS[filename]:
        raise ValueError('RECORDED_MODEL_ORIGIN_REJECTED')
    case=record['cases'][0] if 'cases' in record else record
    call=case['attempts'][0]
    verifier=call['verification']['owned_verifier_receipt']
    if receipt_hash(verifier)!=verifier['receipt_sha256']:raise ValueError('RECORDED_VERIFIER_IDENTITY_REJECTED')
    return case,call,verifier


def replay(enabled=False):
    if enabled is not True:raise ValueError('EXPLICIT_RECORDED_OWNED_REPLAY_REQUIRED')
    from bountyforge.phase8_evaluation import require_credential_free_host
    from bountyforge.repair_engines import RepairService,receipt_hash
    from deepseek_owned_bridge import verify_owned_harness_response
    require_credential_free_host()
    rows=[]
    for filename in ORIGINS:
        case,call,old=validate_origin(filename,json.loads((ROOT/'evidence/phase20'/filename).read_text()))
        service=RepairService();task=service.prepare(case['case_id'],'CODEX_AGENT')
        if any(task[k]!=case['task'][k] for k in ('source_sha256','tests_sha256')):
            raise ValueError('FROZEN_REPLAY_TASK_CHANGED')
        proposal=call.get('effective_proposal',call.get('sdk_final_response',call.get('model_response')))
        result=verify_owned_harness_response(service,task,proposal,allow_owned_verification=True)
        now=result['owned_verifier_receipt']
        same=now.get('candidate_sha256')==old['candidate_sha256']
        matches=same and now['outcome']==old['outcome'] and now['independently_verified']==old['independently_verified']
        rows.append({'case_id':case['case_id'],'origin_receipt_sha256':ORIGINS[filename],
            'candidate_author':case['candidate_author'],'same_candidate_sha256':same,
            'expected_outcome':old['outcome'],'matched_expected_outcome':matches,'verification':result})
    record={'kind':'PHASE20_RECORDED_MODEL_CANDIDATE_REPLAY','status':'PASSED' if all(r['matched_expected_outcome'] for r in rows) else 'FAILED',
        'new_model_requests':0,'new_model_generated_repairs':0,'replay_of_existing_developmental_results':True,
        'independent_evaluation':False,'cases':rows,'commercial_admission':'NOT_ADMITTED','additional_spending_usd':0}
    record['receipt_sha256']=receipt_hash(record)
    return record


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admit-recorded-owned-replay',action='store_true');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if not args.admit_recorded_owned_replay:parser.error('Explicit recorded owned replay admission required')
    result=replay(True);args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':result['status'],'new_model_requests':0,'new_model_generated_repairs':0}))
    return 0 if result['status']=='PASSED' else 1


if __name__=='__main__':raise SystemExit(main())
