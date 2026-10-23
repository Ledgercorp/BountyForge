"""Independent evidence gate for completed, owned-only Groq v5 experiments.

A complete failed repair experiment is valid evidence. Blocked execution,
transport failures, missing baselines, and inconsistent accounting are not.
This validator makes no claim about independently verified provider billing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from benchmarks.phase5.development_runner import SUITES
from bountyforge.curated_docker import IMAGE
from bountyforge.curated_tasks import editable_scope
from bountyforge.groq_adapter import MODEL_ID


class CanaryRejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CanaryRejected(message)


def validate_owned_canary(report, *, suite, expected_revision):
    require(isinstance(report, dict), 'Canary report must be an object')
    require(suite in SUITES, 'Unknown owned suite')
    require(isinstance(expected_revision, str) and re.fullmatch(r'[0-9a-f]{40}', expected_revision),
            'Expected source revision must be an exact commit SHA')
    require(report.get('revision') == expected_revision, 'Canary source revision mismatch')
    require(report.get('benchmark') == 'owned_phase5_development', 'Wrong benchmark')
    require(report.get('suite') == suite and report.get('protocol') == 'ast_contract_v5',
            'Canary suite or protocol mismatch')
    require(report.get('image') == IMAGE, 'Unapproved Docker image')
    for field in ('commercial_bounty', 'historical_evaluation', 'paid_inference', 'external_submission'):
        require(report.get(field) is False, 'Canary boundary flag missing or invalid: ' + field)
    require(not report.get('blocked'), 'Canary sandbox admission was blocked')
    preflight = report.get('sandbox_preflight')
    controls = ('network_denied', 'loopback_inference_unreachable', 'source_writes_denied',
                'root_writes_denied', 'secrets_absent', 'uid_unprivileged', 'capabilities_empty',
                'no_new_privileges', 'seccomp_active', 'memory_limit_enforced', 'swap_disabled',
                'cpu_quota_verified', 'pid_limit_verified', 'tmpfs_bounded_noexec',
                'wall_clock_enforced', 'cleanup_verified', 'output_bounded',
                'docker_socket_absent', 'pid_pressure_enforced', 'cpu_pressure_enforced')
    require(isinstance(preflight, dict) and all(preflight.get(name) is True for name in controls),
            'Independent Docker controls incomplete')
    require(preflight.get('image_digest') == IMAGE.split('@')[1]
            and preflight.get('untrusted_execution_certified') is False,
            'Sandbox provenance or scope mismatch')
    require(type(report.get('max_model_calls')) is int and report['max_model_calls'] == 8
            and type(report.get('max_attempts_per_task')) is int and report['max_attempts_per_task'] == 2,
            'Canary budget changed')
    count = report.get('model_calls')
    require(type(count) is int and 4 <= count <= 8, 'Canary call count out of bounds')
    backend = report.get('inference_backend')
    require(isinstance(backend, dict) and backend.get('provider') == 'groq'
            and backend.get('model') == MODEL_ID
            and type(backend.get('transport_calls')) is int
            and backend['transport_calls'] == count
            and backend.get('total_generation_tokens_per_call') == 1024
            and backend.get('minimum_interval_seconds') == 60,
            'Provider identity or transport accounting mismatch')
    manifest = SUITES[suite][1]
    expected = {task['id']: task for task in manifest['tasks']}
    tasks = report.get('tasks')
    require(isinstance(tasks, list) and len(tasks) == len(expected) == 4,
            'Canary must complete exactly four owned tasks')
    require(all(isinstance(task, dict) for task in tasks), 'Malformed owned task record')
    identities = [task.get('id') for task in tasks]
    require(all(isinstance(identity, str) for identity in identities)
            and len(set(identities)) == 4 and set(identities) == set(expected),
            'Owned task identity mismatch or duplicate')
    calls = []
    passed = 0
    for task in tasks:
        spec = expected[task['id']]
        catalog = SUITES[suite][0] / spec['id']
        require(all(hashlib.sha256((catalog / name).read_bytes()).hexdigest() == digest
                    for name, digest in spec['sha256'].items()), 'Owned catalog changed since pinning')
        original = (catalog / spec['file']).read_text()
        approved = editable_scope(original, spec['symbol'])
        require(task.get('symbol') == spec['symbol']
                and task.get('source_sha256') == spec['sha256'][spec['file']]
                and task.get('tests_sha256') == spec['sha256']['tests/test_regression.py'],
                'Owned source or test provenance mismatch')
        require(task.get('status') in ('failed', 'owned_development_passed'),
                'Owned task is blocked or has an unsupported terminal status')
        baseline = task.get('baseline')
        require(task.get('baseline_reproduced') is True and isinstance(baseline, dict)
                and baseline.get('passed') is False and type(baseline.get('returncode')) is int
                and baseline['returncode'] == 1 and baseline.get('timeout') is False
                and baseline.get('error') is None
                and isinstance(baseline.get('output'), str)
                and re.search(r'FAILED \((?:failures|errors)=[1-9]', baseline['output']) is not None,
                'Owned defect baseline was not independently reproduced')
        attempts = task.get('attempts')
        require(isinstance(attempts, list) and 1 <= len(attempts) <= 2
                and all(isinstance(attempt, dict) for attempt in attempts)
                and [attempt.get('number') for attempt in attempts] == list(range(1, len(attempts) + 1)),
                'Owned attempt sequence is incomplete')
        require(all(attempt.get('status') in ('failed', 'passed') for attempt in attempts)
                and all(attempt.get('failure_reason') != 'inference_or_sandbox_unavailable' for attempt in attempts),
                'Inference or sandbox failure cannot complete an experiment')
        successful = task.get('model_generated_success')
        require(type(successful) is bool
                and successful == (task['status'] == 'owned_development_passed')
                and successful == (attempts[-1].get('status') == 'passed')
                and all(attempt.get('status') == 'failed' for attempt in attempts[:-1]),
                'Repair success labels contradict attempt results')
        if successful:
            check = attempts[-1].get('test')
            require(isinstance(check, dict) and check.get('passed') is True
                    and type(check.get('returncode')) is int and check['returncode'] == 0
                    and check.get('timeout') is False and check.get('error') is None
                    and isinstance(check.get('output'), str)
                    and re.search(r'Ran [1-9][0-9]* tests?', check['output']) is not None
                    and check['output'].rstrip().endswith('OK'),
                    'Successful repair lacks passing isolated tests')
            passed += 1
        task_calls = task.get('calls')
        require(isinstance(task_calls, list) and 1 <= len(task_calls) <= 2,
                'Every owned task must have bounded inference attempts')
        for call in task_calls:
            require(isinstance(call, dict) and not call.get('error') and call.get('kind') == 'patch'
                    and type(call.get('round')) is int and 1 <= call['round'] <= len(attempts),
                    'Owned model call failed or has invalid kind/round')
            require(isinstance(call.get('system'), str) and 0 < len(call['system'].encode()) <= 3600
                    and isinstance(call.get('prompt'), str) and 0 < len(call['prompt'].encode()) <= 3600,
                    'Prompt transcript is absent or out of bounds')
            try:
                prompt = json.loads(call['prompt'])
            except ValueError as exc:
                raise CanaryRejected('Prompt transcript is malformed') from exc
            require(isinstance(prompt, dict) and prompt.get('approved_file') == spec['file']
                    and prompt.get('target_symbol') == spec['symbol']
                    and prompt.get('editable_lines') == approved,
                    'Prompt target exceeds the owned scope')
            metadata = call.get('metadata')
            total_limit=metadata.get('requested_max_completion_tokens') if isinstance(metadata,dict) else None
            require(isinstance(metadata, dict) and metadata.get('provider') == 'groq'
                    and metadata.get('model') == MODEL_ID and metadata.get('finish_reason') == 'stop'
                    and metadata.get('provider_model_reported') == MODEL_ID
                    and type(metadata.get('prompt_tokens')) is int and metadata['prompt_tokens'] > 0
                    and type(metadata.get('completion_tokens')) is int
                    and type(call.get('max_tokens')) is int
                    and 1 <= call['max_tokens'] <= 150
                    and type(total_limit) is int and total_limit == 1024
                    and 1 <= metadata['completion_tokens'] <= total_limit,
                    'Missing or invalid completed-model accounting')
            response = call.get('response')
            require(isinstance(response, str) and 0 < len(response.encode()) <= 3000
                    and call.get('response_sha256') == hashlib.sha256(response.encode()).hexdigest(),
                    'Response transcript is absent or tampered')
            seconds = call.get('seconds')
            require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0,
                    'Invalid inference latency')
            calls.append(call)
    require(len(calls) == count and [call.get('number') for call in calls] == list(range(1, count + 1)),
            'Model call sequence does not reconcile')
    require(type(report.get('attempted')) is int and report['attempted'] == 4
            and type(report.get('passed')) is int and report['passed'] == passed,
            'Owned task totals do not reconcile')
    seconds = report.get('inference_seconds')
    require(type(seconds) in (int, float) and math.isfinite(seconds)
            and abs(seconds - sum(call['seconds'] for call in calls)) <= 0.002,
            'Inference timing total does not reconcile')
    return {'completed_tasks': 4, 'repairs_passed': passed, 'model_calls': count,
            'commercial_bounty': False, 'billing_independently_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('--suite', choices=tuple(SUITES), required=True)
    parser.add_argument('--revision', required=True)
    arguments = parser.parse_args()
    result = validate_owned_canary(json.loads(arguments.report.read_text()),
                                   suite=arguments.suite, expected_revision=arguments.revision)
    print(json.dumps(result, sort_keys=True))
