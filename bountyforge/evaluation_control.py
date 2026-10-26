"""Model-free evaluation preparation. Public historical tasks are NOT unseen.

Only factual metadata and test IDs are retained; solutions/test patches/hints are
never persisted. The agent-facing projection has a separate strict allowlist.
"""
import hashlib
import json
import re
from bountyforge.repair_engines import encoded,strict_json
from phase21_reasoning import clean_text


def test_ids(value):
    rows=strict_json(value) if type(value) is str else value
    if (type(rows) is not list or not 1<=len(rows)<=10000
            or any(type(x) is not str or not 1<=len(x)<=1000 for x in rows)
            or len(set(rows))!=len(rows)):raise ValueError('COMPLETE_UNIQUE_TEST_IDENTITIES_REQUIRED')
    return sorted(rows)


def metadata_projection(row):
    if type(row) is not dict:raise ValueError('HISTORICAL_METADATA_REQUIRED')
    repo=row.get('repo');base=row.get('base_commit');problem=row.get('problem_statement')
    if (type(repo) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo)
            or type(base) is not str or not re.fullmatch('[a-f0-9]{40}',base)
            or type(row.get('instance_id')) is not str or not 1<=len(row['instance_id'])<=100
            or type(problem) is not str or not 1<=len(problem.encode())<=40000):raise ValueError('HISTORICAL_IDENTITY_REQUIRED')
    fail=test_ids(row.get('FAIL_TO_PASS'));regression=test_ids(row.get('PASS_TO_PASS'))
    if set(fail)&set(regression):raise ValueError('CONFLICTING_TEST_EXPECTATIONS')
    # No problem text, patch, test_patch, hints, or executable install commands.
    return {'instance_id':row['instance_id'],'repo':repo,'base_commit':base,
            'problem_sha256':hashlib.sha256(problem.encode()).hexdigest(),
            'expected_failing_tests':fail,'required_regressions':regression,
            'test_identity_sha256':hashlib.sha256(encoded({'fail':fail,'pass':regression})).hexdigest(),
            'contamination_warnings':['PUBLIC_HISTORICAL_TRAINING_OVERLAP_UNKNOWN']+
                (['ISSUE_MAY_DISCLOSE_SOLUTION'] if re.search(r'(?i)(here is (?:the|a) fix|diff --git|the following patch)',problem) else []),
            'reference_material_persisted':False,'execution_admitted':False,'independently_unseen':False}


def agent_packet(value,feedback):
    fields={'description','source','source_sha256','approved_file','editable_lines'}
    if type(value) is not dict or set(value)!=fields:raise ValueError('STRICT_AGENT_CONTEXT_FIELDS_REQUIRED')
    source=value['source'];lines=value['editable_lines']
    if (type(source) is not str or not 1<=len(source.encode())<=12000
            or hashlib.sha256(source.encode()).hexdigest()!=value['source_sha256']
            or value['approved_file']!='subject.py' or type(lines) is not list or not lines
            or any(type(n) is not int or not 1<=n<=len(source.splitlines()) for n in lines)
            or type(value['description']) is not str or len(value['description'])>2000):raise ValueError('AUTHORIZED_SOURCE_CONTEXT_REJECTED')
    static=encoded(value).decode()
    if feedback is not None:
        if type(feedback) is not dict or set(feedback)-{'stage','assertions'}:raise ValueError('FEEDBACK_FIELDS_REJECTED')
        if type(feedback.get('assertions',[])) is not list:raise ValueError('FEEDBACK_FORMAT_REJECTED')
    dynamic={'authority':'UNTRUSTED_OBSERVATION_DATA_ONLY','stage':clean_text((feedback or {}).get('stage','BASELINE'),80),
             'assertions':[clean_text(t,180) for t in (feedback or {}).get('assertions',[])[:4]]}
    return {'stable_prefix':static,'stable_prefix_sha256':hashlib.sha256(static.encode()).hexdigest(),
            'dynamic_feedback':dynamic,'cache_hit_guaranteed':False,'measured_token_savings':None,
            'reference_solutions_included':False,'paid_inference_authorized':False}


def retry_policy(stage,attempt):
    if type(attempt) is not int or not 1<=attempt<=2:raise ValueError('ATTEMPT_NUMBER_REJECTED')
    if attempt==2:return 'STOP_ATTEMPT_LIMIT'
    if stage in ('API_TIMEOUT','UNKNOWN_USAGE','INTERRUPTED'):return 'STOP_UNCERTAIN_SPEND'
    if stage in ('SOURCE_REJECTED','TEST_FAILED'):return 'REVISE_WITH_SANITIZED_FEEDBACK'
    if stage=='VERIFIED':return 'STOP_VERIFIED'
    return 'STOP_UNSUPPORTED_FAILURE'


def admit_historical_execution(_):
    # Caller booleans cannot replace hostile-code, dependency and source-rights
    # admission. This module intentionally has no inference/execute function.
    raise ValueError('HISTORICAL_THIRD_PARTY_EXECUTION_NOT_ADMITTED')
