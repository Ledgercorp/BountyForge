"""Bounded, review-only repair of *trusted synthetic fixtures*.

This is not a general-purpose hostile-repository sandbox. A disposable copy,
subprocess budgets and a scrubbed environment do not provide network isolation.
Third-party code execution is intentionally disabled until a stronger sandbox
has been independently accepted.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import resource
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from bountyforge.coder import propose_draft
from bountyforge.minimal import propose_minimal
from bountyforge.lineedit import propose_lines
from bountyforge.line_scope import infer_editable_lines
from bountyforge.drafts import DraftRejected, _verify_existing, safe_path

MAX_ATTEMPTS = 2
MAX_SECONDS = 25
MAX_OUTPUT = 12000
FIXTURE_MARKER = '.bountyforge-controlled-fixture'


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000, 1_000_000))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


def _run_tests(root: Path, timeout: int = MAX_SECONDS) -> dict:
    """Fixed command, no shell, scrubbed environment, subprocess group timeout."""
    command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v']
    env = {'PATH': os.defpath, 'HOME': str(root), 'PYTHONPATH': str(root),
           'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C.UTF-8'}
    started = time.monotonic()
    try:
        with tempfile.TemporaryFile() as log:
            child = subprocess.Popen(command, cwd=root, env=env, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True,
                                     preexec_fn=_limits)
            try:
                child.wait(timeout=timeout)
                expired = False
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                expired = True
            code = child.returncode
            log.seek(0)
            output = log.read(MAX_OUTPUT)
    except OSError as exc:
        return {'passed': False, 'exit_code': None, 'timeout': False,
                'seconds': round(time.monotonic()-started, 3), 'output': 'Runner unavailable: ' + type(exc).__name__}
    return {'passed': code == 0 and not expired and bool(re.search(rb'Ran [1-9][0-9]* tests?',output)) and output.rstrip().endswith(b'OK'), 'exit_code': code,
            'timeout': expired, 'seconds': round(time.monotonic()-started, 3),
            'output': output[:MAX_OUTPUT].decode('utf-8', errors='replace')}


def _contained_copy(source: Path, target: Path) -> None:
    if not (source / FIXTURE_MARKER).is_file() or (source / FIXTURE_MARKER).is_symlink():
        raise DraftRejected('Only explicitly marked controlled synthetic fixtures may execute')
    if source.is_symlink() or not source.is_dir():
        raise DraftRejected('Invalid source fixture')
    count = 0
    for path in source.rglob('*'):
        if path.is_symlink():
            raise DraftRejected('Fixture symlinks not permitted')
        if path.is_file():
            count += 1
            if count > 20 or path.stat().st_size > 100_000:
                raise DraftRejected('Fixture size or file count exceeds budget')
    shutil.copytree(source, target, symlinks=False)


def _fixture_hash(root: Path) -> str:
    hasher = hashlib.sha256()
    for p in sorted(root.rglob('*')):
        if p.is_file():
            hasher.update(p.relative_to(root).as_posix().encode())
            hasher.update(p.read_bytes())
    return hasher.hexdigest()


def repair_fixture(issue: dict, fixture_root: Path, approved_paths: list[str], model,
                   *, max_attempts: int = MAX_ATTEMPTS, strategy: str = 'full',
                   editable_lines: dict[str, list[int]] | None = None,
                   test_runner=None) -> dict:
    """Prepare patch evidence, never commit, push, submit or run outside fixture.

    First test must reproduce a failure. Every model attempt is validated,
    then applied solely in its own disposable copy of a fixture. A test-passing
    proposal is reviewable, but not necessarily a legitimate real-world fix.
    """
    if strategy not in {'full', 'minimal', 'line', 'auto_line', 'statement'}:
        raise ValueError('Only known patch strategies permitted')
    if not 1 <= max_attempts <= 2:
        raise ValueError('max_attempts must be 1 or 2')
    if not isinstance(issue, dict) or issue.get('verification') != 'unverified_candidate':
        raise DraftRejected('Unknown issue state')
    allowed = [safe_path(x) for x in approved_paths]
    if not allowed or len(set(allowed)) != len(allowed) or len(allowed) > 3:
        raise DraftRejected('Invalid allowlist')
    if strategy in {'line', 'auto_line', 'statement'}:
        if len(allowed) != 1 or (strategy in {'line','statement'} and (not isinstance(editable_lines, dict) or set(editable_lines) != set(allowed))):
            raise DraftRejected('Line strategy requires one trusted path; explicit lines required for manual line mode')
    start = time.monotonic()
    runner = test_runner or _run_tests
    with tempfile.TemporaryDirectory(prefix='bountyforge-worker-') as temp:
        root = Path(temp) / 'base'
        _contained_copy(Path(fixture_root), root)
        for item in allowed:
            _verify_existing(root, item)
        fingerprint = _fixture_hash(root)
        initial = runner(root)
        report = {'status': 'failed', 'scenario': str(issue.get('title', ''))[:140],
                  'controlled_synthetic_fixture': True, 'source_sha256': fingerprint,
                  'baseline': initial, 'attempts': [], 'verified_payout': False,
                  'submitted': False, 'code_executed_in_trusted_fixture_only': True,
                  'paid_model_calls': 0, 'patch': None, 'model_calls': 0}
        if initial['passed']:
            report['error'] = 'baseline_does_not_reproduce'; return report
        if initial['timeout']:
            report['error'] = 'baseline_timeout'; return report
        if strategy == 'auto_line':
            try:
                editable_lines = {allowed[0]: infer_editable_lines(root, allowed[0], initial['output'])}
            except (DraftRejected, SyntaxError, ValueError, OSError) as exc:
                report['error'] = 'automatic_scope_rejected'
                report['scope_reason'] = type(exc).__name__
                return report
            report['inferred_editable_lines'] = editable_lines[allowed[0]]
        if (initial.get('exit_code') != 1 or 'FAIL:' not in initial.get('output','')
                or 'FAILED (failures=' not in initial['output'] or 'errors=' in initial['output']):
            report['error'] = 'baseline_not_assertion_failure'; return report
        feedback = None
        previous_response = ''
        seen_candidates = set()
        for number in range(1, max_attempts + 1):
            attempt = {'number': number, 'status': 'failed'}
            work = Path(temp) / ('attempt' + str(number))
            shutil.copytree(root, work)
            try:
                adapted = dict(issue)
                if strategy == 'statement':
                    adapted.update(baseline_failure=initial['output'],
                                   test_failure_excerpt=feedback or initial['output'],
                                   prior_error=feedback or '', previous_proposal=previous_response)
                if feedback:
                    adapted['description_excerpt'] = (
                        str(issue.get('description_excerpt', ''))[:900] +
                        '\nPrevious attempt failed: ' + feedback[:420]
                    )
                if strategy in {'minimal', 'line', 'auto_line'}:
                    adapted['test_failure_excerpt'] = initial['output'][-700:]
                    adapted['prior_error'] = feedback or ''
                if strategy == 'statement':
                    from bountyforge.statements import propose_statements
                    attempt['calls'] = []
                    class CapturedModel:
                        def complete_line(self, system, prompt, max_tokens):
                            report['model_calls'] += 1
                            call = {'system':system,'prompt':prompt,'max_tokens':max_tokens,'response':None}
                            attempt['calls'].append(call)
                            generated = time.monotonic()
                            try:
                                model.last_call = None
                                response = model.complete_line(system,prompt,max_tokens)
                                call['response'] = response
                                call['response_sha256'] = hashlib.sha256(response.encode()).hexdigest()
                                return response
                            except Exception as exc:
                                call['error'] = type(exc).__name__
                                raise
                            finally:
                                call['seconds'] = round(time.monotonic()-generated,3)
                                call['metadata'] = getattr(model,'last_call',None)
                    try:
                        result = propose_statements(adapted, work, allowed[0], editable_lines[allowed[0]], CapturedModel())
                    finally:
                        if attempt['calls']:
                            previous_response = attempt['calls'][-1].get('response') or ''
                    candidate = result['semantic_sha256']
                    if candidate in seen_candidates:
                        attempt['error'] = 'repeated_ineffective_candidate'
                        feedback = 'Repeated semantically identical failed candidate; do not execute again'
                        report['attempts'].append(attempt)
                        continue
                    seen_candidates.add(candidate)
                elif strategy in {'line', 'auto_line'}:
                    report['model_calls'] += 1
                    result = propose_lines(adapted, work, allowed[0], editable_lines[allowed[0]], model=model)
                elif strategy == 'minimal':
                    report['model_calls'] += 1
                    result = propose_minimal(adapted, work, allowed, model=model)
                else:
                    report['model_calls'] += 1
                    result = propose_draft(adapted, work, allowed, model=model)
                # Every path is individually checked by stage_draft; never
                # execute a model-provided shell command or alter test files.
                for entry in result['files']:
                    path = entry['path']
                    if path.startswith('tests/') or path == FIXTURE_MARKER:
                        raise DraftRejected('Test files may not be patched')
                    file_path = work / path
                    _verify_existing(work, path)
                    file_path.write_text(entry['content'], encoding='utf-8')
                    if path.endswith('.py'):
                        ast.parse(entry['content'], filename=path)
                verified = runner(work)
                attempt['test'] = verified
                attempt['diff'] = '\n'.join(entry['diff'] for entry in result['files'])[:12000]
                if verified['passed']:
                    if strategy == 'statement':
                        independent_root = Path(temp) / 'independent'
                        shutil.copytree(root, independent_root)
                        for entry in result['files']:
                            (independent_root/entry['path']).write_text(entry['content'],encoding='utf-8')
                        independent = runner(independent_root)
                        report['independent_verification'] = independent
                        if not independent['passed']:
                            attempt['error'] = 'independent_verification_failed'
                            report['error'] = 'independent_verification_failed'
                            report['attempts'].append(attempt)
                            break
                    attempt['status'] = 'passed'
                    report['status'] = 'review_ready'
                    report['patch'] = [{'path': entry['path'], 'diff': entry['diff']}
                                       for entry in result['files']]
                    report['attempts'].append(attempt)
                    break
                attempt['error'] = 'test_failure_or_timeout'
                feedback = verified['output'][-420:]
            except (RuntimeError, OSError) as exc:
                attempt['error'] = 'model_or_runner_unavailable'
                report['attempts'].append(attempt)
                break  # Do not overlap inference after an endpoint timeout.
            except (DraftRejected, ValueError) as exc:
                attempt['error'] = type(exc).__name__
                feedback = str(exc)[:450] if strategy == 'statement' else type(exc).__name__
                if strategy == 'statement': attempt['diagnostic'] = feedback
            report['attempts'].append(attempt)
        report['elapsed_seconds'] = round(time.monotonic()-start, 3)
        return report
