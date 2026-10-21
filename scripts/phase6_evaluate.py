"""Frozen owned maintenance comparison; no customer or arbitrary-source admission.

Every execution uses the existing hardened Docker primitive after exact catalog
and response replay validation. No model, host execution or provider fallback
is selected implicitly. One attempt per case/arm, eight requests maximum.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from bountyforge.curated_docker import IMAGE, CuratedSandboxUnavailable, _execute
from bountyforge.curated_tasks import editable_scope
from bountyforge.drafts import DraftRejected
from bountyforge.groq_adapter import HostedGroqModel, MODEL_ID
from bountyforge.lineedit import stage_lines
from bountyforge.statements import stage_statements
from bountyforge.worker import FIXTURE_MARKER, repair_fixture

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / 'benchmarks/phase6/evaluation_tasks'
MAX_REPORT_BYTES = 200_000
CORE_REVISION = '5f3f0cc668d3993f013759133223e204fa61c904'
CATALOG_REVISION = '7687104d0b34d43f6b08ce598df2e764e467ec3b'
CATALOG_SHA256 = 'f46c86ae7bb86340f8bb195001a68a5eb868c608b5a3b584bbc6284a4e7179bf'
CORE_SHA256 = {
    'bountyforge/worker.py': '564678b2c00c750ee580a4bb802d9f5236258b2d7cf24b30da03ebfdf4d655fb',
    'bountyforge/statements.py': '7ee92b1a794ce221042196ac7e5fedd97792691184f3d2709d182787ecfeb460',
    'bountyforge/lineedit.py': 'cfafdde8490cd3f7f84e7f3ef3a10aa0bc43973baa3468ec431e7ee4d2205e14',
    'bountyforge/repair_context.py': 'fb0aac6f25e7ad23e7fbedba20d6638c523c5304508bedfcd5b892d419f7b70f',
    'bountyforge/curated_tasks.py': '048bf0efe8e44278d4fb5a34ebc951b1d27c7034fb28a77da94f6990b965d48f',
    'bountyforge/curated_docker.py': '0beb01183867f514029f466274e641f5e9e2860de7a56d34fe725a12b61dfa2f',
    'bountyforge/groq_adapter.py': '6e808c41baab332356af5ac27d15b115b673dd4c0aedf2f608d5071b36298137',
    'bountyforge/drafts.py': 'e5336eb40548b72fae901d6b281ffd0d45de5d2cbf04f0189f2721f700b29af5',
    'bountyforge/line_scope.py': 'df2d83ccc9f290b387df299625c63fe16729a63029cc481c9a05d00adc0f6128',
}
CONTROLS = (
    'network_denied', 'loopback_inference_unreachable', 'source_writes_denied',
    'root_writes_denied', 'secrets_absent', 'uid_unprivileged', 'capabilities_empty',
    'no_new_privileges', 'seccomp_active', 'memory_limit_enforced', 'swap_disabled',
    'cpu_quota_verified', 'pid_limit_verified', 'tmpfs_bounded_noexec',
    'wall_clock_enforced', 'cleanup_verified', 'output_bounded',
    'docker_socket_absent', 'pid_pressure_enforced', 'cpu_pressure_enforced',
)


class EvaluationRejected(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_proof(proof):
    if (not isinstance(proof, dict) or not all(proof.get(k) is True for k in CONTROLS)
            or proof.get('image_digest') != IMAGE.split('@')[1]
            or proof.get('untrusted_execution_certified') is not False):
        raise EvaluationRejected('Complete fixed Docker admission proof required')


def catalog():
    raw = (TASKS / 'manifest.json').read_bytes()
    if digest(raw) != CATALOG_SHA256:
        raise EvaluationRejected('Evaluation catalog manifest changed')
    data = json.loads(raw)
    if len(data['tasks']) != 4 or len({t['id'] for t in data['tasks']}) != 4:
        raise EvaluationRejected('Evaluation requires four unique pinned cases')
    for name, expected in CORE_SHA256.items():
        if digest((ROOT / name).read_bytes()) != expected:
            raise EvaluationRejected('Frozen repair core changed')
    for spec in data['tasks']:
        if (spec['file'] != 'subject.py' or set(spec['sha256']) != {'subject.py', 'tests/test_regression.py'}
                or not re.fullmatch(r'[a-z_]+', spec['id'])):
            raise EvaluationRejected('Unrecognized owned catalog shape')
        for name, expected in spec['sha256'].items():
            path = TASKS / spec['id'] / name
            if path.is_symlink() or path.stat().st_nlink != 1 or digest(path.read_bytes()) != expected:
                raise EvaluationRejected('Pinned evaluation source or tests changed')
    return data


def order_for(tasks):
    return [(spec, arm) for index, spec in enumerate(tasks)
            for arm in (('line', 'statement') if index % 2 == 0 else ('statement', 'line'))]


def stage_response(spec, arm, response):
    if arm not in ('line', 'statement'):
        raise EvaluationRejected('Unknown repair arm')
    original = (TASKS / spec['id'] / spec['file']).read_text()
    stage = stage_lines if arm == 'line' else stage_statements
    return stage(response, TASKS / spec['id'], spec['file'],
                 editable_scope(original, spec['symbol']), spec['sha256'][spec['file']])['files'][0]


def admit(root, spec, *, arm, response):
    """Nonexecuting exact-tree admission; response never chooses a file or span."""
    manifest = catalog()  # Recheck pins/core on every execution/cache request.
    if spec not in manifest['tasks']:
        raise EvaluationRejected('Unrecognized or modified catalog task metadata')
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise EvaluationRejected('Invalid owned evaluation root')
    root = root.resolve(strict=True)
    files, directories = set(), set()
    for path in root.rglob('*'):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise EvaluationRejected('Unsafe evaluation filesystem object')
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.add(relative)
        else:
            info = path.stat()
            if info.st_nlink != 1 or info.st_size > 12000:
                raise EvaluationRejected('Evaluation file exceeds immutable bounds')
            files.add(relative)
    if directories != {'tests'} or files != {spec['file'], 'tests/test_regression.py', FIXTURE_MARKER}:
        raise EvaluationRejected('Unexpected evaluation file or directory')
    if (root / FIXTURE_MARKER).read_text() != spec['id']:
        raise EvaluationRejected('Evaluation marker mismatch')
    if digest((root / 'tests/test_regression.py').read_bytes()) != spec['sha256']['tests/test_regression.py']:
        raise EvaluationRejected('Evaluation acceptance tests changed')
    original = (TASKS / spec['id'] / spec['file']).read_text()
    expected = original
    if response is not None:
        try:
            expected = stage_response(spec, arm, response)['content']
        except (DraftRejected, SyntaxError, TypeError, KeyError, ValueError):
            raise EvaluationRejected('Candidate response failed original-scope replay') from None
    if (root / spec['file']).read_text() != expected:
        raise EvaluationRejected('Evaluation source lacks exact response provenance')
    return root


def test_result(root):
    result = _execute(root, None, 12)
    if result.get('error') or result.get('timeout'):
        raise CuratedSandboxUnavailable('Owned Docker execution failed or exhausted budget')
    output = result.get('output', '')
    if not isinstance(output, str) or len(output.encode()) > 6000:
        raise CuratedSandboxUnavailable('Owned Docker output exceeds budget')
    passed = (result.get('passed') is True and result.get('returncode') == 0
              and re.search(r'Ran [1-9][0-9]* tests?', output) is not None
              and output.rstrip().endswith('OK'))
    if result.get('returncode') not in (0, 1):
        raise CuratedSandboxUnavailable('Owned Docker process did not complete tests')
    return {'passed': passed, 'exit_code': result['returncode'], 'timeout': False,
            'output': output, 'seconds': result.get('elapsed_seconds'),
            'sandbox': 'digest_pinned_docker_no_network_read_only_no_privileges',
            'untrusted_execution_certified': False}


def assertion_baseline(result):
    return (result.get('passed') is False and result.get('exit_code') == 1
            and result.get('timeout') is False and 'FAIL:' in result.get('output', '')
            and 'FAILED (failures=' in result['output'] and 'errors=' not in result['output'])


def write_report(path, report):
    raw = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False).encode() + b'\n'
    if len(raw) > MAX_REPORT_BYTES:
        raise EvaluationRejected('Evaluation evidence exceeds report budget')
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(raw); temporary.replace(path)


def completed_model_call(call):
    metadata = call.get('metadata')
    return (not call.get('error') and isinstance(metadata, dict)
            and metadata.get('provider') == 'groq' and metadata.get('model') == MODEL_ID
            and metadata.get('provider_model_reported') == MODEL_ID
            and metadata.get('finish_reason') == 'stop'
            and metadata.get('requested_max_completion_tokens') == 1024
            and type(metadata.get('prompt_tokens')) is int and metadata['prompt_tokens'] > 0
            and type(metadata.get('completion_tokens')) is int and 1 <= metadata['completion_tokens'] <= 1024
            and type(metadata.get('total_tokens')) is int
            and metadata['total_tokens'] == metadata['prompt_tokens']+metadata['completion_tokens']
            and isinstance(call.get('response'), str) and 0 < len(call['response'].encode()) <= 3000
            and call.get('response_sha256') == digest(call['response'].encode()))


def evaluate(*, model, proof, output, revision):
    validate_proof(proof)
    manifest = catalog()
    if (not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision)
            or getattr(model, 'total_generation_tokens', None) != 1024
            or getattr(model, 'minimum_interval_seconds', None) != 60
            or type(getattr(model, 'calls', None)) is not int or model.calls != 0):
        raise EvaluationRejected('Explicit fresh model, fixed budget and revision required')
    planned = order_for(manifest['tasks'])
    report = {'schema': 1, 'kind': 'owned_maintenance_paired_evaluation', 'revision': revision,
              'core_revision': CORE_REVISION, 'core_sha256': CORE_SHA256,
              'catalog_revision': CATALOG_REVISION, 'catalog_manifest_sha256': CATALOG_SHA256,
              'image': IMAGE, 'sandbox_preflight': copy.deepcopy(proof), 'status': 'running',
              'commercial_bounty': False, 'external_submission': False,
              'billing_independently_verified': False, 'customer_source_accepted': False,
              'max_model_calls': 8, 'max_attempts_per_arm': 1, 'model_calls': 0,
              'inference_backend': {'provider': 'groq', 'model': MODEL_ID,
                                    'total_generation_tokens_per_call': 1024, 'minimum_interval_seconds': 60},
              'baselines': {}, 'calls': [], 'arms': [
                  {'id': spec['id'], 'arm': arm, 'status': 'pending', 'model_generated_success': False,
                   'source_sha256': spec['sha256'][spec['file']],
                   'tests_sha256': spec['sha256']['tests/test_regression.py'], 'call_numbers': []}
                  for spec, arm in planned]}

    def save():
        report['model_calls'] = model.calls
        report['inference_backend']['transport_calls'] = model.calls
        report['scores'] = {arm: sum(row['model_generated_success'] for row in report['arms']
                                     if row['arm'] == arm) for arm in ('line', 'statement')}
        report['adapter_wall_seconds_including_pacing'] = round(sum(c.get('seconds', 0) for c in report['calls']), 3)
        write_report(output, report)

    save()
    # Execute each pinned original only once; every later cache read still
    # checks exact filesystem/source/tests/capability admission first.
    try:
        for spec in manifest['tasks']:
            with tempfile.TemporaryDirectory(prefix='bf-phase6-baseline-') as directory:
                root = Path(directory)/'case'; shutil.copytree(TASKS/spec['id'], root)
                (root/FIXTURE_MARKER).write_text(spec['id'])
                admit(root, spec, arm='line', response=None)
                result = test_result(root)
                report['baselines'][spec['id']] = result
                if not assertion_baseline(result):
                    raise CuratedSandboxUnavailable('Baseline is not an assertion-only failure')
                save()
    except (EvaluationRejected, CuratedSandboxUnavailable, OSError):
        report['status'] = 'blocked'; report['failure_reason'] = 'baseline_or_sandbox_unavailable'
        for row in report['arms']:
            row.update(status='blocked', failure_reason=report['failure_reason'])
        save(); return report

    inference_available = True
    for row, (spec, arm) in zip(report['arms'], planned):
        if not inference_available:
            row.update(status='blocked', failure_reason='inference_disabled_after_failure')
            save(); continue
        row['status'] = 'running'

        class RecordingModel:
            response = None
            last_call = None
            def complete_line(self, system, prompt, max_tokens):
                if len(report['calls']) >= 8:
                    raise RuntimeError('Owned paired model-call budget exhausted')
                call = {'number': len(report['calls'])+1, 'id': spec['id'], 'arm': arm,
                        'system': system, 'prompt': prompt, 'max_tokens': max_tokens,
                        'response': None, 'metadata': None}
                report['calls'].append(call); row['call_numbers'].append(call['number'])
                save()  # Persist intent before HTTP; interruption leaves an explicitly incomplete record.
                started = time.monotonic()
                try:
                    model.last_call = None
                    response = model.complete_line(system, prompt, max_tokens)
                    if not isinstance(response, str):
                        raise RuntimeError('Unexpected model response type')
                    self.response = response
                    call['response'] = response; call['response_sha256'] = digest(response.encode())
                    return response
                except Exception as exc:
                    call['error'] = type(exc).__name__
                    raise
                finally:
                    call['seconds'] = round(time.monotonic()-started, 3)
                    self.last_call = copy.deepcopy(getattr(model, 'last_call', None))
                    call['metadata'] = self.last_call
                    save()

        recorder = RecordingModel()

        def runner(root):
            original = (TASKS/spec['id']/spec['file']).read_text()
            candidate = (Path(root)/spec['file']).read_text()
            try:
                admit(root, spec, arm=arm, response=None if candidate == original else recorder.response)
            except (EvaluationRejected, OSError) as exc:
                raise CuratedSandboxUnavailable('Owned candidate admission failed') from exc
            if candidate == original:
                return copy.deepcopy(report['baselines'][spec['id']])
            return test_result(root)

        source = (TASKS/spec['id']/spec['file']).read_text()
        issue = {'verification': 'unverified_candidate', 'url': 'owned-evaluation:'+spec['id'],
                 'title': 'Owned maintenance comparison', 'description_excerpt': spec['description'],
                 'target_symbol': spec['symbol'], 'repair_protocol': 'ast_contract_v7',
                 'test_contract_untrusted': (TASKS/spec['id']/'tests/test_regression.py').read_text()}
        with tempfile.TemporaryDirectory(prefix='bf-phase6-owned-') as directory:
            root = Path(directory)/'case'; shutil.copytree(TASKS/spec['id'], root)
            (root/FIXTURE_MARKER).write_text(spec['id'])
            worker = repair_fixture(issue, root, [spec['file']], recorder, max_attempts=1,
                                    strategy=arm, editable_lines={spec['file']: editable_scope(source, spec['symbol'])},
                                    test_runner=runner)
        row['worker'] = worker
        if any(a.get('error') == 'model_or_runner_unavailable' for a in worker.get('attempts', [])):
            row.update(status='blocked', failure_reason='inference_or_sandbox_unavailable')
            inference_available = False
        elif worker.get('error') in ('baseline_not_assertion_failure', 'baseline_timeout', 'baseline_does_not_reproduce'):
            row.update(status='blocked', failure_reason='baseline_contract_failed')
            inference_available = False
        elif worker['status'] == 'review_ready':
            row.update(status='candidate_passed', model_generated_success=True)
        else:
            row['status'] = 'failed'
            if not row['call_numbers']:
                row['failure_reason'] = 'scope_or_context_rejected_before_inference'
            if recorder.response is not None:
                try:
                    stage_response(spec, arm, recorder.response)
                except (DraftRejected, SyntaxError, ValueError, KeyError, TypeError) as exc:
                    row['source_validation_error'] = str(exc)[:450]
        if not row['call_numbers']:
            row.update(status='blocked', model_generated_success=False,
                       failure_reason='scope_or_context_rejected_before_inference')
        elif (len(row['call_numbers']) != 1 or model.calls != len(report['calls'])
              or not completed_model_call(report['calls'][row['call_numbers'][0]-1])):
            row.update(status='blocked', model_generated_success=False,
                       failure_reason='inference_accounting_unavailable')
            inference_available = False
        save()
    complete = (not any(row['status'] == 'blocked' for row in report['arms'])
                and len(report['calls']) == model.calls == 8
                and all(completed_model_call(call) for call in report['calls']))
    report['status'] = 'completed' if complete else 'blocked'
    report['score_final'] = report['status'] == 'completed'
    save()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Explicit approved owned-only Free Plan experiment')
    parser.add_argument('--proof', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not args.live:
        parser.error('No default model or fallback; explicit --live required')
    with args.proof.open('rb') as source:
        raw = source.read(MAX_REPORT_BYTES+1)
    if len(raw) > MAX_REPORT_BYTES:
        raise EvaluationRejected('Admission proof exceeds budget')
    proof = json.loads(raw); validate_proof(proof); catalog()
    revision = os.environ.get('GITHUB_SHA') or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    model = HostedGroqModel(total_generation_tokens=1024, minimum_interval_seconds=60)
    result = evaluate(model=model, proof=proof, output=args.output, revision=revision)
    print('Owned paired experiment:', result['status'], 'scores', result['scores'], 'calls', result['model_calls'])
    return 0 if result['status'] == 'completed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
