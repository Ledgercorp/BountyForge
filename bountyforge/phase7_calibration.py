"""New owned calibration cases, never an independent model performance score.

Cases are public development fixtures, not unseen held-out defects. Only the
exact, authored source and reference fix are executed for harness validation.
"""
import hashlib
import json


class CalibrationBlocked(ValueError):
    pass


CASES = (
    {
        'id': 'page-offset-boundary', 'symbol': 'page',
        'defect': 'pagination off-by-one discards the first item of each page',
        'source': 'def page(items, number, size):\n    start = number * size + 1\n    return items[start:start+size]\n',
        'fixed': 'def page(items, number, size):\n    start = number * size\n    return items[start:start+size]\n',
        'vectors': ((([1,2,3,4],0,2),[1,2]), (([1,2,3,4],1,2),[3,4]), (([1,2,3],2,2),[])),
    },
    {
        'id': 'tenant-key-collision', 'symbol': 'find',
        'defect': 'ID lookup omits tenant scope and returns another account',
        'source': 'def find(records, tenant, key):\n    for row in records:\n        if row["id"] == key:\n            return row["name"]\n    return None\n',
        'fixed': 'def find(records, tenant, key):\n    for row in records:\n        if row["id"] == key and row["tenant"] == tenant:\n            return row["name"]\n    return None\n',
        'vectors': ((([{'id':'x','tenant':'A','name':'Alice'},{'id':'x','tenant':'B','name':'Bob'}],'B','x'),'Bob'), (([{'id':'x','tenant':'A','name':'Alice'}],'B','x'),None), (([],'A','x'),None)),
    },
    {
        'id': 'retry-millisecond-units', 'symbol': 'backoff',
        'defect': 'retry delay milliseconds are not converted to seconds',
        'source': 'def backoff(attempt, base_ms, ceiling_seconds):\n    delay = base_ms * (2 ** attempt)\n    if delay > ceiling_seconds:\n        return ceiling_seconds\n    return delay\n',
        'fixed': 'def backoff(attempt, base_ms, ceiling_seconds):\n    delay = base_ms * (2 ** attempt) / 1000\n    if delay > ceiling_seconds:\n        return ceiling_seconds\n    return delay\n',
        'vectors': (((0,100,10),0.1), ((3,200,10),1.6), ((7,1000,10),10)),
    },
    {
        'id': 'even-median-aggregation', 'symbol': 'median',
        'defect': 'even length median uses upper element rather than midpoint',
        'source': 'def median(values):\n    numbers = sorted(values)\n    middle = len(numbers) // 2\n    if not numbers:\n        return None\n    return numbers[middle]\n',
        'fixed': 'def median(values):\n    numbers = sorted(values)\n    middle = len(numbers) // 2\n    if not numbers:\n        return None\n    if len(numbers) % 2 == 0:\n        return (numbers[middle-1] + numbers[middle]) / 2\n    return numbers[middle]\n',
        'vectors': ((([10,2,7,5],),6.0), (([1,9],),5.0), (([3,1,2],),2), (([],),None)),
    },
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),allow_nan=False).encode('utf-8')


def manifest():
    entries = [{'id':case['id'],'symbol':case['symbol'],
                'source_sha256':hashlib.sha256(case['source'].encode()).hexdigest(),
                'reference_sha256':hashlib.sha256(case['fixed'].encode()).hexdigest(),
                'vectors':len(case['vectors'])} for case in CASES]
    return {'schema':1,'kind':'owned_public_calibration_catalog',
            'cases':entries,'manifest_sha256':hashlib.sha256(canonical(entries)).hexdigest(),
            'hidden_or_unseen_test_set':False,'model_calls':0,
            'independent_model_repairs_verified':0,
            'commercial_repair_accuracy_established':False}


def replay_one(case_id, source_bytes, reference_bytes):
    match=[case for case in CASES if case['id']==case_id]
    if len(match)!=1:
        raise CalibrationBlocked('Not an owned calibration case')
    case=match[0]
    if (type(source_bytes) is not bytes or type(reference_bytes) is not bytes
            or source_bytes!=case['source'].encode() or reference_bytes!=case['fixed'].encode()):
        raise CalibrationBlocked('Owned calibration bytes changed')
    # Only exact authored code can be executed, with a tiny builtin allowlist.
    scope={'__builtins__':{'len':len,'sorted':sorted}}
    baseline=dict(scope); candidate=dict(scope)
    exec(compile(source_bytes,'<owned-calibration-baseline>','exec'),baseline)
    exec(compile(reference_bytes,'<owned-calibration-reference>','exec'),candidate)
    name=case['symbol']
    fail=sum(baseline[name](*args)!=expected for args,expected in case['vectors'])
    passed=sum(candidate[name](*args)==expected for args,expected in case['vectors'])
    if fail<1 or passed!=len(case['vectors']):
        raise CalibrationBlocked('Owned reference or baseline failed validation')
    return {'case_id':case_id,'baseline_failed_vectors':fail,
            'reference_passed_vectors':passed,'total_vectors':len(case['vectors']),
            'model_calls':0,'actual_ai_repair_success_measured':False,
            'customer_code_executed':False}


def replay_catalog():
    records=[replay_one(c['id'],c['source'].encode(),c['fixed'].encode()) for c in CASES]
    return {'schema':1,'kind':'owned_calibration_harness_check',
            'catalog_sha256':manifest()['manifest_sha256'],'case_count':len(records),
            'baseline_defects_reproduced':len(records),
            'owned_reference_fixes_verified':len(records),
            'independent_ai_repairs_tested':0,'live_inference_calls':0,
            'commercial_repair_accuracy_established':False,'records':records}
