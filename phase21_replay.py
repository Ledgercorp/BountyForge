"""Fresh Docker replay of exact recorded Phase21 candidates; zero inference."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from bountyforge.repair_engines import RepairService,receipt_hash,strict_json
from phase21_measurements import ROOT,case_summary
from phase21_runner import CASES,ALL_ARMS


def replay(enabled=False):
    if enabled is not True:raise ValueError('EXPLICIT_RECORDED_OWNED_QUALITY_REPLAY_REQUIRED')
    from bountyforge.phase8_evaluation import require_credential_free_host
    from deepseek_owned_bridge import verify_owned_harness_response
    require_credential_free_host();began=time.monotonic()
    index=strict_json((ROOT/'evidence/phase21/origins.json').read_bytes())
    if index.get('receipt_sha256')!=receipt_hash(index):raise ValueError('ORIGIN_INDEX_HASH_REJECTED')
    specs={s['id']:s for s in strict_json((ROOT/'fixtures/phase21/manifest.json').read_bytes())['cases']}
    rows=[]
    if not index.get('records'):raise ValueError('NO_RECORDED_QUALITY_RESULTS')
    for entry in index['records']:
        if entry['case_id'] not in CASES or entry['arm'] not in ALL_ARMS:raise ValueError('UNAUTHORIZED_REPLAY_CASE')
        filename=entry['case_id']+'--'+entry['arm']+'.json'
        path=ROOT/'evidence/phase21/results'/filename
        if path.is_symlink() or path.stat().st_size>512*1024:raise ValueError('BOUNDED_REGULAR_REPLAY_ORIGIN_REQUIRED')
        raw=path.read_bytes();r=strict_json(raw)
        if hashlib.sha256(raw).hexdigest()!=entry['file_sha256'] or r['receipt_sha256']!=entry['receipt_sha256']:
            raise ValueError('RECORDED_MODEL_ORIGIN_CHANGED')
        case_summary(r,specs[entry['case_id']])
        submitted=[a for a in r['attempts'] if 'verification' in a]
        row={'case_id':r['case_id'],'arm':r['arm'],'origin_receipt_sha256':r['receipt_sha256'],
            'parser_rejections_not_executed':len(r['attempts'])-len(submitted),'attempts':[]}
        if submitted:
            service=RepairService(owned_quality=True);task=service.prepare(r['case_id'],'CODEX_AGENT')
            for a in submitted:
                original=a['verification']['owned_verifier_receipt']
                verified=verify_owned_harness_response(service,task,a['effective_proposal'],allow_owned_verification=True)
                now=verified['owned_verifier_receipt']
                same=(now.get('candidate_sha256')==original.get('candidate_sha256') and now['outcome']==original['outcome']
                    and now['independently_verified']==original['independently_verified'])
                row['attempts'].append({'generation_attempt':a['attempt'],'matched_original':same,
                    'expected_outcome':original['outcome'],'verification':verified})
                if now['state']=='REVISION_REQUIRED':task=service._get(task['task_id'],now['revision'],'CODEX_AGENT')['public']
        rows.append(row)
    good=all(a['matched_original'] for row in rows for a in row['attempts'])
    result={'kind':'PHASE21_RECORDED_CANDIDATE_REPLAY','status':'PASSED' if good else 'FAILED','cases':rows,
        'new_model_requests':0,'new_model_generated_repairs':0,'independent_unseen_evaluation':False,
        'elapsed_seconds':round(time.monotonic()-began,3),'commercial_admission':'NOT_ADMITTED','additional_spending_usd':0,
        'limitations':'Parser/diagnosis-rejected text is not executed. Exact recorded accepted handoffs retain the existing source and Docker gates.'}
    result['receipt_sha256']=receipt_hash(result)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--admit-recorded-quality-replay',action='store_true')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv)
    if not args.admit_recorded_quality_replay:p.error('Explicit recorded owned replay admission required')
    r=replay(True);args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':r['status'],'new_model_requests':0,'new_model_generated_repairs':0}));return 0 if r['status']=='PASSED' else 1


if __name__=='__main__':raise SystemExit(main())
