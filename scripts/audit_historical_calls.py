"""Reconstruct call-level facts without inventing missing historical responses."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [('evidence/phase5/historical-v3.json', '39590337663'),
          ('evidence/hosted-boltons-2026-10-21.json', '39592095298')]


def audit():
    runs = []
    for filename, run_id in INPUTS:
        data = (ROOT / filename).read_bytes()
        report = json.loads(data)
        calls = []
        for task in report['tasks']:
            symbols = ['args2sh', 'args2cmd'] if task['id'] == '454' else [
                {'459': 'bytes2human', '460': 'most_common',
                 '475': 'iter_splitlines', '524': 'bytes2human'}[task['id']]]
            for attempt in task['attempts']:
                generations = {g['symbol']: g for g in attempt['generations']}
                for index, symbol in enumerate(symbols):
                    generation = generations.get(symbol)
                    # Both original harnesses call symbols in manifest order;
                    # a proposal exception stops this attempt at the next symbol.
                    rejected = generation is None
                    if rejected and index != len(generations):
                        continue
                    outcome = ('source_validation_rejection' if rejected else
                               'targeted_tests_failed' if attempt.get('test') else
                               'staged_then_sibling_rejected')
                    output = attempt.get('test', {}).get('output', '')
                    observed = attempt.get('message') if rejected else (
                        'uninitialized_local_in_traceback' if 'UnboundLocalError' in output else
                        'return_type_error_in_traceback' if 'TypeError' in output else
                        'assertion_mismatch' if 'AssertionError' in output else
                        'candidate_staged_no_test_execution')
                    calls.append({
                        'call': len(calls) + 1, 'case': task['id'], 'round': attempt['number'],
                        'symbol': symbol, 'outcome': outcome, 'observed': observed,
                        'response_sha256': generation.get('response_sha256') if generation else None,
                        'recorded_generation_seconds': generation.get('seconds') if generation else None,
                        'metadata': generation.get('model_metadata') if generation else attempt.get('last_model_metadata'),
                        'function_localization': 'trusted_manifest_symbol',
                        'localization': 'wrong_statement_observed' if 'UnboundLocalError' in output and not rejected else 'unknown_response_not_retained',
                        'structured_output': 'accepted_by_stage_lines' if not rejected else 'json_and_change_fields_accepted_before_source_rejection',
                        'source_validation': attempt.get('message') if rejected else 'accepted',
                        'problem_context': 'trailing_failure_only_no_passing_test_contracts; causal_contribution_unproven',
                        'replacement_logic': 'combined_candidate_incorrect_observed' if outcome == 'targeted_tests_failed' else 'not_independently_tested',
                        'full_upstream_regression': 'not_executed',
                        'inference_failure': False,
                        'evidence_limit': 'Raw prompt/response and rejected-call latency were not retained. Test output applies to the whole candidate, including both symbols for case454.',
                    })
                    if rejected:
                        break
        assert len(calls) == report['model_calls'] == 12
        seen = {}
        for call in calls:
            digest = call['response_sha256']
            key = (call['case'], call['symbol'], digest)
            call['identical_prior_response_call'] = seen.get(key) if digest else None
            if digest:
                seen[key] = call['call']
        runs.append({'run_url': f'https://github.com/Ledgercorp/BountyForge/actions/runs/{run_id}',
                     'revision': report['revision'], 'experiment': report['experiment'],
                     'artifact_path': filename, 'artifact_sha256': hashlib.sha256(data).hexdigest(),
                     'repairs_passed': report['passed'], 'cases_attempted': report['attempted'],
                     'calls': calls, 'recorded_generation_seconds': round(sum(c['recorded_generation_seconds'] or 0 for c in calls), 3),
                     'unrecorded_call_latencies': sum(c['recorded_generation_seconds'] is None for c in calls),
                     'case_wall_seconds': round(sum(t['elapsed_seconds'] for t in report['tasks']), 3)})
    return {'schema': 1, 'call_count': 24, 'runs': runs,
            'protocol_findings': [
                'The prompt supplied at most 400 trailing failure characters; earlier failures and passing contracts were absent.',
                'Retries reset to the original source and omitted the prior candidate; deterministic sampling repeated some rejected hypotheses.',
                'The v3 shared system prompt included an unrelated boolean inversion example and a single-line instruction despite a three-change validator.',
                'Statement admission did not prove dataflow correctness: uninitialized end/hnbytes and wrong return values were accepted syntactically.',
                'v4 retained finish_reason=stop for every recorded call: no evidence establishes truncation or timeout as a cause.',
                'No full upstream suite was run. These are curated excerpt failures, never full-regression failures.',
                'Missing raw responses prevent exact per-call semantic reconstruction; protocol weaknesses are hypotheses, not proof of model intent.',
            ]}


if __name__ == '__main__':
    output = ROOT / 'evidence/phase5/historical-call-audit.json'
    output.write_text(json.dumps(audit(), indent=2) + '\n')
    print(output)
