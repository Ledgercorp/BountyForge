"""Explicit, bounded local-Qwen evaluation on the frozen owned Phase 8 set.

This adapter is deliberately separate from phase8_evaluation: the latter stays
provider-free and remains the preparation/replay authority. This module only
admits the pinned public GitHub runner, the pinned local model endpoint, the
frozen 20-case selection and a fresh Docker proof. It cannot fall back remotely.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from bountyforge.model import LocalModel
from bountyforge.phase8_evaluation import (
    Catalog, CONTROLS, EvaluationRejected, ROOT, issue_for, materialize, observe,
    preflight, replay, require_credential_free_host, validate_proof,
)
from bountyforge.repair_session import repair_owned

SELECTION = 'benchmarks/phase8/supplemental_tasks/selection.json'
SELECTION_SHA256 = '55e7de2b2c59eaaea75a494315df5b95cea5eeabcaeb835309a517f43abb891e'
MAX_ATTEMPTS = 2
MAX_TOTAL_CALLS = 40
RESUME_REPORT = 'evidence/phase11/partial_qwen_39935203508.json'
RESUME_REPORT_SHA256 = 'b2621e12fb2118534ba7b67b9cdc1dcbca32594d0b7fd13f8bedc4f86186433c'
PREVIOUS_RUN_ID = 39935203508
PREVIOUS_COMMIT = 'c328532d597e2af0dc5464d3d757a602f24f76bd'
EXPOSED_CASES = ('stock_admission', 'booking_intersection', 'literal_tail',
                 'line_termination', 'duration_label', 'shipping_cartons',
                 'block_indentation', 'running_measurements', 'endpoint_authority',
                 'archive_classification', 'markup_text', 'csv_field_encoding',
                 'cyclic_sequence', 'configuration_switch', 'terminal_run_summary',
                 'rectangular_columns', 'rooted_segments', 'utf8_prefix_budget',
                 'wildcard_empty_prefix')
MODEL_SHA256 = 'cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046'
RUNTIME_SHA256 = '152e33221c9c9d37816a8ee9943f8d87339199197c80cb692559c9756b2027d8'


def require_hosted_admission() -> None:
    """Prevent accidental local/other-repository use of the live evaluator."""
    event = os.environ.get('GITHUB_EVENT_NAME')
    explicit_gate = (event == 'workflow_dispatch'
                     or (event == 'push' and os.environ.get('BOUNTYFORGE_QWEN_PUSH_ACK') == 'true'))
    if (not explicit_gate or os.environ.get('GITHUB_ACTIONS') != 'true'
            or os.environ.get('GITHUB_REPOSITORY') != 'Ledgercorp/BountyForge'
            or os.environ.get('GITHUB_REF') != 'refs/heads/engineering/revenue-linux-scout-20261021'
            or os.environ.get('BOUNTYFORGE_QWEN_COST_ACK') != 'true'
            or os.environ.get('RUNNER_OS') != 'Linux'
            or os.environ.get('RUNNER_ARCH') != 'X64'):
        raise EvaluationRejected('Live Qwen evaluation is admitted only on its manual public Linux workflow')


def _category(session: dict, replay_result: dict | None) -> str:
    if replay_result is not None:
        return 'independently_replayed_success' if replay_result.get('status') == 'replay_passed' else 'independent_replay_rejected'
    worker = session.get('worker', {})
    reason = worker.get('error')
    attempts = worker.get('attempts', [])
    errors = [row.get('error') for row in attempts if isinstance(row, dict)]
    if session.get('reason') == 'context_rejected_before_inference' or reason in ('automatic_scope_rejected', 'baseline_not_assertion_failure'):
        return 'deterministic_admission_or_context_failure'
    diagnostics = [row.get('diagnostic') for row in attempts if isinstance(row, dict)]
    if any('Semantically ineffective proposal' in str(value) for value in diagnostics):
        return 'ineffective_model_proposal'
    if any(row.get('source_rejection') for row in session.get('calls', []) if isinstance(row, dict)):
        return 'source_or_patch_validation_rejection'
    if any(error in ('DraftRejected', 'ValueError') for error in errors):
        return 'other_patch_validation_rejection'
    if 'repeated_ineffective_candidate' in errors:
        return 'repeated_ineffective_proposal'
    if 'test_failure_or_timeout' in errors:
        return 'targeted_test_failure'
    if any(error in ('model_or_runner_unavailable', 'RuntimeError') for error in errors):
        return 'inference_or_test_runner_failure'
    if session.get('model_calls', 0) == 0:
        return 'no_inference_due_to_admission'
    return 'no_independently_verified_repair'


def load_resume_report(catalog: Catalog, tasks: list[dict]) -> dict:
    """Load the immutable first segment; never repeat its six exposed cases."""
    path = ROOT / RESUME_REPORT
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise EvaluationRejected('Pinned prior evaluation segment is unavailable')
    raw = path.read_bytes()
    if len(raw) > 3_000_000 or hashlib.sha256(raw).hexdigest() != RESUME_REPORT_SHA256:
        raise EvaluationRejected('Prior evaluation segment differs from its trusted digest')
    prior = json.loads(raw)
    expected_ids = [task['id'] for task in tasks]
    if (prior.get('evaluation') != 'phase8_frozen20_live_local_qwen'
            or prior.get('status') != 'blocked' or prior.get('accuracy') is not None
            or prior.get('selected_cases') != expected_ids
            or prior.get('attempted_cases') != len(EXPOSED_CASES)
            or [row.get('case_id') for row in prior.get('cases', [])] != list(EXPOSED_CASES)
            or prior.get('inference_calls') != 35
            or sum(row.get('model_calls', 0) for row in prior.get('cases', [])) != 35
            or prior.get('verified_successes') != 0
            or prior.get('independently_replayed_successes') != 0
            or prior.get('customer_execution_authorized') is not False
            or prior.get('delivery_authorized') is not False
            or prior.get('paid_fallback') is not False
            or prior.get('model', {}).get('sha256') != MODEL_SHA256
            or prior.get('model', {}).get('runtime_archive_sha256') != RUNTIME_SHA256
            or prior.get('execution', {}).get('selection_sha256') != SELECTION_SHA256):
        raise EvaluationRejected('Prior evaluation segment does not match the frozen continuation contract')
    validate_proof(prior.get('preflight'))
    by_id = {task['id']: task for task in tasks}
    for row in prior['cases']:
        spec = by_id[row['case_id']]
        if (row.get('source_sha256') != spec['sha256']['subject.py']
                or row.get('tests_sha256') != spec['sha256']['tests/test_regression.py']
                or row.get('model_calls') not in (1, 2)
                or not isinstance(row.get('session'), dict)):
            raise EvaluationRejected('Prior case provenance or bounded transcript failed')
        session = row['session']
        if (session.get('source_sha256') != spec['sha256']['subject.py']
                or session.get('tests_sha256') != spec['sha256']['tests/test_regression.py']
                or session.get('model_calls') != row['model_calls']
                or any(session.get(flag) is not False for flag in (
                    'customer_execution_authorized', 'delivery_authorized', 'paid_fallback'))
                or len(session.get('calls', [])) != row['model_calls']):
            raise EvaluationRejected('Prior session is not bound to its frozen case')
        # Re-derive taxonomy from the immutable raw transcript instead of
        # carrying forward the first adapter's overly broad rejection label.
        row['failure_category'] = _category(session, row.get('independent_replay'))
        row['status'] = 'failed_or_unverified'
    segments = prior.get('run_segments')
    if (not isinstance(segments, list) or len(segments) != 3
            or [str(segment.get('run_id')) for segment in segments]
               != ['39896337388', '39934425118', str(PREVIOUS_RUN_ID)]
            or [case_id for segment in segments for case_id in segment.get('cases', [])]
               != list(EXPOSED_CASES)
            or segments[0].get('commit') != '777004ca60f0b3252c97112e851f22c89944f273'
            or segments[0].get('calls') != 11
            or segments[0].get('report_sha256') != 'b3bd0415afbc3a910e3de797e819c7f5c6a7b2cc190894b823b25811007d47c7'
            or segments[1].get('commit') != '4df5b182cce04d8fb68b5a3bcd3b4f0e58d70f13'
            or segments[1].get('calls') != 3
            or segments[2].get('commit') != PREVIOUS_COMMIT
            or segments[2].get('calls') != 21):
        raise EvaluationRejected('Prior evaluation segments do not match the pinned continuation history')
    history = prior.get('preflight_history')
    if (not isinstance(history, list) or len(history) != 3
            or [str(row.get('run_id')) for row in history]
               != ['39896337388', '39934425118', str(PREVIOUS_RUN_ID)]):
        raise EvaluationRejected('Prior Docker admission history is incomplete')
    return prior


def _atomic_write(path: Path, report: dict) -> None:
    raw = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False).encode() + b'\n'
    # Full successful call records are retained for independent replay. This is
    # bounded well below the workflow's short-lived artifact allowance.
    if len(raw) > 3_000_000:
        raise EvaluationRejected('Evaluation evidence exceeds 3 MB bound')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(raw)
    temporary.replace(path)


def _summarize_cases(report: dict) -> None:
    categories = {}
    counters = {'patch_proposals_returned': 0, 'source_validation_rejections': 0,
                'ineffective_proposals_rejected': 0, 'other_patch_validation_rejections': 0,
                'targeted_test_failures': 0, 'repeated_ineffective_proposals': 0,
                'inference_or_runner_errors': 0}
    for row in report['cases']:
        category = row.get('failure_category', 'incomplete')
        categories[category] = categories.get(category, 0) + 1
        session = row.get('session', {})
        calls = session.get('calls', []) if isinstance(session, dict) else []
        worker = session.get('worker', {}) if isinstance(session, dict) else {}
        attempts = worker.get('attempts', []) if isinstance(worker, dict) else []
        counters['patch_proposals_returned'] += sum(
            1 for attempt in attempts if isinstance(attempt, dict) and attempt.get('diff'))
        counters['source_validation_rejections'] += sum(
            1 for call in calls if isinstance(call, dict) and call.get('source_rejection'))
        counters['ineffective_proposals_rejected'] += sum(
            1 for attempt in attempts if isinstance(attempt, dict)
            and 'Semantically ineffective proposal' in str(attempt.get('diagnostic', '')))
        counters['other_patch_validation_rejections'] += sum(
            1 for attempt in attempts if isinstance(attempt, dict)
            and attempt.get('error') in ('DraftRejected', 'ValueError', 'SyntaxError')
            and 'Semantically ineffective proposal' not in str(attempt.get('diagnostic', ''))
            and not any(call.get('source_rejection') for call in calls if isinstance(call, dict)))
        counters['targeted_test_failures'] += sum(
            1 for attempt in attempts if isinstance(attempt, dict)
            and (attempt.get('error') == 'test_failure_or_timeout'
                 or (isinstance(attempt.get('test'), dict) and attempt['test'].get('passed') is False)))
        counters['repeated_ineffective_proposals'] += sum(
            1 for attempt in attempts if isinstance(attempt, dict)
            and attempt.get('error') == 'repeated_ineffective_candidate')
        counters['inference_or_runner_errors'] += sum(
            1 for attempt in attempts if isinstance(attempt, dict)
            and attempt.get('error') == 'model_or_runner_unavailable')
    report['failure_category_counts'] = categories
    report['proposal_and_verification_counts'] = counters


def evaluate(*, output: str | Path) -> dict:
    """Continue the pinned partial evaluation without repeating exposed cases."""
    started = time.monotonic()
    report = {
        'schema': 1, 'evaluation': 'phase8_frozen20_live_local_qwen',
        'status': 'blocked', 'accuracy': None, 'attempted_cases': 0,
        'verified_successes': 0, 'independently_replayed_successes': 0,
        'inference_calls': 0, 'max_inference_calls': MAX_TOTAL_CALLS,
        'inference_seconds': 0.0, 'prompt_tokens': None, 'completion_tokens': None,
        'local_inference_cost_usd': 0, 'additional_infrastructure_cost_usd': 0,
        'cost_basis': 'No API calls; public standard GitHub-hosted runner and bounded existing cache/artifact allowances.',
        'customer_execution_authorized': False, 'delivery_authorized': False,
        'paid_fallback': False, 'external_submissions': 0,
        'model': {'id': 'Qwen2.5-Coder-1.5B-Instruct Q4_K_M', 'sha256': MODEL_SHA256,
                  'runtime': 'llama.cpp b11750', 'runtime_archive_sha256': RUNTIME_SHA256,
                  'endpoint': '127.0.0.1:8080', 'remote_fallback': False},
        'execution': {'runner': 'GitHub-hosted ubuntu-24.04 standard X64',
                      'tests': 'fresh digest-pinned Docker, network disabled',
                      'selection_file': SELECTION, 'selection_sha256': SELECTION_SHA256},
        'cases': [],
    }
    path = Path(output)
    try:
        require_hosted_admission()
        require_credential_free_host()
        catalog = Catalog(SELECTION, SELECTION_SHA256)
        tasks = catalog.tasks()
        if len(tasks) != 20:
            raise EvaluationRejected('Frozen selection must contain exactly twenty cases')
        report = load_resume_report(catalog, tasks)
        report['resumed_from_report_sha256'] = RESUME_REPORT_SHA256
        report['resumed_case_ids'] = list(EXPOSED_CASES)
        report['runner_run_id'] = os.environ.get('GITHUB_RUN_ID', 'unit-test')
        report['runner_commit'] = os.environ.get('GITHUB_SHA', 'unit-test')
        proof = preflight()
        report['preflight'] = proof
        report['preflight_history'].append({'run_id': report['runner_run_id'], 'proof': proof})
        report['run_segments'].append({'run_id': report['runner_run_id'],
                                       'commit': report['runner_commit'],
                                       'cases': [], 'calls': 0})
        report['status'] = 'running'
        _atomic_write(path, report)
        backend = LocalModel(timeout_seconds=45)
        for spec in tasks:
            if spec['id'] in report['resumed_case_ids']:
                continue
            row = {'case_id': spec['id'], 'status': 'attempting',
                   'source_sha256': spec['sha256']['subject.py'],
                   'tests_sha256': spec['sha256']['tests/test_regression.py'],
                   'model_calls': 0, 'failure_category': None}
            report['cases'].append(row)
            _atomic_write(path, report)
            with tempfile.TemporaryDirectory(prefix='bf-phase8-qwen-') as directory:
                root = Path(directory) / 'original'
                materialize(catalog, spec, root)
                session = repair_owned(
                    issue_for(spec), root, 'subject.py', backend,
                    expected_hashes=spec['sha256'],
                    test_runner=lambda work, spec=spec: observe(catalog, spec, Path(work)),
                    max_attempts=MAX_ATTEMPTS,
                )
            row['model_calls'] = session.get('model_calls', 0)
            report['inference_calls'] += row['model_calls']
            report['run_segments'][-1]['cases'].append(spec['id'])
            report['run_segments'][-1]['calls'] += row['model_calls']
            report['inference_seconds'] = round(report['inference_seconds'] + sum(
                float(call.get('seconds', 0)) for call in session.get('calls', [])
                if isinstance(call, dict)), 3)
            metadata = [call.get('metadata') for call in session.get('calls', [])
                        if isinstance(call, dict) and isinstance(call.get('metadata'), dict)]
            if metadata and all(isinstance(item.get('prompt_tokens'), int) for item in metadata):
                report['prompt_tokens'] = (report['prompt_tokens'] or 0) + sum(item['prompt_tokens'] for item in metadata)
            if metadata and all(isinstance(item.get('completion_tokens'), int) for item in metadata):
                report['completion_tokens'] = (report['completion_tokens'] or 0) + sum(item['completion_tokens'] for item in metadata)
            row['session_status'] = session.get('status')
            row['session_reason'] = session.get('reason')
            replay_result = None
            if session.get('status') == 'review_ready' and session.get('patch'):
                report['verified_successes'] += 1
                replay_result = replay({'case_id': spec['id'], 'session': session},
                                       selection_file=SELECTION,
                                       selection_sha256=SELECTION_SHA256)
                row['independent_replay'] = replay_result
                if replay_result.get('status') == 'replay_passed':
                    report['independently_replayed_successes'] += 1
            row['failure_category'] = _category(session, replay_result)
            row['status'] = 'independently_replayed_success' if row['failure_category'] == 'independently_replayed_success' else 'failed_or_unverified'
            row['session'] = session
            report['attempted_cases'] += 1
            if report['inference_calls'] > MAX_TOTAL_CALLS:
                raise EvaluationRejected('Global inference call budget exceeded')
            attempt_errors = [attempt.get('error') for attempt in session.get('worker', {}).get('attempts', [])
                              if isinstance(attempt, dict)]
            if 'model_or_runner_unavailable' in attempt_errors:
                row['status'] = 'blocked'
                report['status'] = 'blocked'
                report['blocking_reason'] = 'inference_or_isolated_test_runner_unavailable; remaining cases not dispatched'
                _atomic_write(path, report)
                break
            _atomic_write(path, report)
        if report['status'] != 'blocked':
            report['accuracy'] = {
                'verified_repairs': report['independently_replayed_successes'],
                'attempted': report['attempted_cases'],
            }
            report['status'] = 'completed' if report['attempted_cases'] == 20 else 'incomplete'
    except KeyboardInterrupt:
        report['status'] = 'interrupted'
        report['accuracy'] = None
        raise
    except Exception as exc:
        report['status'] = 'blocked'
        report['accuracy'] = None
        report['blocking_reason'] = type(exc).__name__ + ': ' + str(exc)[:240]
    finally:
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        _summarize_cases(report)
        report['usage'] = {'model_requests': report['inference_calls'],
                           'max_requests': MAX_TOTAL_CALLS,
                           'calls_per_case_max': MAX_ATTEMPTS,
                           'prompt_tokens': report['prompt_tokens'],
                           'completion_tokens': report['completion_tokens']}
        _atomic_write(path, report)
    return report
