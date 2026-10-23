"""Independently rerun admitted owned-model successes, without any inference.

Only the fixed owned development catalog is admitted. A reported success must
reconstruct through the original shared line validator and match its exact
recorded patch before fresh Docker admission or tests can run.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from benchmarks.phase5.development_runner import (
    MARKER, RECEIPT, SUITES, run_development_tests,
)
from bountyforge.curated_docker import (
    CuratedSandboxUnavailable, MARKER as HISTORICAL_MARKER, verify_runtime_boundary,
)
from bountyforge.curated_tasks import TASKS as HISTORICAL_TASKS, editable_scope
from bountyforge.drafts import DraftRejected
from bountyforge.lineedit import stage_lines
from scripts.validate_owned_canary import CanaryRejected, validate_owned_canary

MAX_REPORT_BYTES = 200_000


class OwnedReplayRejected(ValueError):
    pass


def replay_owned_canary(raw, *, suite, expected_revision):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_REPORT_BYTES:
        raise OwnedReplayRejected('Owned canary input exceeds the report budget')
    try:
        report = json.loads(raw)
    except (UnicodeError, ValueError):
        raise OwnedReplayRejected('Owned canary input is not valid JSON') from None
    # No Docker execution, including admission probes, occurs before this gate.
    validate_owned_canary(report, suite=suite, expected_revision=expected_revision)
    catalog, manifest = SUITES[suite]
    specs = {task['id']: task for task in manifest['tasks']}
    prepared = []
    for task in report['tasks']:
        if not task['model_generated_success']:
            continue
        spec = specs[task['id']]
        number = task['attempts'][-1]['number']
        calls = [call for call in task['calls'] if call['kind'] == 'patch' and call['round'] == number]
        if len(calls) != 1:
            raise OwnedReplayRejected('Successful round lacks one unambiguous patch response')
        response = calls[0]['response']
        trusted = catalog / task['id']
        source = (trusted / spec['file']).read_text()
        try:
            staged = stage_lines(response, trusted, spec['file'],
                                 editable_scope(source, spec['symbol']), spec['sha256'][spec['file']])
        except (DraftRejected, OSError, SyntaxError, TypeError, ValueError, KeyError):
            raise OwnedReplayRejected('Successful proposal failed independent source validation') from None
        candidate = staged['files'][0]
        if not isinstance(task.get('patch'), str) or task['patch'] != candidate['diff']:
            raise OwnedReplayRejected('Reported patch does not match the validated response')
        prepared.append((spec, response, candidate))

    replay = {'schema': 1, 'kind': 'owned_canary_independent_replay',
              'source_report_sha256': hashlib.sha256(raw).hexdigest(),
              'revision': expected_revision, 'suite': suite, 'protocol': report['protocol'],
              'model_calls': 0, 'inference_performed': False,
              'commercial_bounty': False, 'external_submission': False,
              'untrusted_execution_certified': False,
              'reported_success_ids': [spec['id'] for spec, _, _ in prepared],
              'verified_success_ids': [], 'verified_success_count': 0,
              'target_test_attempts': 0, 'status': 'blocked', 'tasks': []}
    try:
        # These are existing fixed trusted probes; the historical source is
        # admitted exactly but never imported or executed during preflight.
        with tempfile.TemporaryDirectory(prefix='bf-owned-replay-preflight-') as directory:
            baseline = Path(directory) / 'baseline'
            shutil.copytree(HISTORICAL_TASKS / '459', baseline)
            (baseline / HISTORICAL_MARKER).write_text('459')
            replay['sandbox_preflight'] = verify_runtime_boundary(baseline)
    except CuratedSandboxUnavailable:
        replay['failure_reason'] = 'independent_sandbox_admission_failed'
        return replay

    for spec, response, candidate in prepared:
        item = {'id': spec['id'], 'source_sha256': spec['sha256'][spec['file']],
                'tests_sha256': spec['sha256']['tests/test_regression.py'],
                'candidate_sha256': hashlib.sha256(candidate['content'].encode()).hexdigest(),
                'patch_sha256': hashlib.sha256(candidate['diff'].encode()).hexdigest(),
                'verified': False}
        replay['tasks'].append(item)
        with tempfile.TemporaryDirectory(prefix='bf-owned-independent-replay-') as directory:
            work = Path(directory) / 'candidate'
            shutil.copytree(catalog / spec['id'], work)
            (work / MARKER).write_text(spec['id'])
            (work / spec['file']).write_text(candidate['content'])
            (work / RECEIPT).write_text(json.dumps({'symbol': spec['symbol'], 'response': response}))
            replay['target_test_attempts'] += 1
            try:
                # This function rechecks the catalog, tests and replay receipt
                # before using the unchanged hardened Docker execution path.
                result = run_development_tests(work)
            except CuratedSandboxUnavailable:
                replay['failure_reason'] = 'independent_owned_execution_unavailable'
                return replay
            item['test'] = result
            passed = (isinstance(result, dict) and result.get('passed') is True
                      and type(result.get('returncode')) is int and result['returncode'] == 0
                      and result.get('timeout') is False and result.get('error') is None
                      and isinstance(result.get('output'), str)
                      and re.search(r'Ran [1-9][0-9]* tests?', result['output']) is not None
                      and result['output'].rstrip().endswith('OK'))
            if not passed:
                replay['status'] = 'replay_failed'
                replay['failure_reason'] = 'independent_owned_tests_failed'
                return replay
            item['verified'] = True
            replay['verified_success_ids'].append(spec['id'])
            replay['verified_success_count'] = len(replay['verified_success_ids'])
    replay['status'] = 'completed'
    return replay


def write_report(path, report):
    data = json.dumps(report, indent=2, ensure_ascii=True).encode() + b'\n'
    if len(data) > MAX_REPORT_BYTES:
        raise OwnedReplayRejected('Owned replay output exceeds the report budget')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(data)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('--suite', choices=tuple(SUITES), required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = b''
    try:
        with args.report.open('rb') as source:
            raw = source.read(MAX_REPORT_BYTES + 1)
        result = replay_owned_canary(raw, suite=args.suite, expected_revision=args.revision)
    except (CanaryRejected, OwnedReplayRejected, OSError):
        result = {'schema': 1, 'kind': 'owned_canary_independent_replay',
                  'source_report_sha256': hashlib.sha256(raw).hexdigest() if 0 < len(raw) <= MAX_REPORT_BYTES else None,
                  'status': 'rejected', 'failure_reason': 'input_or_proposal_validation_failed',
                  'model_calls': 0, 'inference_performed': False,
                  'verified_success_ids': [], 'verified_success_count': 0,
                  'target_test_attempts': 0, 'commercial_bounty': False,
                  'external_submission': False, 'untrusted_execution_certified': False}
    write_report(args.output, result)
    print('Independent owned replay:', result['status'],
          'verified repairs:', result['verified_success_count'], 'model calls: 0')
    return 0 if result['status'] == 'completed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
