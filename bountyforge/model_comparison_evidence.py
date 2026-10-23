"""Post-hoc receipt checks and fresh owned replay. Never performs inference."""
from collections import Counter
import json
from pathlib import Path
import tempfile

from bountyforge.curated_tasks import editable_scope
from bountyforge.model_profiles import PROFILES,profile_spec
from bountyforge.owned_repair_queue import valid_success
from bountyforge.phase8_evaluation import validate_proof
from bountyforge.repair_engines import (ROOT,OwnedVerifier,catalog,digest,encoded,materialize,
    observation_summary,receipt_hash,strict_json)
from bountyforge.repair_intelligence import revision_proposal,validate_local_dependencies
from bountyforge.repair_session import validate_proposal_bindings
from bountyforge.statements import stage_statements,statement_catalog


def usage(calls,*,unknown=False):
    if unknown:return {'completion_requests':None,'prompt_tokens':None,'completion_tokens':None}
    dispatched=[]
    for call in calls:
        metadata=call.get('metadata')
        if (type(metadata) is not dict or type(metadata.get('completion_requests')) is not int
                or metadata['completion_requests'] not in (0,1)):
            return usage([],unknown=True)
        if metadata['completion_requests']==1:dispatched.append(metadata)
    result={'completion_requests':len(dispatched)}
    for key in ('prompt_tokens','completion_tokens'):
        values=[m.get(key) for m in dispatched]
        result[key]=sum(values) if all(type(n) is int and n>=0 for n in values) else None
    return result


def failure_kind(attempt):
    if attempt['outcome']!='SOURCE_REJECTED':return attempt['outcome']
    diagnostic=attempt.get('diagnostic','')
    for phrase,kind in [('Semantically ineffective','NO_OP'),('reads local before','INVALID_LOCAL_BINDING'),
                        ('Condition requires','INVALID_PYTHON_FRAGMENT'),('Invalid structured JSON','INVALID_JSON'),
                        ('proposal schema','INVALID_PATCH_STRUCTURE'),('Unapproved','INVALID_SCOPE'),
                        ('New callable','SOURCE_CAPABILITY_REJECTION')]:
        if phrase in diagnostic:return kind
    return 'SOURCE_VALIDATION_REJECTION'


def load_record(raw,expected_sha):
    if type(raw) is not bytes or len(raw)>500000 or digest(raw)!=expected_sha:raise ValueError('COMPARISON_DIGEST_REJECTED')
    record=strict_json(raw)
    configs=[p.read_bytes() for p in (ROOT/'experiments/phase15/comparison.json',ROOT/'experiments/phase15/comparison-v2.json',
                                    ROOT/'experiments/phase15/comparison-v3.json',ROOT/'experiments/phase15/comparison-v4.json',
                                    ROOT/'experiments/phase15/comparison-v5-unmeasured.json') if p.is_file()]
    config_raw=next((r for r in configs if digest(r)==record.get('experiment_sha256')),None)
    if config_raw is None:raise ValueError('FROZEN_EXPERIMENT_NOT_FOUND')
    config=strict_json(config_raw)
    if (record.get('kind')!='phase15_local_model_comparison' or record.get('receipt_sha256')!=receipt_hash(record)
            or record.get('experiment_sha256')!=digest(config_raw) or record.get('frozen_experiment')!=config
            or record.get('independent_evaluation') is not False or record.get('default_replaced') is not False
            or record.get('paid_fallback') is not False or type(record.get('models')) is not list
            or [m['model_profile'] for m in record['models']]!=list(PROFILES)[:len(record['models'])]
            or len(record['models'])>2):raise ValueError('COMPARISON_BINDING_REJECTED')
    if record.get('status')=='COMPLETED' and (len(record['models'])!=2 or any(
            m['status']!='COMPLETED' or len(m['jobs'])!=len(config['case_ids']) or any(j.get('result',{}).get('state') not in ('FAILED','VERIFIED')
            for j in m['jobs']) for m in record['models'])):raise ValueError('INCOMPLETE_COMPARISON_MISLABELED')
    return record


def candidate(spec,task,attempt):
    source=task['source'];scope=sorted(statement_catalog(source,editable_scope(source,spec['symbol'])))
    proposal=attempt['proposal'];raw=proposal.encode() if type(proposal) is str else encoded(proposal)
    if (task['source_sha256']!=spec['sha256']['subject.py'] or digest(source.encode())!=task['source_sha256']
            or task['tests_sha256']!=spec['sha256']['tests/test_regression.py'] or task['editable_lines']!=scope
            or attempt['proposal_sha256']!=digest(raw)):
        raise ValueError('SOURCE_SCOPE_BINDING_REJECTED')
    with tempfile.TemporaryDirectory(prefix='bf15-candidate-check-') as d:
        root=Path(d)/'task';materialize(spec,root)
        staged=stage_statements(raw.decode(),root,'subject.py',scope,task['source_sha256'])['files'][0]
        validate_proposal_bindings(source,scope,raw.decode());validate_local_dependencies(source,raw.decode())
    if digest(staged['content'].encode())!=attempt['candidate_sha256'] or staged['diff']!=attempt['diff']:
        raise ValueError('RECORDED_CANDIDATE_REJECTED')
    return staged['content']


def summarize(record):
    specs={s['id']:s for s in catalog()};allowed=record['frozen_experiment']['case_ids'];rows=[]
    for engine in record['models']:
        profile=engine['model_profile'];model=profile_spec(profile)
        jobs=engine['jobs'];case_ids=[j['case_id'] for j in jobs]
        if case_ids!=allowed[:len(jobs)] or len(jobs)>len(allowed):raise ValueError('COMPARISON_CASE_ORDER_REJECTED')
        row={'model_profile':profile,'model_sha256':model['sha256'],'status':engine['status'],
             'blocking_reason':engine.get('blocking_reason'),'resource_admitted':engine.get('resource_admitted',False),
             'configured_tasks':len(allowed),'tasks_prepared':0,'tasks_with_model_response':0,'valid_patches':0,
             'tasks_with_completion_request':0,'tasks_completed':0,'tasks_blocked':0,
             'targeted_suites_passed':0,'verified_repairs':0,'fresh_replay_methods_passed':0,
             'source_rejected':0,'repeated_proposals':0,'client_attempts':0,'failure_categories':{},'cases':[]}
        all_calls=[];unknown=False;categories=Counter();runtimes=[]
        probe=engine.get('resource_probe',{})
        if 'runtime' in probe:runtimes.append(probe['runtime'])
        for job in jobs:
            if 'runtime' in job:runtimes.append(job['runtime'])
            task=job.get('preparation',{}).get('task');result=job.get('result',{});wrapper=result.get('receipt',{})
            calls=wrapper.get('calls',[]);attempts=wrapper.get('attempts',[])
            if len(calls)>2 or len(attempts)>len(calls):raise ValueError('MODEL_ATTEMPT_BOUND_REJECTED')
            if result and (type(wrapper.get('model_calls')) is not int or wrapper['model_calls']!=len(calls)):unknown=True
            if not result and job.get('runtime',{}).get('load_seconds') is not None:unknown=True
            if task:
                if task.get('model_profile')!=profile or task.get('model_sha256')!=model['sha256']:raise ValueError('TASK_MODEL_IDENTITY_REJECTED')
                row['tasks_prepared']+=1
            metrics={'case_id':job['case_id'],'queue_state':result.get('state'),'terminal_outcome':wrapper.get('outcome'),
                     'inference_failure':wrapper.get('inference_failure'),
                     'client_attempts':len(calls),'valid_patches':0,'verified_repair':False,'attempts':[],
                     'elapsed_seconds':job.get('elapsed_seconds')}
            for index,attempt in enumerate(attempts):
                if (attempt.get('receipt_sha256')!=receipt_hash(attempt) or attempt.get('engine')!='QWEN_LOCAL'
                        or attempt.get('model_profile')!=profile or attempt.get('model_sha256')!=model['sha256']
                        or attempt.get('task_id')!=task.get('task_id') or attempt.get('case_id')!=job['case_id']
                        or attempt.get('source_sha256')!=specs[job['case_id']]['sha256']['subject.py']
                        or attempt.get('tests_sha256')!=specs[job['case_id']]['sha256']['tests/test_regression.py']):
                    raise ValueError('ATTEMPT_RECEIPT_REJECTED')
                call=calls[index];response=call.get('response')
                if type(response) is not str or digest(response.encode())!=call.get('response_sha256'):raise ValueError('MODEL_RESPONSE_BINDING_REJECTED')
                effective,retained=revision_proposal(attempts[index-1] if index else None,response)
                if (effective!=attempt['proposal'] or effective!=call.get('effective_proposal')
                        or retained!=call.get('retained_anchors')
                        or attempt.get('generation',{}).get('raw_response_sha256')!=call['response_sha256']
                        or attempt.get('generation',{}).get('prompt_sha256')!=call.get('prompt_sha256')):
                    raise ValueError('AUTONOMOUS_GENERATION_BINDING_REJECTED')
                if 'candidate_sha256' in attempt:
                    content=candidate(specs[job['case_id']],task,attempt);metrics['valid_patches']+=1
                    if attempt.get('candidate') is not None and attempt['candidate']!=content:raise ValueError('SUCCESS_BYTES_REJECTED')
                if attempt.get('independently_verified') is True:
                    if not valid_success(attempt,job['case_id'],'QWEN_LOCAL',task['task_id'],profile):raise ValueError('FALSE_SUCCESS_REJECTED')
                    if not job.get('runtime',{}).get('server_stopped'):raise ValueError('CLEANUP_UNVERIFIED')
                    metrics['verified_repair']=True;row['fresh_replay_methods_passed']+=attempt['independent']['tests_run']
                categories[attempt['outcome']]+=1
                row['targeted_suites_passed']+=attempt.get('targeted',{}).get('passed') is True
                metrics['attempts'].append({'outcome':attempt['outcome'],'failure_kind':failure_kind(attempt),'diagnostic':attempt['diagnostic'],
                    'receipt_sha256':attempt['receipt_sha256'],'new_failing_test_ids':sorted(
                        set(attempt.get('test_feedback',{}).get('failing_tests',[]))-set(task['baseline_feedback']['failing_tests']))})
            if (result.get('state')=='VERIFIED')!=metrics['verified_repair']:raise ValueError('QUEUE_SUCCESS_CONTRADICTION')
            if wrapper.get('outcome') and wrapper['outcome'] not in {a['outcome'] for a in attempts}:
                categories[wrapper['outcome']]+=1
            if any(type(c.get('response')) is str for c in calls):row['tasks_with_model_response']+=1
            if any(type(c.get('metadata')) is dict and c['metadata'].get('completion_requests')==1 for c in calls):row['tasks_with_completion_request']+=1
            row['tasks_completed']+=result.get('state') in ('FAILED','VERIFIED')
            row['tasks_blocked']+=result.get('state')=='BLOCKED' or bool(job.get('runtime_error'))
            row['client_attempts']+=len(calls);row['valid_patches']+=metrics['valid_patches'];row['verified_repairs']+=metrics['verified_repair']
            row['cases'].append(metrics);all_calls+=calls
        row['source_rejected']=categories['SOURCE_REJECTED'];row['repeated_proposals']=categories['REPEATED_PROPOSAL']
        row['tasks_not_prepared']=len(allowed)-row['tasks_prepared']
        row['failure_categories']={k:v for k,v in categories.items() if k!='VERIFIED'}
        row['repair_usage']=usage(all_calls,unknown=unknown)
        row['admission_usage']=usage([probe] if probe.get('metadata') is not None else [])
        row['resource_probe_tokenized_prompt_tokens']=(probe.get('metadata') or {}).get('tokenized_prompt_tokens')
        row['repair_tokenized_prompt_tokens']=[(c.get('metadata') or {}).get('tokenized_prompt_tokens') for c in all_calls]
        row['inference_seconds']=round(sum(c.get('seconds',0) for c in all_calls),3)
        row['resource_probe_inference_seconds']=probe.get('inference_seconds');row['total_execution_seconds']=engine.get('elapsed_seconds')
        row['peak_rss_kib_observed']=max((r['peak_rss_kib'] for r in runtimes if r.get('peak_rss_kib') is not None),default=None)
        row['server_load_seconds']=[r.get('load_seconds') for r in runtimes]
        row['all_recorded_servers_stopped']=all(r.get('server_stopped') is True for r in runtimes)
        row['unexpected_server_exits']=[{k:r.get(k) for k in ('server_exit_code','observed_cpu_seconds','cpu_limit_seconds',
                                                            'wall_limit_reached','peak_rss_kib')} for r in runtimes if r.get('unexpected_exit')]
        times=[r.get('observed_cpu_seconds') for r in runtimes]
        row['observed_process_cpu_seconds']=round(sum(times),3) if times and all(type(n) in (int,float) for n in times) else None
        row['cpu_measurement_note']='Process CPU counters at last pre-shutdown sample; not host-wide utilization. V1 did not collect CPU time.'
        rows.append(row)
    requests=[r[k]['completion_requests'] for r in rows for k in ('repair_usage','admission_usage')]
    total=sum(requests) if all(type(n) is int for n in requests) else None
    maximum=record['frozen_experiment']['budgets']['maximum_completion_requests']
    if total is not None and total>maximum:raise ValueError('TOTAL_COMPLETION_BUDGET_EXCEEDED')
    hashes={}
    for engine in record['models']:
        for job in engine['jobs']:
            calls=job.get('result',{}).get('receipt',{}).get('calls',[])
            if calls:hashes.setdefault(job['case_id'],[]).append(calls[0]['prompt_sha256'])
    return {'kind':'phase15_verified_development_model_summary','classification':'OWNED_DEVELOPMENT',
        'independent_evaluation':False,'independent_accuracy':None,'run_id':record['run_id'],'commit':record['commit'],
        'record_receipt_sha256':record['receipt_sha256'],'experiment_sha256':record['experiment_sha256'],
        'models':rows,'completion_requests_total':total,'maximum_completion_requests':maximum,
        'initial_prompt_comparison':{case:{'models_observed':len(values),'identical_hashes':len(set(values))==1} for case,values in hashes.items()},
        'additional_spending_usd':0,'inference_spending_usd':0,'default_model_profile':'QWEN_1_5B','default_replaced':False}


def replay_successes(record,*,include_failed=False):
    specs={s['id']:s for s in catalog()};selected=[]
    for engine in record['models']:
        for job in engine['jobs']:
            task=job.get('preparation',{}).get('task');wrapper=job.get('result',{}).get('receipt',{})
            receipt=wrapper.get('verification_receipt',{})
            if receipt.get('independently_verified') is True:
                if not valid_success(receipt,job['case_id'],'QWEN_LOCAL',task['task_id'],engine['model_profile']):raise ValueError('REPLAY_SUCCESS_BINDING_REJECTED')
                selected.append((specs[job['case_id']],task,receipt,True))
            elif include_failed:
                for receipt in wrapper.get('attempts',[]):
                    if receipt.get('outcome')=='TEST_FAILED' and 'candidate_sha256' in receipt:
                        if (receipt.get('receipt_sha256')!=receipt_hash(receipt) or receipt.get('model_profile')!=engine['model_profile']
                                or receipt.get('engine')!='QWEN_LOCAL'):raise ValueError('FAILED_REPLAY_BINDING_REJECTED')
                        selected.append((specs[job['case_id']],task,receipt,False))
    report={'kind':'phase15_separate_credential_free_replay','model_generation_calls':0,
        'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,
        'record_receipt_sha256':record['receipt_sha256'],'cases':[],'replay_passed':None,
        'failure_reproduction_matched':None,'verified_successes_replayed':0}
    if selected:
        verifier=OwnedVerifier();proof=verifier.preflight();validate_proof(proof);report['runtime_admission']=proof
        for spec,task,receipt,expected_pass in selected:
            source=candidate(spec,task,receipt);observation=verifier.observe(spec,source)
            report['cases'].append({'case_id':spec['id'],'model_profile':receipt['model_profile'],
                'candidate_sha256':receipt['candidate_sha256'],'original_receipt_sha256':receipt['receipt_sha256'],
                'original_claimed_success':expected_pass,'verification':observation_summary(observation)})
        successes=[c for c in report['cases'] if c['original_claimed_success']]
        failures=[c for c in report['cases'] if not c['original_claimed_success']]
        report['verified_successes_replayed']=sum(c['verification']['passed'] for c in successes)
        report['replay_passed']=all(c['verification']['passed'] for c in successes) if successes else None
        report['failure_reproduction_matched']=all(not c['verification']['passed'] for c in failures) if failures else None
    report['receipt_sha256']=receipt_hash(report);return report
