"""Independent bounded replay of fixed historical model-success evidence.

No inference, downloaded source, arbitrary paths, or publication credentials.
"""
import difflib
import hashlib
import json
import shutil
import tempfile
import math
import re
from pathlib import Path
from bountyforge.curated_tasks import TASKS, MANIFEST, RECEIPT, replay, editable_scope
from bountyforge.curated_docker import MARKER, run_curated, verify_runtime_boundary
from bountyforge.repair_context import physical_lines
from bountyforge.lineedit import stage_lines
from bountyforge.curated_docker import IMAGE
from bountyforge.groq_adapter import MODEL_ID


def validate_hosted_accounting(report, expected_revision):
    """No source execution: reject incomplete or mislabeled hosted experiments."""
    if (report.get('inference_provider') != 'groq'
            or not isinstance(expected_revision, str) or not re.fullmatch(r'[0-9a-f]{40}', expected_revision)
            or report.get('revision') != expected_revision
            or report.get('experiment') != 'ast_contract_v7'
            or report.get('run_type') != 'real_groq_hosted' or report.get('image') != IMAGE
            or report.get('model_sha256') is not None or report.get('runtime_sha256') is not None
            or report.get('billing_independently_verified') is not False
            or report.get('attempted') != 5 or report.get('max_total_model_calls') != 8):
        raise ValueError('Invalid hosted identity, revision or resource budget')
    backend = report.get('inference_backend', {})
    if (backend.get('provider') != 'groq' or backend.get('model') != MODEL_ID
            or type(backend.get('transport_calls')) is not int
            or backend['transport_calls'] != report.get('model_calls')
            or backend.get('total_generation_tokens_per_call') != 1024
            or backend.get('minimum_interval_seconds') != 60):
        raise ValueError('Hosted transport accounting mismatch')
    proof = report.get('sandbox_preflight', {})
    controls = ('network_denied', 'loopback_inference_unreachable', 'source_writes_denied',
                'root_writes_denied', 'secrets_absent', 'uid_unprivileged', 'capabilities_empty',
                'no_new_privileges', 'seccomp_active', 'memory_limit_enforced', 'swap_disabled',
                'cpu_quota_verified', 'pid_limit_verified', 'tmpfs_bounded_noexec',
                'wall_clock_enforced', 'cleanup_verified', 'output_bounded',
                'docker_socket_absent', 'pid_pressure_enforced', 'cpu_pressure_enforced')
    if (not all(proof.get(k) is True for k in controls)
            or proof.get('image_digest') != IMAGE.split('@')[1]
            or proof.get('untrusted_execution_certified') is not False):
        raise ValueError('Hosted Docker controls incomplete')
    calls = []
    for item in report['tasks']:
        baseline = item.get('baseline', {})
        attempts = item.get('attempts', [])
        success = item.get('model_generated_success')
        if (baseline.get('passed') is not False or baseline.get('returncode') != 1
                or baseline.get('timeout') is not False or baseline.get('error') is not None
                or 'FAILED (failures=' not in baseline.get('output', '')
                or not 1 <= len(attempts) <= 2
                or [a.get('number') for a in attempts] != list(range(1, len(attempts)+1))
                or type(success) is not bool
                or item.get('status') != ('historical_excerpt_review_ready' if success else 'failed')
                or any(a.get('status') != 'failed' for a in attempts[:-1])
                or (attempts[-1].get('status') == 'passed') != success
                or any(a.get('failure_reason') not in (None, 'proposal_rejected', 'targeted_tests_failed')
                       for a in attempts)):
            raise ValueError('Hosted baseline or attempt terminal state invalid')
        task_calls = [c for a in attempts for c in a.get('calls', [])]
        if not task_calls or item.get('model_calls') != len(task_calls):
            raise ValueError('Hosted per-case call mismatch')
        calls.extend(task_calls)
        for attempt in attempts:
            check = attempt.get('test')
            if check is not None and (check.get('timeout') is not False or check.get('error') is not None
                    or check.get('returncode') != (0 if check.get('passed') else 1)):
                raise ValueError('Sandbox failure is not a completed model test')
            if attempt.get('status') == 'passed' and (not check or check.get('passed') is not True
                    or not re.search(r'Ran [1-9][0-9]* tests?', check.get('output', ''))
                    or not check['output'].rstrip().endswith('OK')):
                raise ValueError('Hosted success lacks isolated regression evidence')
    if ([c.get('number') for c in calls] != list(range(1, len(calls)+1)) or not 1 <= len(calls) <= 8):
        raise ValueError('Hosted call sequence out of bounds')
    for call in calls:
        metadata = call.get('model_metadata', {})
        response = call.get('response')
        if (call.get('kind') != 'patch' or call.get('inference_error')
                or metadata.get('provider') != 'groq' or metadata.get('model') != MODEL_ID
                or metadata.get('provider_model_reported') != MODEL_ID
                or metadata.get('finish_reason') != 'stop'
                or metadata.get('requested_max_completion_tokens') != 1024
                or type(metadata.get('prompt_tokens')) is not int or metadata['prompt_tokens'] <= 0
                or type(metadata.get('completion_tokens')) is not int
                or not 1 <= metadata['completion_tokens'] <= 1024
                or metadata.get('total_tokens') != metadata['prompt_tokens']+metadata['completion_tokens']
                or not isinstance(response, str)
                or call.get('response_sha256') != hashlib.sha256(response.encode()).hexdigest()):
            raise ValueError('Hosted usage, response or model identity invalid')
    measured = report.get('adapter_wall_seconds_including_pacing')
    if (type(measured) not in (int, float) or not math.isfinite(measured)
            or abs(measured-sum(c['seconds'] for c in calls)) > .002):
        raise ValueError('Hosted timing total mismatch')


def validate_successful_transcript(source, task, calls, protocol):
    """Independently enforce diagnosis ordering, narrowing and source binding."""
    stages = ['diagnosis','patch'] if protocol == 'ast_contract_v6' else ['patch']
    if len(calls) != len(stages)*len(task['symbols']):
        raise ValueError('Unexpected successful call sequence')
    proposals=[];position=0
    with tempfile.TemporaryDirectory(prefix='bf-transcript-check-') as directory:
        root=Path(directory);path=root/task['file']
        for symbol in task['symbols']:
            scope=editable_scope(source,symbol);narrowed=scope
            digest=hashlib.sha256(source.encode()).hexdigest()
            for kind in stages:
                call=calls[position];position+=1
                if (call.get('kind','patch') != kind or call['symbol'] != symbol
                        or call['source_sha256'] != digest):
                    raise ValueError('Call order or source provenance mismatch')
                prompt=json.loads(call['prompt'])
                if (prompt['approved_file'] != task['file'] or prompt['target_symbol'] != symbol
                        or prompt['editable_lines'] != (scope if kind=='diagnosis' else narrowed)):
                    raise ValueError('Prompt scope mismatch')
                if kind=='diagnosis':
                    diagnosis=json.loads(call['response'])
                    if (not isinstance(diagnosis,dict) or set(diagnosis) != {'lines','reason'}
                            or not isinstance(diagnosis['lines'],list) or not 1<=len(diagnosis['lines'])<=3
                            or any(type(i) is not int or i not in scope for i in diagnosis['lines'])
                            or len(set(diagnosis['lines'])) != len(diagnosis['lines'])
                            or not isinstance(diagnosis['reason'],str) or not 1<=len(diagnosis['reason'])<=400):
                        raise ValueError('Invalid diagnosis transcript')
                    narrowed=sorted(diagnosis['lines'])
                else:
                    if call['stage'] != 'source_validated':
                        raise ValueError('Patch was not validated')
                    path.write_text(source)
                    result=stage_lines(call['response'],root,task['file'],narrowed,digest)
                    source=result['files'][0]['content']
                    proposals.append({'symbol':symbol,'response':call['response']})
    return source,proposals


def verify(report, expected_revision=None):
    expected = {t['id']: t for t in MANIFEST['tasks']}
    if (report.get('benchmark') != 'boltons_26.1.0_curated_excerpts'
            or report.get('experiment') not in {'ast_contract_v5','ast_contract_v6','ast_contract_v7'}
            or report.get('blocked') != 0 or report.get('completed') != 5
            or report.get('paid_inference') is not False
            or report.get('external_submission') is not False):
        raise ValueError('Incomplete or unauthorized historical evidence')
    tasks = report.get('tasks', [])
    if len(tasks) != 5 or {t['id'] for t in tasks} != set(expected):
        raise ValueError('Unexpected historical case set')
    if (report.get('inference_provider') == 'groq' or report.get('experiment') == 'ast_contract_v7'
            or expected_revision is not None):
        validate_hosted_accounting(report, expected_revision)
    calls = [c for t in tasks for a in t['attempts'] for c in a['calls']]
    limit=8 if report.get('inference_provider')=='groq' else 24 if report['experiment']=='ast_contract_v6' else 12
    if len(calls) != report['model_calls'] or not 1 <= len(calls) <= limit:
        raise ValueError('Call accounting mismatch')
    for call in calls:
        if (not isinstance(call['response'], str) or len(call['response'].encode()) > 3000
                or len(call['prompt'].encode()) > 3600
                or type(call['max_tokens']) is not int or not 1 <= call['max_tokens'] <= 150
                or not math.isfinite(call['seconds']) or call['seconds'] < 0):
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
        checked,proposals=validate_successful_transcript(source,task,successful[0]['calls'],report['experiment'])
        revised = replay(task['id'], proposals)
        if checked != revised:
            raise ValueError('Narrow-scope and curated replay differ')
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
            'billing_independently_verified':False,
            'cases':verified}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', help='Required exact revision for hosted evaluation')
    args = parser.parse_args()
    raw = args.report.read_bytes()
    if len(raw) > 200000:
        raise ValueError('Evidence size bound exceeded')
    result = verify(json.loads(raw), expected_revision=args.revision)
    result['report_sha256'] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print('Independent replay passed:', result['passed'])
