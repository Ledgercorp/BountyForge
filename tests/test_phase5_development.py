import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.phase5 import development_runner as dev
from bountyforge.curated_docker import CuratedSandboxUnavailable


class DevelopmentAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'work'
        self.task = dev.task_spec('inclusive_span')
        shutil.copytree(dev.TASKS / self.task['id'], self.root)
        (self.root / dev.MARKER).write_text(self.task['id'])

    def test_catalog_is_fixed_owned_development(self):
        self.assertEqual(dev.MANIFEST['kind'], 'owned_development_only')
        self.assertEqual(len(dev.MANIFEST['tasks']), 4)
        for task in dev.MANIFEST['tasks']:
            self.assertEqual(set(task['sha256']), {'subject.py', 'tests/test_regression.py'})
            for filename, digest in task['sha256'].items():
                self.assertEqual(hashlib.sha256((dev.TASKS / task['id'] / filename).read_bytes()).hexdigest(), digest)
        self.assertEqual(dev.verify_development(self.root), self.root.resolve())

    def test_model_cannot_supply_arbitrary_source(self):
        (self.root / 'subject.py').write_text('raise RuntimeError("outside catalog")\n')
        with self.assertRaises(CuratedSandboxUnavailable):
            dev.verify_development(self.root)

    def test_acceptance_tests_cannot_change(self):
        (self.root / 'tests/test_regression.py').write_text('print("OK")\n')
        with self.assertRaises(CuratedSandboxUnavailable):
            dev.verify_development(self.root)

    def test_python_startup_and_link_files_rejected(self):
        (self.root / 'sitecustomize.py').write_text('pass\n')
        with self.assertRaises(CuratedSandboxUnavailable):
            dev.verify_development(self.root)
        (self.root / 'sitecustomize.py').unlink()
        (self.root / 'link').symlink_to('/etc/passwd')
        with self.assertRaises(CuratedSandboxUnavailable):
            dev.verify_development(self.root)

    def test_validated_neutral_replay_and_wrong_symbol(self):
        # Deliberately not a solution: add neutral parentheses to the bug.
        raw = json.dumps({'changes': [{'line': 3, 'new': 'return list(range(first, (last)))'}]})
        receipt = {'symbol': 'integer_span', 'response': raw}
        (self.root / dev.RECEIPT).write_text(json.dumps(receipt))
        (self.root / 'subject.py').write_text((self.root / 'subject.py').read_text().replace('range(first, last)', 'range(first, (last))'))
        self.assertEqual(dev.verify_development(self.root), self.root.resolve())
        receipt['symbol'] = 'not_authorized'
        (self.root / dev.RECEIPT).write_text(json.dumps(receipt))
        with self.assertRaises(CuratedSandboxUnavailable):
            dev.verify_development(self.root)

    def test_timeout_and_host_fallback_rejected(self):
        with self.assertRaises(ValueError):
            dev.run_development_tests(self.root, timeout=200)
        with patch.object(dev.shutil, 'which', return_value=None):
            with self.assertRaises(CuratedSandboxUnavailable):
                dev.run_development_tests(self.root)

    def test_structural_catalog_is_independent_and_pinned(self):
        structural_ids = set()
        for task in dev.STRUCTURAL_MANIFEST['tasks']:
            structural_ids.add(task['id'])
            trusted = dev.trusted_task_directory(task['id'])
            self.assertEqual(trusted.parent, dev.STRUCTURAL_TASKS)
            for filename, digest in task['sha256'].items():
                self.assertEqual(hashlib.sha256((trusted / filename).read_bytes()).hexdigest(), digest)
            work = Path(self.temporary.name) / task['id']
            shutil.copytree(trusted, work)
            (work / dev.MARKER).write_text(task['id'])
            self.assertEqual(dev.verify_development(work), work.resolve())
        self.assertEqual(len(structural_ids), 4)
        self.assertFalse(structural_ids & {task['id'] for task in dev.MANIFEST['tasks']})

    def test_structural_marker_cannot_admit_original_source(self):
        (self.root / dev.MARKER).write_text('optional_banner')
        with self.assertRaises(CuratedSandboxUnavailable):
            dev.verify_development(self.root)


class DevelopmentRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / 'result.json'

    def test_rejected_calls_keep_transcript_and_time_with_eight_call_bound(self):
        class InvalidModel:
            def complete_line(self, system, prompt, max_tokens):
                return 'not json'
        baseline = {'passed': False, 'returncode': 1, 'output': 'FAILED (failures=1)'}
        with patch.object(dev, 'verify_runtime_boundary', return_value={'admitted': True}), \
                patch.object(dev, 'run_development_tests', return_value=baseline):
            result = dev.run(model=InvalidModel(), output=self.output, protocol='legacy')
        self.assertEqual(result['model_calls'], 8)
        self.assertEqual(result['passed'], 0)
        for item in result['tasks']:
            self.assertEqual(len(item['calls']), 2)
            for call in item['calls']:
                self.assertEqual(call['response'], 'not json')
                self.assertGreaterEqual(call['seconds'], 0)
                self.assertTrue(call['prompt'])
            self.assertTrue(all(attempt['failure_reason'] == 'proposal_rejected' for attempt in item['attempts']))
        self.assertEqual(json.loads(self.output.read_text())['model_calls'], 8)

    def test_admission_failure_has_no_model_calls(self):
        with patch.object(dev, 'verify_runtime_boundary', side_effect=CuratedSandboxUnavailable('denied')):
            result = dev.run(output=self.output)
        self.assertEqual(result['model_calls'], 0)
        self.assertEqual(result['blocked'], 'sandbox_admission_failed')

    def test_endpoint_failure_disables_later_inference_and_keeps_latency(self):
        class Unavailable:
            def complete_line(self, system, prompt, max_tokens):
                raise RuntimeError('endpoint unavailable')
        baseline = {'passed': False, 'returncode': 1, 'output': 'FAILED (failures=1)'}
        with patch.object(dev, 'verify_runtime_boundary', return_value={'admitted': True}), \
                patch.object(dev, 'run_development_tests', return_value=baseline):
            result = dev.run(model=Unavailable(), output=self.output, protocol='legacy')
        self.assertEqual(result['model_calls'], 1)
        self.assertEqual(result['passed'], 0)
        call = result['tasks'][0]['calls'][0]
        self.assertEqual(call['error'], 'RuntimeError')
        self.assertIsNone(call['response'])
        self.assertGreaterEqual(call['seconds'], 0)
        self.assertTrue(all(task['status'] == 'blocked' for task in result['tasks'][1:]))

    def test_diagnosis_and_patch_calls_are_separate_with_sixteen_call_bound(self):
        class DiagnosingModel:
            def complete_diagnosis(self, system, prompt, max_tokens=125):
                data = json.loads(prompt)
                return json.dumps({'lines': data['editable_lines'][:1], 'reason': 'Unit test diagnosis only.'})
            def complete_line(self, system, prompt, max_tokens):
                return 'not json'
        baseline = {'passed': False, 'returncode': 1, 'output': 'FAILED (errors=1)'}
        with patch.object(dev, 'verify_runtime_boundary', return_value={'admitted': True}), \
                patch.object(dev, 'run_development_tests', return_value=baseline):
            result = dev.run(model=DiagnosingModel(), output=self.output,
                             protocol='ast_contract_v6', suite='structural')
        self.assertEqual(result['model_calls'], 16)
        self.assertEqual(result['max_model_calls'], 16)
        self.assertEqual(result['suite'], 'structural')
        self.assertEqual(result['passed'], 0)
        for item in result['tasks']:
            self.assertTrue(item['baseline_reproduced'])
            self.assertEqual([call['kind'] for call in item['calls']],
                             ['diagnosis', 'patch', 'diagnosis', 'patch'])
            self.assertTrue(all(call['seconds'] >= 0 for call in item['calls']))
            self.assertTrue(all(attempt['failure_reason'] == 'proposal_rejected' for attempt in item['attempts']))

    def test_diagnosis_timeout_has_no_patch_or_later_calls(self):
        class UnavailableDiagnosis:
            def complete_diagnosis(self, system, prompt, max_tokens=125):
                raise RuntimeError('diagnosis endpoint unavailable')
            def complete_line(self, system, prompt, max_tokens):
                raise AssertionError('Patch inference must not be reached')
        baseline = {'passed': False, 'returncode': 1, 'output': 'FAILED (failures=1)'}
        with patch.object(dev, 'verify_runtime_boundary', return_value={'admitted': True}), \
                patch.object(dev, 'run_development_tests', return_value=baseline):
            result = dev.run(model=UnavailableDiagnosis(), output=self.output,
                             protocol='ast_contract_v6', suite='structural')
        self.assertEqual(result['model_calls'], 1)
        call = result['tasks'][0]['calls'][0]
        self.assertEqual((call['kind'], call['error']), ('diagnosis', 'RuntimeError'))
        self.assertIsNone(call['response'])
        self.assertTrue(all(not task['calls'] for task in result['tasks'][1:]))


if __name__ == '__main__':
    unittest.main()
