"""Independent bounded replay of fixed historical model-success evidence.

No inference, downloaded source, arbitrary paths, or publication credentials.
"""
import difflib
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from bountyforge.curated_tasks import TASKS, MANIFEST, RECEIPT, replay
from bountyforge.curated_docker import MARKER, run_curated, verify_runtime_boundary
from bountyforge.repair_context import physical_lines


def verify(report):
    expected = {t['id']: t for t in MANIFEST['tasks']}
    if (report.get('benchmark') != 'boltons_26.1.0_curated_excerpts'
            or report.get('experiment') != 'ast_contract_v5'
            or report.get('blocked') != 0 or report.get('completed') != 5
            or report.get('paid_inference') is not False
            or report.get('external_submission') is not False):
        raise ValueError('Incomplete or unauthorized historical evidence')
    tasks = report.get('tasks', [])
    if len(tasks) != 5 or {t['id'] for t in tasks} != set(expected):
        raise ValueError('Unexpected historical case set')
    calls = [c for t in tasks for a in t['attempts'] for c in a['calls']]
    if len(calls) != report['model_calls'] or not 1 <= len(calls) <= 12:
        raise ValueError('Call accounting mismatch')
    for call in calls:
        if (not isinstance(call['response'], str) or len(call['response'].encode()) > 3000
                or len(call['prompt'].encode()) > 3600
                or not 1 <= call['max_tokens'] <= 150 or call['seconds'] < 0):
            raise ValueError('Invalid call transcript')
    verified = []
    for item in tasks:
        task = expected[item['id']]
        trusted = TASKS / task['id']
        source = (trusted / task['file']).read_text()
        for filename, field in [(task['file'], 'source_sha256'),
                                ('tests/test_regression.py', 'tests_sha256')]:
            if hashlib.sha256((trusted/filename).read_bytes()).hexdigest() != item[field]:
                raise ValueError('Historical fixture provenance mismatch')
        if not item['baseline_reproduced']:
            raise ValueError('Baseline not reproduced')
        successful = [a for a in item['attempts'] if a['status'] == 'passed']
        if bool(successful) != item['model_generated_success']:
            raise ValueError('Success accounting mismatch')
        if not successful:
            continue
        if len(successful) != 1 or not successful[0]['test']['passed']:
            raise ValueError('Invalid successful attempt')
        generated = successful[0]['calls']
        if ([c['symbol'] for c in generated] != task['symbols']
                or any(c['stage'] != 'source_validated' for c in generated)):
            raise ValueError('Incomplete successful symbol repair')
        proposals = [{'symbol': c['symbol'], 'response': c['response']} for c in generated]
        revised = replay(task['id'], proposals)
        patch = ''.join(difflib.unified_diff(physical_lines(source, True),
                                           physical_lines(revised, True),
                                           fromfile='a/'+task['file'], tofile='b/'+task['file']))
        if patch != item.get('patch'):
            raise ValueError('Patch does not match actual model responses')
        with tempfile.TemporaryDirectory(prefix='bf-independent-replay-') as directory:
            root = Path(directory)/'case'
            shutil.copytree(trusted, root)
            (root/MARKER).write_text(task['id'])
            # Prove controls before independently executing even the exact tree.
            preflight = verify_runtime_boundary(root)
            (root/task['file']).write_text(revised)
            (root/RECEIPT).write_text(json.dumps(proposals))
            check = run_curated(root)
        if not check['passed']:
            raise ValueError('Independent model repair replay failed: '+task['id'])
        verified.append({'id':task['id'], 'test':check,
                         'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),
                         'sandbox_preflight':preflight})
    if len(verified) != report['passed']:
        raise ValueError('Verified score mismatch')
    return {'verification':'independent_docker_replay', 'inference_calls':0,
            'commercial_bounty':False, 'full_upstream_suite':False,
            'revision':report['revision'], 'passed':len(verified),
            'cases':verified}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.report.read_bytes()
    if len(raw) > 200000:
        raise ValueError('Evidence size bound exceeded')
    result = verify(json.loads(raw))
    result['report_sha256'] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print('Independent replay passed:', result['passed'])
