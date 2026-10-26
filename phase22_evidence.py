"""Pinned real Phase22 provider receipts and model-free independent replay.

This module never constructs an API client, reads a credential or spends credits.
Hash binding proves recorded identity, not a provider signature or unseen accuracy.
"""
import argparse
import hashlib
import json
from pathlib import Path
from bountyforge.repair_engines import receipt_hash,strict_json
from phase22_repair import catalog,OwnedSession
from phase22_deepseek import cost_upper,MAX_INPUT,MAX_OUTPUT

ROOT=Path(__file__).resolve().parent
PLAN_SHA256='a12648b59de913b18d358e94d2cd6abc482c6c86086765871bf52c8bef27b322'
ORIGIN_SHA256='bed6ea807c295632684bcd4a0a9cd6c68f575e52fe7249e971dbe64f0c99d955'
LEDGER_SHA256='96392bbf7c281d1e18204ce1b40f23868b4c542021bde110faf10c89c46f42c9'


def _check(condition,code):
    if not condition:raise ValueError(code)


def analyze(record,ledger):
    _check(record.get('receipt_sha256')==receipt_hash(record) and ledger.get('receipt_sha256')==receipt_hash(ledger),'EVIDENCE_RECEIPT_HASH_REJECTED')
    _check(record.get('plan_sha256')==ledger.get('plan_sha256')==PLAN_SHA256,'FROZEN_PLAN_IDENTITY_REJECTED')
    _check(record.get('status')=='COMPLETED' and record.get('model')=='deepseek-v4-pro'
           and record.get('provider')=='https://api.deepseek.com'
           and record.get('authorship_basis')=='authenticated_provider_response','COMPLETED_PROVIDER_TRIAL_REQUIRED')
    specs=catalog().tasks()
    _check([r['case_id'] for r in record['cases']]==[s['id'] for s in specs],'COMPLETE_FROZEN_TASK_SET_REQUIRED')
    rows=ledger.get('requests',[]);by_id={r['id']:r for r in rows}
    _check(0<len(rows)<=12 and len(by_id)==len(rows),'LEDGER_REQUEST_SET_REJECTED')
    seen=set();cases=[];usage={'prompt_tokens':0,'completion_tokens':0,'reasoning_tokens':0,'prompt_cache_hit_tokens':0,'prompt_cache_miss_tokens':0}
    missing_reasoning=0;known_cost=0;api_seconds=0;verification_seconds=0
    valid=invalid=repeated=incorrect=regressive=0
    for row,spec in zip(record['cases'],specs):
        task=row['task'];previous=None;success=[]
        _check(task['case_id']==spec['id'] and task['source_sha256']==spec['sha256']['subject.py']
               and task['tests_sha256']==spec['sha256']['tests/test_regression.py'],'TASK_SOURCE_OR_TEST_IDENTITY_REJECTED')
        _check(1<=len(row['attempts'])<=2,'TASK_REQUEST_LIMIT_REJECTED')
        for position,entry in enumerate(row['attempts'],1):
            g=entry['generation'];v=entry['verification'];reservation=g['reservation'];rid=reservation['id'];l=by_id.get(rid)
            _check(l is not None and rid not in seen and l['case_id']==row['case_id'] and l['attempt']==position
                   and reservation['attempt']==position and reservation['reserved_microusd']==l['reserved_microusd']==37848,'GENERATION_USAGE_NOT_LEDGER_BOUND')
            seen.add(rid)
            _check(g.get('http_completion_dispatched') is True and g.get('status')=='RETURNED_CANDIDATE'
                   and g.get('provider')=='https://api.deepseek.com' and g.get('model')=='deepseek-v4-pro'
                   and bool(g.get('provider_response_id')),'AUTHENTICATED_RESPONSE_ROUTE_UNCONFIRMED')
            _check(g.get('returned_candidate')==v.get('proposal'),'PROVIDER_CANDIDATE_SUBSTITUTED')
            u=g['usage'];_check(u==l['usage'],'PROVIDER_USAGE_SUBSTITUTED')
            _check(type(u['prompt_tokens']) is int and 0<=u['prompt_tokens']<=MAX_INPUT
                   and type(u['completion_tokens']) is int and 0<=u['completion_tokens']<=MAX_OUTPUT
                   and u['total_tokens']==u['prompt_tokens']+u['completion_tokens'],'USAGE_ENVELOPE_REJECTED')
            _check(u.get('reasoning_tokens') is None or (type(u['reasoning_tokens']) is int and 0<=u['reasoning_tokens']<=u['completion_tokens']),'REASONING_TOKEN_COUNT_REJECTED')
            _check(all(type(u.get(k)) is int and 0<=u[k]<=u['prompt_tokens'] for k in ('prompt_cache_hit_tokens','prompt_cache_miss_tokens'))
                   and u['prompt_cache_hit_tokens']+u['prompt_cache_miss_tokens']==u['prompt_tokens'],'CACHE_TOKEN_COUNT_REJECTED')
            cost=cost_upper('deepseek-v4-pro',u['prompt_tokens'],u['completion_tokens'])
            _check(cost==l['accounted_upper_microusd']==g['cost_upper_microusd'],'COST_ACCOUNTING_REJECTED')
            known_cost+=cost;api_seconds+=g['seconds'];verification_seconds+=v['seconds']
            for name in usage:
                if u.get(name) is None:
                    if name=='reasoning_tokens':missing_reasoning+=1
                else:
                    _check(type(u[name]) is int and u[name]>=0,'TOKEN_USAGE_REJECTED');usage[name]+=u[name]
            _check(v['receipt_sha256']==receipt_hash(v) and v['source_sha256']==task['source_sha256']
                   and v['tests_sha256']==task['tests_sha256'] and v['engine']=='DEEPSEEK_API'
                   and v['previous_receipt_sha256']==previous,'VERIFIER_RECEIPT_IDENTITY_REJECTED')
            previous=v['receipt_sha256'];positive=v.get('independently_verified') is True
            _check(positive==(v.get('outcome')=='VERIFIED'),'INCONSISTENT_SUCCESS_CLAIM')
            if positive:
                _check(v.get('state')=='AWAITING_OWNER_APPROVAL' and all(v.get(stage,{}).get('passed') is True
                    and v[stage].get('tests_run')==8 and v[stage].get('exit_code')==0 for stage in ('targeted','independent')),'INDEPENDENT_REPLAY_REQUIRED')
            if 'targeted' in v:valid+=1
            if v['outcome']=='SOURCE_REJECTED':invalid+=1
            if v['outcome']=='REPEATED_PROPOSAL':repeated+=1
            if v['outcome']=='TEST_FAILED':
                incorrect+=1
                base=set(task['baseline_feedback'].get('failing_tests',[]));now=set(v.get('test_feedback',{}).get('failing_tests',[]))
                regressive+=bool(now-base)
            success.append(positive)
        _check(row.get('verified')==any(success),'CASE_SUCCESS_NOT_VERIFIER_BOUND')
        cases.append({'case_id':row['case_id'],'source_sha256':task['source_sha256'],'tests_sha256':task['tests_sha256'],
                      'attempts':len(success),'verified':any(success),'first_attempt_success':success[0],
                      'retry_assisted_success':not success[0] and any(success)})
    _check(seen==set(by_id) and record['actual_http_completion_attempts']==len(seen)
           and record['budget']['committed_microusd']==known_cost and record['budget']['unknown_requests']==0,'INCOMPLETE_REQUEST_ACCOUNTING')
    if missing_reasoning:usage['reasoning_tokens']=None
    return {'kind':'PHASE22_REAL_PROVIDER_DEVELOPMENTAL_COMPARISON','model':'deepseek-v4-pro',
            'measurement_status':'COMPLETED','plan_sha256':PLAN_SHA256,'tasks_attempted':len(cases),'cases':cases,
            'verified_repairs':sum(c['verified'] for c in cases),'first_attempt_successes':sum(c['first_attempt_success'] for c in cases),
            'retry_assisted_successes':sum(c['retry_assisted_success'] for c in cases),'valid_source_proposals':valid,
            'invalid_proposals':invalid,'repeated_proposals':repeated,'incorrect_tested_proposals':incorrect,
            'proposals_with_newly_reported_regressions':regressive,'actual_http_completion_attempts':len(seen),'usage':usage,
            'accounted_peak_cost_upper_microusd':known_cost,'provider_confirmed_per_request_cost':None,
            'observed_end_account_balance':record.get('after_balance'),'observed_initial_account_balance':record['before']['balance'],
            'observed_account_balance_delta_microusd':record.get('observed_account_balance_delta_microusd'),
            'balance_delta_is_exact_cost':False,'api_completion_roundtrip_seconds':round(api_seconds,3),
            'verification_seconds':round(verification_seconds,3),'full_cycle_seconds':record['elapsed_seconds'],
            'trusted_controller_cpu_seconds':record['trusted_controller_cpu_seconds'],
            'trusted_controller_peak_rss_bytes':record['trusted_controller_peak_rss_bytes'],
            'provider_cpu_memory':'NOT_EXPOSED_BY_API','independent_unseen_evaluation':False,'additional_cash_spending_usd':0,
            'commercial_admission':'NOT_ADMITTED','historical_head_to_head_comparable':False,
            'historical_comparison_limitation':'Phase21 Qwen/Granite used different tasks and context/output limits; no controlled model superiority estimate.'}


def load_origin():
    from phase22_run import load_plan
    load_plan(PLAN_SHA256)  # Identity only; historical replay never refreshes live pricing.
    values=[]
    for name,pin in (('deepseek-pro-trial.json',ORIGIN_SHA256),('live-ledger-summary.json',LEDGER_SHA256)):
        path=ROOT/'evidence/phase22'/name;raw=path.read_bytes()
        _check(not path.is_symlink() and hashlib.sha256(raw).hexdigest()==pin,'PINNED_PROVIDER_ORIGIN_REJECTED')
        values.append(strict_json(raw))
    analyze(*values)
    return values


def replay(admitted=False):
    if admitted is not True:raise ValueError('EXPLICIT_RECORDED_DEEPSEEK_REPLAY_REQUIRED')
    record,_=load_origin();service=OwnedSession();rows=[]
    for row in record['cases']:
        task=service.prepare(row['case_id']);attempts=[]
        for entry in row['attempts']:
            old=entry['verification'];now=service.submit(task,entry['generation']['returned_candidate'])
            matched=(now.get('candidate_sha256')==old.get('candidate_sha256') and now['outcome']==old['outcome']
                     and now['independently_verified']==old['independently_verified'])
            attempts.append({'matched_original':matched,'original_verifier_receipt_sha256':old['receipt_sha256'],'verification':now})
            task=service.current(row['case_id'])
        rows.append({'case_id':row['case_id'],'attempts':attempts})
    return {'kind':'PHASE22_RECORDED_DEEPSEEK_CANDIDATE_REPLAY','status':'PASSED' if all(a['matched_original'] for r in rows for a in r['attempts']) else 'FAILED',
            'cases':rows,'new_inference_requests':0,'new_model_generated_repairs':0,'origin_sha256':ORIGIN_SHA256,
            'original_unique_developmental_repairs':6,'independent_unseen_evaluation':False,'commercial_admission':'NOT_ADMITTED'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('report','replay'))
    p.add_argument('--admit-recorded-deepseek-replay',action='store_true');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    if args.operation=='replay':result=replay(args.admit_recorded_deepseek_replay)
    else:result=analyze(*load_origin())
    result['receipt_sha256']=receipt_hash(result);args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('kind','status','verified_repairs','new_inference_requests','new_model_generated_repairs') if k in result}))
    return 0 if result.get('status','PASSED')=='PASSED' else 1


if __name__=='__main__':raise SystemExit(main())
