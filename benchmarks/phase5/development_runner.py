"""Bounded local inference on a fixed, owned development catalog.

This deliberately does not change curated historical admission or its tests.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from bountyforge.curated_docker import (
    CuratedSandboxUnavailable, IMAGE, MARKER as HISTORICAL_MARKER,
    _execute, verify_runtime_boundary,
)
from bountyforge.curated_tasks import TASKS as HISTORICAL_TASKS, editable_scope
from bountyforge.drafts import DraftRejected
from bountyforge.lineedit import propose_lines, stage_lines
from bountyforge.model import LocalModel

ROOT = Path(__file__).resolve().parent
TASKS = ROOT / 'tasks'
MANIFEST = json.loads((TASKS / 'manifest.json').read_text())
STRUCTURAL_TASKS = ROOT / 'structural_tasks'
STRUCTURAL_MANIFEST = json.loads((STRUCTURAL_TASKS / 'manifest.json').read_text())
SUITES = {'original': (TASKS, MANIFEST), 'structural': (STRUCTURAL_TASKS, STRUCTURAL_MANIFEST)}
MARKER = '.bountyforge-owned-development'
RECEIPT = '.bountyforge-development-proposal.json'
PROTOCOLS = ('legacy', 'ast_contract_v5', 'ast_contract_v6', 'ast_contract_v7')


def task_spec(task_id):
    found = [task for _, manifest in SUITES.values() for task in manifest['tasks'] if task['id'] == task_id]
    if len(found) != 1:
        raise CuratedSandboxUnavailable('Unknown owned development task')
    return found[0]


def trusted_task_directory(task_id):
    task_spec(task_id)  # Fail closed on unknown or multiply defined IDs.
    return next(directory / task_id for directory, manifest in SUITES.values()
                if any(task['id'] == task_id for task in manifest['tasks']))


def verify_development(root):
    """Admit exact owned tests and replayed bounded proposals; never arbitrary code."""
    root = Path(root)
    if root.is_symlink():
        raise CuratedSandboxUnavailable('Symlinked development root')
    root = root.resolve(strict=True)
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise CuratedSandboxUnavailable('Unsafe development filesystem object')
        if path.is_file():
            if path.stat().st_nlink != 1 or path.stat().st_size > 12000:
                raise CuratedSandboxUnavailable('Development file exceeds bounds')
            actual.add(path.relative_to(root).as_posix())
    try:
        task = task_spec((root / MARKER).read_text())
        trusted = trusted_task_directory(task['id'])
        expected = set(task['sha256']) | {MARKER}
        if actual not in (expected, expected | {RECEIPT}):
            raise CuratedSandboxUnavailable('Unexpected development file')
        for filename, digest in task['sha256'].items():
            if hashlib.sha256((trusted / filename).read_bytes()).hexdigest() != digest:
                raise CuratedSandboxUnavailable('Owned catalog hash changed')
            if filename != task['file'] and (root / filename).read_bytes() != (trusted / filename).read_bytes():
                raise CuratedSandboxUnavailable('Owned acceptance tests changed')
        original = (trusted / task['file']).read_text()
        revised = original
        if (root / RECEIPT).exists():
            receipt = json.loads((root / RECEIPT).read_text())
            if (not isinstance(receipt, dict) or set(receipt) != {'symbol', 'response'}
                    or receipt['symbol'] != task['symbol']):
                raise CuratedSandboxUnavailable('Invalid development receipt')
            staged = stage_lines(receipt['response'], trusted, task['file'],
                                 editable_scope(original, task['symbol']),
                                 hashlib.sha256(original.encode()).hexdigest())
            revised = staged['files'][0]['content']
        if (root / task['file']).read_text() != revised:
            raise CuratedSandboxUnavailable('Development source lacks validated provenance')
    except (OSError, ValueError, TypeError, KeyError, SyntaxError, DraftRejected) as exc:
        raise CuratedSandboxUnavailable('Development admission failed') from exc
    return root


def run_development_tests(root, timeout=12):
    if type(timeout) is not int or not 2 <= timeout <= 20:
        raise ValueError('Development timeout must remain bounded')
    root = verify_development(root)
    if shutil.which('docker') is None:
        raise CuratedSandboxUnavailable('Docker unavailable; no host test fallback')
    result = _execute(root, None, timeout)
    result['passed'] = (result['passed']
                        and re.search(r'Ran [1-9][0-9]* tests?', result['output']) is not None
                        and result['output'].rstrip().endswith('OK'))
    return result


def run(*, model=None, output=None, protocol='ast_contract_v5', suite='original'):
    if protocol not in PROTOCOLS:
        raise ValueError('Unknown development protocol')
    if suite not in SUITES:
        raise ValueError('Unknown owned development suite')
    task_directory, manifest = SUITES[suite]
    model = model or LocalModel('http://127.0.0.1:18080/v1/chat/completions')
    output = Path(output or ROOT.parents[1] / 'evidence-run/phase5-development.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    revision = os.environ.get('GITHUB_SHA') or subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    report = {'schema': 1, 'benchmark': 'owned_phase5_development',
              'commercial_bounty': False, 'historical_evaluation': False,
              'revision': revision, 'protocol': protocol, 'suite': suite, 'image': IMAGE,
              'model_calls': 0, 'max_model_calls': 16 if protocol == 'ast_contract_v6' else 8,
              'max_attempts_per_task': 2,
              'paid_inference': False, 'external_submission': False, 'tasks': []}

    def save():
        report['passed'] = sum(task['model_generated_success'] for task in report['tasks'])
        report['attempted'] = sum(bool(task['calls']) for task in report['tasks'])
        temporary = output.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n')
        temporary.replace(output)

    # Reuse independently tested runtime controls without widening their
    # existing curated admission API. Probe commands do not execute task source.
    try:
        with tempfile.TemporaryDirectory(prefix='bf-dev-preflight-') as directory:
            preflight = Path(directory) / 'baseline'
            shutil.copytree(HISTORICAL_TASKS / '459', preflight)
            (preflight / HISTORICAL_MARKER).write_text('459')
            report['sandbox_preflight'] = verify_runtime_boundary(preflight)
    except CuratedSandboxUnavailable as exc:
        report['blocked'] = 'sandbox_admission_failed'
        report['message'] = str(exc)[:300]
        save()
        return report

    inference_available = True
    for task in manifest['tasks']:
        started = time.monotonic()
        item = {'id': task['id'], 'symbol': task['symbol'], 'calls': [], 'attempts': [],
                'status': 'blocked', 'model_generated_success': False,
                'source_sha256': task['sha256'][task['file']],
                'tests_sha256': task['sha256']['tests/test_regression.py']}
        report['tasks'].append(item)
        with tempfile.TemporaryDirectory(prefix='bf-development-') as directory:
            base = Path(directory) / 'baseline'
            shutil.copytree(task_directory / task['id'], base)
            (base / MARKER).write_text(task['id'])
            baseline = run_development_tests(base)
            item['baseline'] = baseline
            item['baseline_reproduced'] = (baseline.get('returncode') == 1
                                           and not baseline['passed']
                                           and re.search(r'FAILED \((?:failures|errors)=[1-9]', baseline['output']) is not None)
            if not item['baseline_reproduced']:
                item['failure_reason'] = 'baseline_not_reproduced'
            elif not inference_available:
                item['failure_reason'] = 'inference_disabled_after_failure'
            else:
                previous_failure = baseline['output']
                previous_response = ''
                item['status'] = 'failed'
                for number in range(1, 3):
                    work = Path(directory) / f'attempt-{number}'
                    shutil.copytree(base, work)
                    one = {'number': number, 'status': 'failed'}
                    item['attempts'].append(one)

                    class RecordingModel:
                        response = ''

                        def _complete(self, kind, system, prompt, max_tokens):
                            if report['model_calls'] >= report['max_model_calls']:
                                raise RuntimeError('Development model budget exhausted')
                            call = {'number': report['model_calls'] + 1, 'kind': kind,
                                    'round': number, 'system': system, 'prompt': prompt,
                                    'max_tokens': max_tokens, 'response': None}
                            report['model_calls'] += 1
                            item['calls'].append(call)
                            generated = time.monotonic()
                            try:
                                model.last_call = None
                                complete = model.complete_diagnosis if kind == 'diagnosis' else model.complete_line
                                response = complete(system, prompt, max_tokens)
                                if kind == 'patch':
                                    self.response = response
                                call['response'] = response
                                call['response_sha256'] = hashlib.sha256(response.encode()).hexdigest()
                                return response
                            except Exception as exc:
                                call['error'] = type(exc).__name__
                                raise
                            finally:
                                call['seconds'] = round(time.monotonic() - generated, 3)
                                call['metadata'] = getattr(model, 'last_call', None)
                                save()

                        def complete_line(self, system, prompt, max_tokens):
                            return self._complete('patch', system, prompt, max_tokens)

                        def complete_diagnosis(self, system, prompt, max_tokens=125):
                            return self._complete('diagnosis', system, prompt, max_tokens)

                    recorder = RecordingModel()
                    source = (work / task['file']).read_text()
                    issue = {'verification': 'unverified_candidate',
                             'url': 'owned-development:' + task['id'],
                             'description_excerpt': task['description'],
                             'test_failure_excerpt': previous_failure,
                             'baseline_failure': baseline['output'],
                             'prior_error': previous_failure if number > 1 else '',
                             'target_symbol': task['symbol'],
                             'test_contract_untrusted': (base / 'tests/test_regression.py').read_text(),
                             'previous_proposal': previous_response}
                    if protocol != 'legacy':
                        issue['repair_protocol'] = protocol
                    try:
                        proposed = propose_lines(issue, work, task['file'],
                                                 editable_scope(source, task['symbol']), recorder)
                        (work / task['file']).write_text(proposed['files'][0]['content'])
                        (work / RECEIPT).write_text(json.dumps(
                            {'symbol': task['symbol'], 'response': recorder.response}))
                        check = run_development_tests(work)
                        one['test'] = check
                        previous_failure = check['output']
                        if check['passed']:
                            one['status'] = 'passed'
                            item['status'] = 'owned_development_passed'
                            item['model_generated_success'] = True
                            item['patch'] = proposed['files'][0]['diff']
                            break
                        one['failure_reason'] = 'targeted_tests_failed'
                    except (ValueError, SyntaxError, KeyError, TypeError) as exc:
                        one['failure_reason'] = 'proposal_rejected'
                        one['message'] = str(exc)[:300]
                        previous_failure = one['message']
                    except (RuntimeError, TimeoutError) as exc:
                        one['failure_reason'] = 'inference_or_sandbox_unavailable'
                        one['message'] = str(exc)[:300]
                        inference_available = False
                        break
                    finally:
                        previous_response = recorder.response
                        save()
        item['elapsed_seconds'] = round(time.monotonic() - started, 3)
        save()
        print(task['id'], item['status'], 'calls', len(item['calls']), flush=True)
    report['inference_seconds'] = round(sum(call['seconds'] for task in report['tasks']
                                          for call in task['calls']), 3)
    save()
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--protocol', choices=PROTOCOLS, default='ast_contract_v5')
    parser.add_argument('--suite', choices=tuple(SUITES), default='original')
    arguments = parser.parse_args()
    result = run(output=arguments.output, protocol=arguments.protocol, suite=arguments.suite)
    print('DEVELOPMENT', result['passed'], '/', result['attempted'], 'calls', result['model_calls'])
    if result.get('blocked') or any(task['status'] == 'blocked' for task in result['tasks']):
        raise SystemExit(2)
