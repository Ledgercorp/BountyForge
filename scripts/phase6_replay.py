"""Validate every paired record, then independently rerun claimed successes.

No model is constructed. All source comes from the frozen owned catalog, every
candidate is reconstructed through the shared validator, and one fresh Docker
preflight precedes the independently tested candidates. No host fallback.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path

from bountyforge.curated_docker import (
    CuratedSandboxUnavailable, MARKER as HISTORICAL_MARKER, _execute, verify_runtime_boundary,
)
from bountyforge.curated_tasks import TASKS as HISTORICAL_TASKS, editable_scope
from bountyforge.drafts import DraftRejected
from bountyforge.groq_adapter import MODEL_ID
from bountyforge.lineedit import propose_lines
from bountyforge.statements import propose_statements, statement_catalog
from scripts.phase6_evaluate import (
    TASKS, MAX_REPORT_BYTES, CORE_REVISION, CORE_SHA256, CATALOG_REVISION,
    CATALOG_SHA256, IMAGE, FIXTURE_MARKER, EvaluationRejected, catalog, order_for,
    digest, validate_proof, assertion_baseline, stage_response, admit, write_report,
)


def require(condition, message):
    if not condition:
        raise EvaluationRejected(message)


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def test_passed(check):
    return (isinstance(check, dict) and check.get('passed') is True
            and type(check.get('exit_code')) is int and check['exit_code'] == 0
            and check.get('timeout') is False and isinstance(check.get('output'), str)
            and len(check['output'].encode()) <= 6000
            and re.search(r'Ran [1-9][0-9]* tests?', check['output']) is not None
            and check['output'].rstrip().endswith('OK'))


def capture_prompt(spec, arm, baseline, response):
    """Rebuild source context without inference or execution; inspect exact transcript."""
    issue = {'verification': 'unverified_candidate', 'url': 'owned-evaluation:'+spec['id'],
             'title': 'Owned maintenance comparison', 'description_excerpt': spec['description'],
             'target_symbol': spec['symbol'], 'repair_protocol': 'ast_contract_v7',
             'test_contract_untrusted': (TASKS/spec['id']/'tests/test_regression.py').read_text()}
    if arm == 'line':
        issue.update(test_failure_excerpt=baseline['output'][-700:], prior_error='')
        propose = propose_lines
    else:
        issue.update(baseline_failure=baseline['output'], test_failure_excerpt=baseline['output'],
                     prior_error='', previous_proposal='')
        propose = propose_statements
    captured = []
    class Capture:
        def complete_line(self, system, prompt, max_tokens):
            captured.append((system, prompt, max_tokens))
            return response
    source = (TASKS/spec['id']/spec['file']).read_text()
    try:
        propose(issue, TASKS/spec['id'], spec['file'], editable_scope(source, spec['symbol']), Capture())
    except (DraftRejected, ValueError, SyntaxError, KeyError, TypeError):
        pass  # Source rejection is valid failed-repair evidence; prompt must still bind.
    return captured


def validate_prompt(call, spec, arm, baseline):
    require(capture_prompt(spec, arm, baseline, call['response']) ==
            [(call['system'], call['prompt'], call['max_tokens'])],
            'Model prompt does not reproduce frozen scope/context')


def validate_report(raw, *, expected_revision):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_REPORT_BYTES, 'Paired report exceeds byte budget')
    try:
        report = json.loads(raw)
    except (ValueError, UnicodeError):
        raise EvaluationRejected('Paired report is not JSON') from None
    require(isinstance(report, dict), 'Paired report must be an object')
    require(isinstance(expected_revision, str) and re.fullmatch(r'[0-9a-f]{40}', expected_revision),
            'Exact expected revision required')
    require(report.get('revision') == expected_revision and report.get('schema') == 1
            and report.get('kind') == 'owned_maintenance_paired_evaluation'
            and report.get('status') == 'completed' and report.get('score_final') is True,
            'Paired experiment incomplete, blocked or wrong revision')
    require(report.get('core_revision') == CORE_REVISION and report.get('core_sha256') == CORE_SHA256
            and report.get('catalog_revision') == CATALOG_REVISION
            and report.get('catalog_manifest_sha256') == CATALOG_SHA256
            and report.get('image') == IMAGE, 'Frozen core/catalog/image identity mismatch')
    for flag in ('commercial_bounty', 'external_submission', 'billing_independently_verified', 'customer_source_accepted'):
        require(report.get(flag) is False, 'Boundary flag missing or unauthorized')
    require(type(report.get('max_model_calls')) is int and report['max_model_calls'] == 8
            and type(report.get('max_attempts_per_arm')) is int and report['max_attempts_per_arm'] == 1,
            'Paired resource budget changed')
    validate_proof(report.get('sandbox_preflight'))
    manifest = catalog(); planned = order_for(manifest['tasks'])
    baselines = report.get('baselines')
    require(isinstance(baselines, dict) and set(baselines) == {spec['id'] for spec in manifest['tasks']},
            'Four reproduced baseline records required')
    for baseline in baselines.values():
        require(isinstance(baseline, dict) and assertion_baseline(baseline)
                and isinstance(baseline.get('output'), str) and len(baseline['output'].encode()) <= 6000
                and finite_number(baseline.get('seconds')), 'Baseline did not reproduce assertion-only failure')
    rows = report.get('arms'); calls = report.get('calls')
    require(isinstance(rows, list) and len(rows) == 8 and all(isinstance(row, dict) for row in rows),
            'Exactly eight paired arms required')
    require(isinstance(calls, list) and len(calls) == 8 and all(isinstance(call, dict) for call in calls),
            'Invalid paired inference call list')
    count = report.get('model_calls')
    require(type(count) is int and count == len(calls), 'Paired transport/call accounting mismatch')
    backend = report.get('inference_backend', {})
    require(isinstance(backend, dict) and backend.get('provider') == 'groq' and backend.get('model') == MODEL_ID
            and type(backend.get('transport_calls')) is int and backend['transport_calls'] == count
            and backend.get('total_generation_tokens_per_call') == 1024
            and backend.get('minimum_interval_seconds') == 60, 'Paired provider or transport budget mismatch')
    require([c.get('number') for c in calls] == list(range(1, count+1)), 'Model call sequence mismatch')
    for call in calls:
        metadata = call.get('metadata')
        require(not call.get('error') and isinstance(metadata, dict)
                and metadata.get('provider') == 'groq' and metadata.get('model') == MODEL_ID
                and metadata.get('provider_model_reported') == MODEL_ID and metadata.get('finish_reason') == 'stop'
                and metadata.get('requested_max_completion_tokens') == 1024
                and type(metadata.get('prompt_tokens')) is int and metadata['prompt_tokens'] > 0
                and type(metadata.get('completion_tokens')) is int and 1 <= metadata['completion_tokens'] <= 1024
                and type(metadata.get('total_tokens')) is int
                and metadata['total_tokens'] == metadata['prompt_tokens']+metadata['completion_tokens'],
                'Completed model identity or token usage invalid')
        reasoning = metadata.get('reasoning_tokens')
        require(reasoning is None or (type(reasoning) is int and 0 <= reasoning <= metadata['completion_tokens']),
                'Reasoning usage invalid')
        require(isinstance(call.get('system'), str) and 0 < len(call['system'].encode()) <= 3600
                and isinstance(call.get('prompt'), str) and 0 < len(call['prompt'].encode()) <= 3600
                and type(call.get('max_tokens')) is int and 1 <= call['max_tokens'] <= 150
                and isinstance(call.get('response'), str) and 0 < len(call['response'].encode()) <= 3000
                and call.get('response_sha256') == digest(call['response'].encode())
                and finite_number(call.get('seconds')), 'Call transcript/hash/timing missing or invalid')
    require(finite_number(report.get('adapter_wall_seconds_including_pacing'))
            and abs(report['adapter_wall_seconds_including_pacing']-sum(c['seconds'] for c in calls)) <= .002,
            'Paired adapter timing mismatch')
    prepared = []; used = []; scores = {'line': 0, 'statement': 0}
    for row, (spec, arm) in zip(rows, planned):
        require(row.get('id') == spec['id'] and row.get('arm') == arm
                and row.get('source_sha256') == spec['sha256'][spec['file']]
                and row.get('tests_sha256') == spec['sha256']['tests/test_regression.py'],
                'Counterbalanced order or source/test provenance mismatch')
        success = row.get('model_generated_success')
        require(type(success) is bool and row.get('status') == ('candidate_passed' if success else 'failed'),
                'Blocked or inconsistent paired arm state')
        numbers = row.get('call_numbers')
        require(isinstance(numbers, list) and len(numbers) == 1
                and all(type(n) is int and 1 <= n <= len(calls) for n in numbers),
                'One attempted generation per arm required')
        used.extend(numbers)
        worker = row.get('worker')
        require(isinstance(worker, dict) and worker.get('baseline') == baselines[spec['id']]
                and worker.get('controlled_synthetic_fixture') is True
                and worker.get('code_executed_in_trusted_fixture_only') is True
                and worker.get('verified_payout') is False and worker.get('submitted') is False
                and worker.get('paid_model_calls') == 0 and not worker.get('error'),
                'Worker baseline/boundary evidence incomplete')
        attempts = worker.get('attempts')
        require(isinstance(attempts, list) and len(attempts) == 1 and isinstance(attempts[0], dict)
                and attempts[0].get('number') == 1
                and attempts[0].get('error') not in ('model_or_runner_unavailable', 'independent_verification_failed'),
                'Worker attempt blocked or incomplete')
        attempt = attempts[0]
        require((worker.get('status') == 'review_ready') == success
                and (attempt.get('status') == 'passed') == success,
                'Worker success contradicts arm status')
        call = calls[numbers[0]-1]
        require(call.get('id') == spec['id'] and call.get('arm') == arm, 'Model call attributed to wrong paired arm')
        validate_prompt(call, spec, arm, baselines[spec['id']])
        check = attempt.get('test')
        if check is not None:
            require(isinstance(check, dict) and check.get('timeout') is False
                    and check.get('exit_code') in (0, 1) and isinstance(check.get('output'), str)
                    and len(check['output'].encode()) <= 6000, 'Worker test is incomplete or unsafe')
        if success:
            require(test_passed(check), 'Successful arm lacks passing tests')
            if arm == 'statement':
                require(test_passed(worker.get('independent_verification')),
                        'Statement worker lacks its independent regression')
            try:
                candidate = stage_response(spec, arm, call['response'])
            except (DraftRejected, OSError, ValueError, TypeError, KeyError, SyntaxError):
                raise EvaluationRejected('Success failed independent source validation') from None
            require(worker.get('patch') == [{'path': spec['file'], 'diff': candidate['diff']}]
                    and attempt.get('diff') == candidate['diff'], 'Claimed success patch differs from raw proposal')
            prepared.append((spec, arm, call['response'], candidate)); scores[arm] += 1
        else:
            require(not test_passed(check) and worker.get('patch') is None,
                    'Failed arm has contradictory passing test or patch')
    require(used == list(range(1, count+1)), 'Calls are missing, duplicated or out of evaluation order')
    require(report.get('scores') == scores, 'Paired score does not reconcile')
    return report, prepared


def replay(raw, *, expected_revision):
    if any(os.environ.get(name) for name in ('GROQ_API_KEY', 'OPENAI_API_KEY', 'STRIPE_SECRET_KEY', 'GITHUB_TOKEN', 'GH_TOKEN')):
        raise EvaluationRejected('Independent replay must not receive inference/payment/publication credentials')
    report, prepared = validate_report(raw, expected_revision=expected_revision)
    result = {'schema': 1, 'kind': 'owned_maintenance_independent_replay',
              'source_report_sha256': digest(raw), 'revision': expected_revision,
              'core_revision': CORE_REVISION, 'catalog_revision': CATALOG_REVISION,
              'model_calls': 0, 'inference_performed': False, 'commercial_bounty': False,
              'external_submission': False, 'untrusted_execution_certified': False,
              'status': 'blocked', 'reported_scores': report['scores'],
              'scores': {'line': 0, 'statement': 0}, 'cases': []}
    try:
        with tempfile.TemporaryDirectory(prefix='bf-phase6-replay-probe-') as directory:
            root = Path(directory)/'baseline'; shutil.copytree(HISTORICAL_TASKS/'459', root)
            (root/HISTORICAL_MARKER).write_text('459')
            proof = verify_runtime_boundary(root); validate_proof(proof)
            result['sandbox_preflight'] = proof
    except (CuratedSandboxUnavailable, EvaluationRejected, OSError):
        result['failure_reason'] = 'independent_docker_admission_failed'
        return result
    # Every identity/accounting/proposal has been validated before any task executes.
    for spec, arm, response, candidate in prepared:
        item = {'id': spec['id'], 'arm': arm, 'source_sha256': spec['sha256'][spec['file']],
                'tests_sha256': spec['sha256']['tests/test_regression.py'],
                'candidate_sha256': digest(candidate['content'].encode()),
                'patch_sha256': digest(candidate['diff'].encode()), 'verified': False}
        result['cases'].append(item)
        try:
            with tempfile.TemporaryDirectory(prefix='bf-phase6-replay-case-') as directory:
                root = Path(directory)/'candidate'; shutil.copytree(TASKS/spec['id'], root)
                (root/FIXTURE_MARKER).write_text(spec['id'])
                (root/spec['file']).write_text(candidate['content'])
                admit(root, spec, arm=arm, response=response)
                check = _execute(root, None, 12)
            item['test'] = check
        except (CuratedSandboxUnavailable, EvaluationRejected, OSError):
            result['failure_reason'] = 'independent_execution_unavailable'
            return result
        if check.get('timeout') or check.get('error'):
            result['failure_reason'] = 'independent_execution_unavailable'
            return result
        passed = (check.get('passed') is True and check.get('returncode') == 0
                  and isinstance(check.get('output'), str) and len(check['output'].encode()) <= 6000
                  and re.search(r'Ran [1-9][0-9]* tests?', check['output']) is not None
                  and check['output'].rstrip().endswith('OK'))
        if not passed:
            result.update(status='replay_failed', failure_reason='independent_regression_failed')
            return result
        item['verified'] = True; result['scores'][arm] += 1
    require(result['scores'] == result['reported_scores'], 'Independent paired totals mismatch')
    result['status'] = 'completed'
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raw = b''
    try:
        with args.report.open('rb') as source:
            raw = source.read(MAX_REPORT_BYTES+1)
        result = replay(raw, expected_revision=args.revision)
    except (EvaluationRejected, OSError, ValueError, KeyError, TypeError):
        result = {'schema': 1, 'kind': 'owned_maintenance_independent_replay', 'status': 'rejected',
                  'failure_reason': 'input_or_proposal_validation_failed', 'model_calls': 0,
                  'inference_performed': False, 'commercial_bounty': False,
                  'external_submission': False, 'untrusted_execution_certified': False,
                  'source_report_sha256': digest(raw) if 0 < len(raw) <= MAX_REPORT_BYTES else None,
                  'scores': {'line': 0, 'statement': 0}, 'cases': []}
    write_report(args.output, result)
    print('Independent paired replay:', result['status'], 'scores', result['scores'], 'model calls: 0')
    return 0 if result['status'] == 'completed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
