"""Replay acceptance tests use mocked Docker; UNIT_ONLY candidates are not fixes."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.phase5.development_runner import MARKER, RECEIPT, SUITES
from bountyforge.curated_docker import CuratedSandboxUnavailable
from bountyforge.curated_tasks import editable_scope
from bountyforge.lineedit import stage_lines
from scripts import replay_owned_canary as replay
from scripts.validate_owned_canary import CanaryRejected
from test_owned_canary_gate import REVISION, completed_report


def unit_success_report():
    """Neutral comment, with mock test success: never an autonomous repair result."""
    report = completed_report()
    task = report['tasks'][0]
    spec = SUITES['structural'][1]['tasks'][0]
    trusted = SUITES['structural'][0] / spec['id']
    source = (trusted / spec['file']).read_text()
    line = editable_scope(source, spec['symbol'])[0]
    replacement = source.splitlines()[line - 1].lstrip() + '  # UNIT_ONLY_REPLAY'
    response = json.dumps({'changes': [{'line': line, 'new': replacement}]})
    staged = stage_lines(response, trusted, spec['file'], editable_scope(source, spec['symbol']),
                         spec['sha256'][spec['file']])
    task['model_generated_success'] = True
    task['status'] = 'owned_development_passed'
    task['attempts'][0] = {'number': 1, 'status': 'passed',
                           'test': {'passed': True, 'returncode': 0, 'timeout': False,
                                    'error': None, 'output': 'Ran 4 tests\nOK\n'}}
    task['calls'][0]['response'] = response
    task['calls'][0]['response_sha256'] = hashlib.sha256(response.encode()).hexdigest()
    task['patch'] = staged['files'][0]['diff']
    report['passed'] = 1
    return report, staged['files'][0]['content']


class OwnedReplayTests(unittest.TestCase):
    def invoke(self, report):
        raw = json.dumps(report).encode()
        return replay.replay_owned_canary(raw, suite='structural', expected_revision=REVISION), raw

    def test_unit_only_neutral_candidate_reconstructed_before_mocked_docker(self):
        report, candidate = unit_success_report()
        expected = report['tasks'][0]
        observed = []
        def check(root):
            self.assertTrue(observed, 'Runtime preflight must precede source execution')
            self.assertEqual((root / MARKER).read_text(), expected['id'])
            self.assertEqual((root / 'subject.py').read_text(), candidate)
            receipt = json.loads((root / RECEIPT).read_text())
            self.assertEqual(receipt['response'], expected['calls'][0]['response'])
            self.assertEqual(hashlib.sha256((root / 'tests/test_regression.py').read_bytes()).hexdigest(),
                             expected['tests_sha256'])
            return {'passed': True, 'returncode': 0, 'timeout': False, 'error': None,
                    'output': 'UNIT_ONLY mock Docker result\nRan 4 tests\nOK\n'}
        def preflight(root):
            observed.append('preflight')
            return {'unit_only_mock_preflight': True}
        with patch.object(replay, 'verify_runtime_boundary', side_effect=preflight) as probe, \
                patch.object(replay, 'run_development_tests', side_effect=check) as run:
            result, raw = self.invoke(report)
        probe.assert_called_once()
        run.assert_called_once()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['verified_success_ids'], [expected['id']])
        self.assertEqual(result['source_report_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['model_calls'], 0)
        self.assertFalse(result['inference_performed'])

    def test_wrong_patch_rejected_before_any_docker_execution(self):
        report, _ = unit_success_report()
        report['tasks'][0]['patch'] += '\nnot the model patch'
        with patch.object(replay, 'verify_runtime_boundary') as probe, \
                patch.object(replay, 'run_development_tests') as run:
            with self.assertRaisesRegex(replay.OwnedReplayRejected, 'does not match'):
                self.invoke(report)
        probe.assert_not_called()
        run.assert_not_called()

    def test_source_validator_cannot_be_bypassed_by_reported_success(self):
        report, _ = unit_success_report()
        call = report['tasks'][0]['calls'][0]
        call['response'] = json.dumps({'changes': [{'line': 1, 'new': 'def other(): pass'}]})
        call['response_sha256'] = hashlib.sha256(call['response'].encode()).hexdigest()
        with patch.object(replay, 'verify_runtime_boundary') as probe, \
                patch.object(replay, 'run_development_tests') as run:
            with self.assertRaisesRegex(replay.OwnedReplayRejected, 'source validation'):
                self.invoke(report)
        probe.assert_not_called()
        run.assert_not_called()

    def test_missing_baseline_rejects_before_any_execution(self):
        report, _ = unit_success_report()
        report['tasks'][0]['baseline_reproduced'] = False
        with patch.object(replay, 'verify_runtime_boundary') as probe:
            with self.assertRaises(CanaryRejected): self.invoke(report)
        probe.assert_not_called()

    def test_new_runtime_admission_failure_does_not_replay(self):
        report, _ = unit_success_report()
        with patch.object(replay, 'verify_runtime_boundary', side_effect=CuratedSandboxUnavailable('denied')), \
                patch.object(replay, 'run_development_tests') as run:
            result, _ = self.invoke(report)
        run.assert_not_called()
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['verified_success_count'], 0)
        self.assertEqual(result['target_test_attempts'], 0)

    def test_independent_test_failure_cannot_promote_a_success(self):
        report, _ = unit_success_report()
        with patch.object(replay, 'verify_runtime_boundary', return_value={'unit_only': True}), \
                patch.object(replay, 'run_development_tests', return_value={
                    'passed': False, 'returncode': 1, 'output': 'UNIT_ONLY mock test failure'}):
            result, _ = self.invoke(report)
        self.assertEqual(result['status'], 'replay_failed')
        self.assertEqual(result['verified_success_count'], 0)
        self.assertFalse(result['tasks'][0]['verified'])

    def test_passed_flag_without_real_test_result_cannot_promote(self):
        report, _ = unit_success_report()
        with patch.object(replay, 'verify_runtime_boundary', return_value={'unit_only': True}), \
                patch.object(replay, 'run_development_tests', return_value={
                    'passed': True, 'returncode': 1, 'output': 'Not a passing test result'}):
            result, _ = self.invoke(report)
        self.assertEqual(result['status'], 'replay_failed')
        self.assertEqual(result['verified_success_count'], 0)

    def test_docker_unavailable_has_no_host_fallback(self):
        report, _ = unit_success_report()
        with patch.object(replay, 'verify_runtime_boundary', return_value={'unit_only': True}), \
                patch.object(replay, 'run_development_tests', side_effect=CuratedSandboxUnavailable('offline')) as run:
            result, _ = self.invoke(report)
        run.assert_called_once()
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['verified_success_count'], 0)

    def test_zero_success_evidence_never_becomes_a_repair(self):
        with patch.object(replay, 'verify_runtime_boundary', return_value={'unit_only': True}) as probe, \
                patch.object(replay, 'run_development_tests') as run:
            result, _ = self.invoke(completed_report())
        probe.assert_called_once()
        run.assert_not_called()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['verified_success_count'], 0)
        self.assertEqual(result['reported_success_ids'], [])

    def test_oversized_or_malformed_report_never_executes(self):
        for raw in (b' ' * (replay.MAX_REPORT_BYTES + 1), b'{', b''):
            with self.subTest(size=len(raw)), patch.object(replay, 'verify_runtime_boundary') as probe:
                with self.assertRaises(replay.OwnedReplayRejected):
                    replay.replay_owned_canary(raw, suite='structural', expected_revision=REVISION)
            probe.assert_not_called()

    def test_cli_rejection_writes_bounded_machine_readable_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.json'
            source.write_text('{}')
            output = Path(directory) / 'replay.json'
            arguments = ['replay_owned_canary', str(source), '--suite', 'structural',
                         '--revision', REVISION, '--output', str(output)]
            with patch('sys.argv', arguments), patch.object(replay, 'verify_runtime_boundary') as probe:
                self.assertEqual(replay.main(), 2)
            proof = json.loads(output.read_text())
            self.assertEqual(proof['status'], 'rejected')
            self.assertEqual(proof['model_calls'], 0)
            self.assertLess(output.stat().st_size, replay.MAX_REPORT_BYTES)
            probe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
