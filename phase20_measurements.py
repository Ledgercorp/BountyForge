"""Read-only aggregation of the frozen Phase20 real inference receipts."""
import json
from pathlib import Path
from bountyforge.repair_engines import receipt_hash

ROOT=Path(__file__).resolve().parent/'evidence/phase20'
INPUTS={
    'native-demo-v1.json':'a6f8d04a1dc94680040b47b7f78f6e41f7bd81cef3e2c89e992982a3f99cd7f8',
    'optional-setting-native.json':'c83c05ab0ea78d27746c5bb746a189860cf2afe9261691d0327612aaddc7a0bd',
    'reading-groups-native.json':'669924c01bfe160109e12f4286c2804407e609556532dc7afb02c87d973dfc60',
    'reserve-release-native.json':'d353300feb3e23052c9c5a8e5ed5ca68a3156cebab2254e7919e4e10329f6311',
    'optional-setting-external.json':'ab4d933b86ee30a020ff584aa4da50834f0d3e0e370fab9cd0f83e5dfd225c3e',
    'reading-groups-external.json':'c56670f78436da7fed1494cf1f5df1ec2fdabf62bea5fe3e7b854673dd56e151',
    'reserve-release-external.json':'ad06456caf4d7b3e23f62365c5d70d9fca7888ffff2567e655db179f0d3bb7fb',
    'chunk-count-native.json':'8be66779f8399b0fff483d610dfa127eb0838177b559a476a935603b5fcb6e2d',
}
CAUSES={
    ('weighted-mix','NATIVE_SDK'):'OUTPUT_BUDGET_PROTOCOL_CLAMP_AND_POST_TURN_TMPFS_FULL',
    ('optional-setting','NATIVE_SDK'):'WRONG_LOGIC_FALSE_VALUES_STILL_FALL_BACK',
    ('reading-groups','NATIVE_SDK'):'WRONG_LOGIC_TRUTHY_FILTER_AND_OUTER_VALUE_DEPENDENCE',
    ('reading-groups','EXTERNAL_CONTROL'):'WRONG_LOGIC_ZERO_IS_EXCLUDED',
    ('reserve-release','NATIVE_SDK'):'WRONG_STATE_TRANSITION_RELEASE_COUNT_INCREMENTED_THREE_TIMES',
    ('reserve-release','EXTERNAL_CONTROL'):'WRONG_STATE_TRANSITION_RELEASE_COUNT_INCREMENTED_THREE_TIMES',
}


def summarize_resources(raw):
    if not raw:return None
    cpu=dict(line.split() for line in raw['cpu.stat'].splitlines())
    return {'cgroup_memory_peak_bytes':int(raw['memory.peak']),
        'cgroup_cpu_usage_seconds':int(cpu['usage_usec'])/1e6,'pids_peak':int(raw['pids.peak'])}


def build():
    rows=[]
    for filename,digest in INPUTS.items():
        raw=json.loads((ROOT/filename).read_text())
        if raw.get('receipt_sha256')!=digest or receipt_hash(raw)!=digest:raise ValueError('MEASUREMENT_INPUT_CHANGED')
        case=raw['cases'][0] if 'cases' in raw else raw
        attempts=case['attempts'];requests=case['model_trace']['requests']
        receipts=[a['verification']['owned_verifier_receipt'] for a in attempts if 'verification' in a]
        if any(receipt_hash(r)!=r['receipt_sha256'] for r in receipts):raise ValueError('VERIFIER_RECEIPT_CHANGED')
        baseline=set(case['task'].get('baseline_feedback',{}).get('failing_tests',[]))
        failed=set(t for r in receipts for t in r.get('test_feedback',{}).get('failing_tests',[]))
        rows.append({'file':filename,'origin_receipt_sha256':digest,'case_id':case['case_id'],'arm':case['arm'],
            'source_sha256':case['task']['source_sha256'],'tests_sha256':case['task']['tests_sha256'],
            'candidate_sha256':[r['candidate_sha256'] for r in receipts],
            'model_requests':case['model_trace']['dispatched'],'retry_count':max(0,len(requests)-1),
            'prompt_tokens':sum(r['usage']['prompt_tokens'] for r in requests),
            'completion_tokens':sum(r['usage']['completion_tokens'] for r in requests),
            'inference_seconds':round(sum(r['seconds'] for r in requests),3),'cycle_wall_seconds':case['elapsed_seconds'],
            'valid_candidates':len(receipts),'rejected_handoffs':sum('handoff_rejection' in a for a in attempts),
            'targeted_test_suites_passed':sum(r.get('targeted',{}).get('passed') is True for r in receipts),
            'independently_verified_repairs':case['verified_repairs'],
            'newly_reported_failing_tests':sorted(failed-baseline),
            'failure_category':CAUSES.get((case['case_id'],case['arm'])),
            'sdk_resources':summarize_resources(case.get('sdk_resources')),
            'model_resources':summarize_resources(case.get('model_resources')),
            'runtime_interruption':case.get('status')=='BLOCKED',
            'shutdown_confirmed':case.get('shutdown_confirmed') if case['arm']=='NATIVE_SDK' else None,
            'cleanup_confirmed':case['containers_absent_after_cleanup']})
    paired={}
    for arm in ('NATIVE_SDK','EXTERNAL_CONTROL'):
        selected=[r for r in rows if r['arm']==arm and r['case_id'] in ('optional-setting','reading-groups','reserve-release')]
        paired[arm]={k:sum(r[k] for r in selected) for k in ('model_requests','valid_candidates','targeted_test_suites_passed','independently_verified_repairs','prompt_tokens','completion_tokens')}
        paired[arm]['tasks_attempted']=len(selected)
        paired[arm]['inference_seconds']=round(sum(r['inference_seconds'] for r in selected),3)
        paired[arm]['cycle_wall_seconds']=round(sum(r['cycle_wall_seconds'] for r in selected),3)
    result={'kind':'PHASE20_REAL_INFERENCE_MEASUREMENTS','classification':'EXPOSED_OWNED_DEVELOPMENT',
        'independent_unseen_evaluation':False,'paired_comparison':paired,'cases':rows,
        'actual_model_requests':sum(r['model_requests'] for r in rows),
        'native_sdk_requests':sum(r['model_requests'] for r in rows if r['arm']=='NATIVE_SDK'),
        'external_control_requests':sum(r['model_requests'] for r in rows if r['arm']=='EXTERNAL_CONTROL'),
        'prompt_tokens':sum(r['prompt_tokens'] for r in rows),'completion_tokens':sum(r['completion_tokens'] for r in rows),
        'total_inference_seconds':round(sum(r['inference_seconds'] for r in rows),3),
        'total_measured_case_wall_seconds':round(sum(r['cycle_wall_seconds'] for r in rows),3),
        'additional_spending_usd':0,'confirmed_revenue_usd':0,'commercial_admission':'NOT_ADMITTED',
        'limitations':[
            'Paired SDK prompts contained 26 additional required working-directory tokens; prompt equivalence is incomplete.',
            'The attempted task-only hook in the frozen supplement was ineffective: required SDK context was restored. No task-only accuracy measurement exists.',
            'Memory is cgroup memory.peak, not process RSS. Shared file-backed model pages can be charged outside the observed cgroup.',
            'CPU covers observed containers through the final probe, including observation subprocesses; host verifier CPU is not measured.',
            'Case wall includes setup, reproduction, inference and verification. Isolated verification wall time was not separately instrumented.',
            'New failing test names are from bounded development feedback, not an exhaustive regression count.',
            'The initial failure lacks post-run memory/CPU metrics. Null denotes unavailable, not zero.',
            'Protocol replay/simulated responses, hosted candidate replays and previous Phase19 inference are excluded.',
            'Receipts bind recorded bytes by SHA256; signatures and cryptographic authorship identity are not attested.'
        ]}
    result['receipt_sha256']=receipt_hash(result)
    return result


if __name__=='__main__':print(json.dumps(build(),indent=2,sort_keys=True))
