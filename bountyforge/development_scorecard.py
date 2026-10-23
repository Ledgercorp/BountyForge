"""Receipt-bound developmental measurements; never upgrades evaluation blindness."""
from bountyforge.owned_repair_queue import valid_success
from bountyforge.repair_engines import catalog, receipt_hash, digest, encoded, strict_json

CASES=('invoice-summary','cursor-adapter','retry-policy')


def measure(case_id,engine,attempts,*,calls=None,elapsed=None):
    if case_id not in CASES or not 0<=len(attempts)<=2:raise ValueError('Unexpected measurement task/attempt budget')
    spec=next(x for x in catalog() if x['id']==case_id)
    for attempt in attempts:
        if (attempt.get('receipt_sha256')!=receipt_hash(attempt) or attempt.get('engine')!=engine
                or attempt.get('case_id')!=case_id or attempt.get('source_sha256')!=spec['sha256']['subject.py']
                or attempt.get('tests_sha256')!=spec['sha256']['tests/test_regression.py']):
            raise ValueError('Measurement receipt binding rejected')
        if attempt.get('independently_verified') is True and not valid_success(attempt,case_id,engine):
            raise ValueError('Contradictory successful receipt')
    verified=any(valid_success(row,case_id,engine) for row in attempts)
    valid=[a for a in attempts if 'candidate_sha256' in a]
    result={'case_id':case_id,'engine':engine,'proposal_attempts':len(attempts),
            'valid_patches':len(valid),'verified_repair':verified,
            'targeted_suites_passed':sum(a.get('targeted',{}).get('passed') is True for a in attempts),
            'targeted_test_methods_in_passing_suites':sum(a['targeted']['tests_run'] for a in attempts if a.get('targeted',{}).get('passed') is True),
            'fresh_replay_test_methods_passed':sum(a['independent']['tests_run'] for a in attempts if a.get('independent',{}).get('passed') is True),
            'failure_categories':[a['outcome'] for a in attempts if a['outcome']!='VERIFIED'],
            'model_calls':None,'prompt_tokens':None,'completion_tokens':None,
            'elapsed_seconds':elapsed,'classification':'OWNED_DEVELOPMENT','independent_evaluation':False}
    if calls is not None:
        if type(calls) is not list or len(calls)>2:raise ValueError('Call budget rejected')
        for call in calls:
            response=call.get('response')
            if type(response) is str and digest(response.encode())!=call.get('response_sha256'):
                raise ValueError('Raw generation hash rejected')
        result['model_calls']=len(calls)
        for token in ('prompt_tokens','completion_tokens'):
            values=[c.get('metadata',{}).get(token) for c in calls]
            if values and all(type(x) is int and x>=0 for x in values):result[token]=sum(values)
    return result


def compare(codex_trace,qwen_report):
    codex={case:[] for case in CASES}
    for call in codex_trace['calls']:
        if call['tool']!='submit_owned_repair':continue
        result=call['response'].get('result',{})
        if result.get('isError') is not False:continue
        value=strict_json(result['content'][0]['text'])
        if value.get('case_id') in codex:codex[value['case_id']].append(value)
    codex_rows=[measure(case,'CODEX_AGENT',codex[case]) for case in CASES]
    qwen_rows=[]
    for job in qwen_report['jobs']:
        task=job['preparation']['task'];result=job['result']['receipt']
        calls=result.get('calls',[]) if type(result.get('model_calls')) is int else None
        if calls is not None and result['model_calls']!=len(calls):raise ValueError('Reported call count differs from raw calls')
        row=measure(task['case_id'],'QWEN_LOCAL',result.get('attempts',[]),calls=calls,elapsed=result.get('elapsed_seconds'))
        row['terminal_outcome']=result['outcome'];row['queue_state']=job['result']['state']
        if not row['failure_categories'] and result['outcome']!='VERIFIED':row['failure_categories']=[result['outcome']]
        qwen_rows.append(row)
    if len({row['case_id'] for row in qwen_rows})!=len(qwen_rows):raise ValueError('Duplicate measured task')
    return {'kind':'phase14_dual_engine_development_scorecard','classification':'OWNED_DEVELOPMENT',
            'independent_evaluation':False,'codex':codex_rows,'qwen':qwen_rows,
            'qwen_experiment_elapsed_seconds':qwen_report['elapsed_seconds'],
            'codex_session_elapsed_seconds':codex_trace['elapsed_seconds'],
            'additional_spending_usd':0,'independent_accuracy':None,
            'comparison_limits':['Agent authored public tasks and can inspect tests',
             'Different hosts and generation contexts; not a blinded randomized comparison',
             'Active-session model usage unavailable; transport starts no additional model turn',
             'Passing replay verifies a candidate, not unseen generalization or commercial admission']}
