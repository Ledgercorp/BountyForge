"""Read-only Phase21 accounting. Replay and simulated traffic are not repairs."""
import argparse
import hashlib
import json
from pathlib import Path
from bountyforge.repair_engines import receipt_hash,strict_json
from bountyforge.model_profiles import profile_spec
from phase21_runner import CASES,ALL_ARMS

ROOT=Path(__file__).resolve().parent
PLANS={'QWEN_COMPARISON':'6ff122f2d457bbe1cac42d843ab82f6ae711c2036cf6e0aa6d0e64ad24fe84fe',
       'GRANITE_TRIAL':'dcdedf899f342d9e1c96d2cec3a2b88c1392517d3b5f1863416205b9ac852912'}


def verified_receipt(receipt,source_sha,tests_sha,tests):
    if (receipt.get('receipt_sha256')!=receipt_hash(receipt) or receipt.get('source_sha256')!=source_sha
            or receipt.get('tests_sha256')!=tests_sha):raise ValueError('VERIFIER_IDENTITY_REJECTED')
    positive=receipt.get('independently_verified') is True or receipt.get('outcome')=='VERIFIED'
    if positive:
        if (receipt.get('independently_verified') is not True or receipt.get('outcome')!='VERIFIED'
                or receipt.get('state')!='AWAITING_OWNER_APPROVAL'
                or any(receipt.get(stage,{}).get('passed') is not True
                    or receipt[stage].get('exit_code')!=0 or receipt[stage].get('tests_run')!=tests
                    for stage in ('targeted','independent'))):raise ValueError('UNVERIFIED_SUCCESS_CLAIM')
    return positive


def success_counts(rows):
    return {'verified_repairs':sum(r['verified'] for r in rows),
        'first_attempt_successes':sum(r['first_attempt_verified'] for r in rows),
        'retry_assisted_successes':sum(r['retry_assisted'] for r in rows)}


def resource_summary(raw):
    if raw is None:return None
    cpu=dict(line.split() for line in raw['cpu.stat'].splitlines())
    return {'cgroup_memory_peak_bytes':int(raw['memory.peak']),
        'cgroup_cpu_usage_seconds':int(cpu['usage_usec'])/1e6,'pids_peak':int(raw['pids.peak'])}


def case_summary(r,spec):
    if (r.get('receipt_sha256')!=receipt_hash(r) or r.get('kind')!='PHASE21_OWNED_MODEL_ARM'
            or r['case_id']!=spec['id'] or r['arm'] not in ALL_ARMS):raise ValueError('MODEL_ARM_IDENTITY_REJECTED')
    profile='GRANITE42_3B' if r['arm']=='GRANITE_DIAG' else 'QWEN_1_5B'
    plan=PLANS['GRANITE_TRIAL' if profile=='GRANITE42_3B' else 'QWEN_COMPARISON']
    if (r['model_profile']!=profile or r['model_sha256']!=profile_spec(profile)['sha256']
            or r['experiment_sha256']!=plan or r['task']['source_sha256']!=spec['sha256']['subject.py']
            or r['task']['tests_sha256']!=spec['sha256']['tests/test_regression.py']
            or hashlib.sha256(r['task']['source'].encode()).hexdigest()!=r['task']['source_sha256']):
        raise ValueError('FROZEN_ARM_BINDING_CHANGED')
    trace=r.get('model_trace',{});count=trace.get('dispatched');forwarded=[v for v in trace.get('requests',[]) if v.get('completion_forwarded')]
    known=(type(count) is int and 0<=count<=2 and count==len(forwarded)
           and (count>0 or r['status']=='COMPLETED' or 'model_boundary_before' not in r))
    verified=[];attempts=[];baseline=set(r['task']['baseline_feedback']['failing_tests'])
    for index,a in enumerate(r['attempts']):
        response=a['response']
        if (index>=len(forwarded) or forwarded[index].get('response')!=response
                or hashlib.sha256(response.encode()).hexdigest()!=a['response_sha256']):
            raise ValueError('MODEL_RESPONSE_BINDING_CHANGED')
        v=a.get('verification',{}).get('owned_verifier_receipt')
        passed=verified_receipt(v,r['task']['source_sha256'],r['task']['tests_sha256'],8) if v else False
        verified.append(passed)
        failures=set(v.get('test_feedback',{}).get('failing_tests',[])) if v else set()
        attempts.append({'attempt':a['attempt'],'response_sha256':a['response_sha256'],
            'diagnosis':a.get('diagnosis'),'candidate_sha256':v.get('candidate_sha256') if v else None,
            'outcome':v['outcome'] if v else 'HANDOFF_OR_DIAGNOSIS_REJECTED',
            'rejection':a.get('rejection'), 'valid_source_proposal':bool(v and v.get('candidate_sha256')),
            'targeted_passed':bool(v and v.get('targeted',{}).get('passed')),
            'verified':passed,'newly_reported_failures':sorted(failures-baseline),
            'reported_baseline_failures_remaining':sorted(failures&baseline),
            'verification_seconds':a.get('verification_seconds'), 'retained_anchors':a.get('retained_anchors',[])})
    positive=any(verified)
    if positive!=r['independently_verified']:raise ValueError('ARM_SUCCESS_CLAIM_INCONSISTENT')
    if r['status']=='COMPLETED' and (not known or not r['attempts']):raise ValueError('EMPTY_COMPLETED_EXPERIMENT')
    usages=[q.get('usage') for q in forwarded];unknown_usage=sum(v is None for v in usages)
    return {'case_id':r['case_id'],'arm':r['arm'],'origin_receipt_sha256':r['receipt_sha256'],
        'status':r['status'],'failure':r.get('failure'),'model_profile':profile,
        'completion_requests':count if known else None,'maximum_reserved_requests':2,
        'prompt_tokens_known':sum(u['prompt_tokens'] for u in usages if u is not None),
        'completion_tokens_known':sum(u['completion_tokens'] for u in usages if u is not None),'requests_with_unknown_usage':unknown_usage,
        'tokenized_input_tokens':sum(q['rendered_prompt_tokens'] for q in forwarded),
        'returned_model_responses':sum('response' in q for q in forwarded),
        'gateway_seconds':round(sum(q['seconds'] for q in trace.get('requests',[])),3),
        'cycle_wall_seconds':r['cycle_wall_seconds'],'preparation_seconds':r['preparation_seconds'],
        'verified':positive,'first_attempt_verified':bool(verified and verified[0]),
        'retry_assisted':positive and not verified[0],'attempts':attempts,
        'model_resources':resource_summary(r.get('model_resources')),'sdk_resources':resource_summary(r.get('sdk_resources')),
        'model_process_memory':r.get('model_process_memory'),'sdk_process_memory':r.get('sdk_process_memory'),
        'cleanup_confirmed':r['cleanup_confirmed'],
        'output_limit_finishes':sum(q.get('finish_reason')=='length' for q in forwarded),
        'boundary_observations_complete':all(k in r for k in ('model_boundary_before','model_boundary_after'))
            and (r['arm']=='EXTERNAL_BASE' or all(k in r for k in ('sdk_boundary_before','sdk_boundary_after','startup_tool_audit')))}


def build():
    specs={s['id']:s for s in strict_json((ROOT/'fixtures/phase21/manifest.json').read_bytes())['cases']}
    rows=[]
    for path in sorted((ROOT/'evidence/phase21/results').glob('*.json')):
        if path.is_symlink() or path.stat().st_size>512*1024:raise ValueError('BOUNDED_REGULAR_RESULT_REQUIRED')
        r=strict_json(path.read_bytes())
        if r.get('case_id') not in CASES or r.get('arm') not in ALL_ARMS or path.name!=r['case_id']+'--'+r['arm']+'.json':
            raise ValueError('UNAUTHORIZED_RESULT_PATH')
        rows.append(case_summary(r,specs[r['case_id']]))
    summary={}
    for arm in ALL_ARMS:
        selected=[r for r in rows if r['arm']==arm];attempts=[a for r in selected for a in r['attempts']]
        unknown=sum(r['completion_requests'] is None for r in selected)
        summary[arm]={'planned_tasks':4,'recorded_tasks':len(selected),'completed_tasks':sum(r['status']=='COMPLETED' for r in selected),
            **success_counts(selected),'model_requests':None if unknown else sum(r['completion_requests'] for r in selected),
            'request_count_unknown_cases':unknown,'prompt_tokens_known':sum(r['prompt_tokens_known'] for r in selected),
            'completion_tokens_known':sum(r['completion_tokens_known'] for r in selected),
            'tokenized_input_tokens':sum(r['tokenized_input_tokens'] for r in selected),
            'returned_model_responses':sum(r['returned_model_responses'] for r in selected),
            'requests_with_unknown_usage':sum(r['requests_with_unknown_usage'] for r in selected),
            'valid_source_proposals':sum(a['valid_source_proposal'] for a in attempts),
            'invalid_proposals':sum(a['outcome'] in ('SOURCE_REJECTED','HANDOFF_OR_DIAGNOSIS_REJECTED') for a in attempts),
            'repeated_proposals':sum(a['outcome']=='REPEATED_PROPOSAL' for a in attempts),
            'incorrect_tested_proposals':sum(a['outcome'] in ('TEST_FAILED','INDEPENDENT_VERIFICATION_FAILED') for a in attempts),
            'proposals_with_newly_reported_regressions':sum(bool(a['newly_reported_failures']) for a in attempts),
            'targeted_test_passes':sum(a['targeted_passed'] for a in attempts),
            'gateway_seconds':round(sum(r['gateway_seconds'] for r in selected),3),
            'cycle_wall_seconds':round(sum(r['cycle_wall_seconds'] for r in selected),3),
            'output_limit_finishes':sum(r['output_limit_finishes'] for r in selected),
            'incomplete_boundary_observations':sum(not r['boundary_observations_complete'] for r in selected)}
    status=('UNMEASURED' if not rows else ('COMPLETE' if len(rows)==len(CASES)*len(ALL_ARMS)
        and all(r['status']=='COMPLETED' for r in rows) else 'PARTIAL_OR_BLOCKED'))
    result={'kind':'PHASE21_FROZEN_DEVELOPMENT_MEASUREMENTS','measurement_status':status,
        'independent_unseen_evaluation':False,'arms':summary,'cases':rows,
        'additional_spending_usd':0,'confirmed_revenue_usd':0,'commercial_admission':'NOT_ADMITTED','default_model_changed':False,
        'limitations':['Developmental owned material visible to Codex; no independently inaccessible held-out store.',
            'Native SDK retains required context and prior turns; external requests contain only the current prompt.',
            'Diagnosis shares output/context budget; all arms have at most two requests per task.',
            'Newly reported test failures are bounded feedback witnesses, not exhaustive software regression proof.',
            'Cgroup peaks and process VmHWM are separate metrics; missing data is null, not zero.',
            'Cgroup CPU includes contained observation processes; trusted host-verifier CPU was not separately measured.',
            'Gateway time includes tokenization/transport/generation. Complete-cycle time includes admission and verification.',
            'Warm-cache/order effects and small sample preclude a causal generalization or default-model claim.',
            'Protocol simulations, blocked preflight runs and recorded replay are excluded from model accuracy.',
            'Hash binding does not establish an authenticated runtime signature or cryptographic authorship identity.']}
    result['receipt_sha256']=receipt_hash(result)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv)
    r=build();args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r['arms'],sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
