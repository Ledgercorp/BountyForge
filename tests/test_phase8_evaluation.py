"""Coordinator contracts: no imports or execution of evaluation subjects."""
import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bountyforge import phase8_evaluation as evaluation


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        # Coordinator mocks need no ambient credentials or process configuration.
        self.environment = patch.dict('os.environ', {}, clear=True)
        self.environment.start(); self.addCleanup(self.environment.stop)

    def proof(self):
        return {**dict.fromkeys(evaluation.CONTROLS, True),
                'image_digest': evaluation.IMAGE.split('@')[1],
                'untrusted_execution_certified': False}

    def failing(self, root, command, timeout):
        self.assertIsNone(command)
        tree = ast.parse((root/'tests/test_regression.py').read_text())
        name = next(n.name for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name.startswith('test_'))
        return {'passed': False, 'returncode': 1, 'timeout': False, 'error': None,
                'elapsed_seconds': 0.01,
                'output': f'FAIL: {name} (Contract.{name})\nAssertionError: owned neutral observation\nRan 6 tests\nFAILED (failures=1)'}

    def test_prepare_runs_originals_once_and_never_labels_accuracy_zero(self):
        with patch.object(evaluation, 'verify_runtime_boundary', return_value=self.proof()) as boundary, \
                patch.object(evaluation, '_execute', side_effect=self.failing) as execute:
            report = evaluation.prepare()
        boundary.assert_called_once()
        self.assertEqual(execute.call_count, 20)
        self.assertEqual(report['baseline_invocations'], 20)
        self.assertEqual(report['baseline_assertion_failures'], 20)
        self.assertEqual(report['inference_calls'], 0)
        self.assertIsNone(report['accuracy'])
        self.assertEqual(len(report['cases']), 20)
        self.assertIn('novelty', report)

    def test_incomplete_preflight_executes_no_originals(self):
        proof = self.proof(); proof.pop('pid_pressure_enforced')
        with patch.object(evaluation, 'verify_runtime_boundary', return_value=proof), \
                patch.object(evaluation, '_execute') as execute:
            report = evaluation.prepare()
        execute.assert_not_called()
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['baseline_invocations'], 0)
        self.assertIsNone(report['accuracy'])

    def test_context_failure_is_blocked_without_becoming_model_failure(self):
        with patch.object(evaluation, 'verify_runtime_boundary', return_value=self.proof()), \
                patch.object(evaluation, '_execute', side_effect=self.failing), \
                patch.object(evaluation, 'make_prompt', side_effect=ValueError('cannot fit')):
            report = evaluation.prepare()
        self.assertTrue(all(case['status'] == 'blocked' for case in report['cases']))
        self.assertTrue(all(case['reason'] == 'context_rejected' for case in report['cases']))
        self.assertEqual(report['inference_calls'], 0)
        self.assertIsNone(report['accuracy'])

    def test_invalid_receipt_never_counts_as_reproduced_baseline(self):
        receipt = {'passed': True, 'returncode': 1, 'timeout': False,
                   'error': None, 'output': 'Ran 1 test\nOK'}
        with patch.object(evaluation, 'verify_runtime_boundary', return_value=self.proof()), \
                patch.object(evaluation, '_execute', return_value=receipt):
            report = evaluation.prepare()
        self.assertEqual(report['baseline_assertion_failures'], 0)
        self.assertTrue(all(case['status'] == 'blocked' for case in report['cases']))

    def test_exact_tree_rejects_extra_marker_source_test_and_hardlink_changes(self):
        catalog = evaluation.Catalog()
        spec = catalog.tasks()[0]
        for mutation in ('extra', 'marker', 'source', 'test', 'hardlink', 'directory'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'work'
                evaluation.materialize(catalog, spec, root)
                if mutation == 'extra': (root/'extra').write_text('x')
                elif mutation == 'marker': (root/evaluation.FIXTURE_MARKER).write_text('owned-forged')
                elif mutation == 'source': (root/'subject.py').write_text('changed')
                elif mutation == 'test': (root/'tests/test_regression.py').write_text('changed')
                elif mutation == 'directory': (root/'empty').mkdir()
                else:
                    import os
                    os.link(root/'subject.py', Path(directory)/'linked')
                with self.assertRaises(evaluation.EvaluationRejected):
                    evaluation.admit(catalog, spec, root)

    def test_pinned_selection_supports_explicit_subset_and_rejects_changed_bytes(self):
        catalog = evaluation.Catalog(); ids = [catalog.tasks()[0]['id']]
        config = {'schema': 1, 'novelty': 'explicit primary subset; novelty pending',
                  'manifests': [{'path': evaluation.PRIMARY_MANIFEST,
                                'sha256': evaluation.PRIMARY_SHA256, 'case_ids': ids}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'selection.json'; path.write_text(json.dumps(config))
            pin = hashlib.sha256(path.read_bytes()).hexdigest()
            selected = evaluation.Catalog(path, pin)
            self.assertEqual([case['id'] for case in selected.tasks()], ids)
            path.write_text('{}')
            with self.assertRaises(evaluation.EvaluationRejected): selected.tasks()

    def test_replay_rejects_unbound_record_before_docker(self):
        with patch.object(evaluation, '_execute') as execute, \
                patch.object(evaluation, 'verify_runtime_boundary') as boundary:
            result = evaluation.replay({'case_id': 'stock_admission', 'session': {
                'status': 'review_ready', 'calls': [], 'patch': []}})
        execute.assert_not_called(); boundary.assert_not_called()
        self.assertEqual(result['status'], 'blocked')
        self.assertIsNone(result['accuracy'])

    def test_core_pin_failure_blocks_before_preflight(self):
        with patch.object(evaluation, 'CORE_SHA256', {'bountyforge/worker.py': '0'*64}), \
                patch.object(evaluation, 'verify_runtime_boundary') as boundary:
            report = evaluation.prepare()
        boundary.assert_not_called()
        self.assertEqual(report['status'], 'blocked')

    def test_interruption_keeps_atomic_checkpoint_before_first_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'partial.json'
            def interrupt(root, command, timeout):
                checkpoint = json.loads(path.read_text())
                self.assertEqual(checkpoint['baseline_invocations'], 1)
                self.assertEqual(checkpoint['cases'][0]['status'], 'baseline_pending')
                self.assertEqual(checkpoint['inference_calls'], 0)
                raise KeyboardInterrupt()
            with patch.object(evaluation, 'verify_runtime_boundary', return_value=self.proof()), \
                    patch.object(evaluation, '_execute', side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt): evaluation.prepare(report_path=path)
            checkpoint = json.loads(path.read_text())
            self.assertEqual(checkpoint['status'], 'preparing')
            self.assertIsNone(checkpoint['accuracy'])
            self.assertFalse(path.with_suffix('.json.tmp').exists())

    def test_postexecution_custody_mutation_is_rejected(self):
        def altered(root, command, timeout):
            result = self.failing(root, command, timeout)
            (root/'tests/test_regression.py').write_text('changed')
            return result
        with patch.object(evaluation, 'verify_runtime_boundary', return_value=self.proof()), \
                patch.object(evaluation, '_execute', side_effect=altered):
            report = evaluation.prepare()
        self.assertEqual(report['baseline_invocations'], 20)
        self.assertEqual(report['baseline_assertion_failures'], 0)
        self.assertEqual(report['status'], 'blocked')

    def test_malformed_replay_record_is_blocked_without_uncaught_exception(self):
        for record in (None, [], 'untrusted'):
            with self.subTest(record=record), patch.object(evaluation, '_execute') as execute:
                result = evaluation.replay(record)
            execute.assert_not_called()
            self.assertEqual(result['status'], 'blocked')

    def test_prepare_refuses_known_credentials_before_preflight_without_echoing_values(self):
        for name in ('GROQ_API_KEY', 'OPENAI_API_KEY', 'STRIPE_SECRET_KEY', 'GITHUB_TOKEN', 'GH_TOKEN'):
            for value in ('private-owned-test-sentinel', ''):
                with self.subTest(name=name, empty=not value), \
                        patch.dict('os.environ', {name: value}, clear=True), \
                        patch.object(evaluation, 'preflight') as boundary, \
                        patch.object(evaluation, '_execute') as execute:
                    report = evaluation.prepare()
                    self.assertEqual(report['status'], 'blocked')
                    self.assertEqual(report['baseline_invocations'], 0)
                    self.assertNotIn('private-owned-test-sentinel', json.dumps(report))
                    boundary.assert_not_called(); execute.assert_not_called()

    def test_neutral_record_replay_checks_binding_and_fresh_proof(self):
        # AST-only neutral transcript, never an evaluation-case reference repair.
        from bountyforge.statements import stage_statements
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory)/'neutral'; original.mkdir()
            (original/'tests').mkdir()
            (original/'subject.py').write_text('def scaled(value):\n    total = value * 2\n    return total\n')
            (original/'tests/test_regression.py').write_text(
                'import unittest\nfrom subject import scaled\nclass Contract(unittest.TestCase):\n'
                ' def test_scaled(self):\n  self.assertEqual(scaled(4), 12)\n')
            spec = {'id': 'neutral', 'file': 'subject.py', 'symbol': 'scaled',
                    'description': 'Use factor three.', 'catalog': 'unused/manifest.json',
                    'catalog_sha256': 'f'*64,
                    'sha256': {name: evaluation.digest((original/name).read_bytes())
                               for name in ('subject.py', 'tests/test_regression.py')}}
            baseline = {'passed': False, 'exit_code': 1, 'timeout': False,
                        'output': 'FAIL: test_scaled (Contract.test_scaled)\nAssertionError: 8 != 12\nRan 1 test\nFAILED (failures=1)'}
            scope, prompt = evaluation.context_for(spec, original, baseline)
            response = '{"changes":[{"line":2,"new":"total = value * 3"}]}'
            staged = stage_statements(response, original, 'subject.py', scope,
                                      spec['sha256']['subject.py'])['files'][0]
            patch_value = [{'path': 'subject.py', 'diff': staged['diff']}]
            passed = {'passed': True, 'exit_code': 0, 'timeout': False,
                      'output': 'Ran 1 test\nOK'}
            session = {'protocol': evaluation.PROTOCOL, 'status': 'review_ready',
                       'customer_execution_authorized': False, 'delivery_authorized': False,
                       'paid_fallback': False,
                       'source_sha256': spec['sha256']['subject.py'],
                       'tests_sha256': spec['sha256']['tests/test_regression.py'],
                       'baseline': baseline, 'editable_lines': scope, 'model_calls': 1,
                       'patch': patch_value, 'candidate_sha256': evaluation.digest(staged['content'].encode()),
                       'calls': [{'number': 1, 'system': evaluation.SESSION_SYSTEM,
                                  'prompt': prompt, 'max_tokens': 150, 'response': response,
                                  'response_sha256': evaluation.digest(response.encode()),
                                  'previous_response_sha256': None}],
                       'worker': {'status': 'review_ready', 'patch': patch_value,
                                  'independent_verification': passed,
                                  'attempts': [{'status': 'passed', 'test': passed}]}}
            result = {'passed': True, 'returncode': 0, 'timeout': False,
                      'error': None, 'output': passed['output']}
            with patch.object(evaluation.Catalog, 'tasks', return_value=[spec]), \
                    patch.object(evaluation, 'original_root', return_value=original), \
                    patch.object(evaluation, 'verify_runtime_boundary', return_value=self.proof()) as boundary, \
                    patch.object(evaluation, '_execute', return_value=result) as execute:
                report = evaluation.replay({'case_id': 'neutral', 'session': session})
                self.assertEqual(report['status'], 'replay_passed')
                self.assertIsNone(report['accuracy'])
                self.assertEqual(report['inference_calls'], 0)
                boundary.assert_called_once(); execute.assert_called_once()
                for name in ('GROQ_API_KEY', 'OPENAI_API_KEY', 'STRIPE_SECRET_KEY', 'GITHUB_TOKEN', 'GH_TOKEN'):
                    for value in ('private-owned-replay-sentinel', ''):
                        with self.subTest(credential=name, empty=not value), \
                                patch.dict('os.environ', {name: value}, clear=True):
                            boundary.reset_mock(); execute.reset_mock()
                            report = evaluation.replay({'case_id': 'neutral', 'session': session})
                            self.assertEqual(report['status'], 'blocked')
                            self.assertNotIn('private-owned-replay-sentinel', json.dumps(report))
                            boundary.assert_not_called(); execute.assert_not_called()
                for flag in ('customer_execution_authorized', 'delivery_authorized', 'paid_fallback'):
                    for value in (True, 0, None, 'false', 'missing'):
                        with self.subTest(flag=flag, value=value):
                            if value == 'missing': session.pop(flag)
                            else: session[flag] = value
                            boundary.reset_mock(); execute.reset_mock()
                            report = evaluation.replay({'case_id': 'neutral', 'session': session})
                            self.assertEqual(report['status'], 'blocked')
                            self.assertIs(report['customer_execution_authorized'], False)
                            self.assertIs(report['delivery_authorized'], False)
                            self.assertIs(report['paid_fallback'], False)
                            self.assertEqual(report['financial_authority'], 'unverified; no live inference API enabled')
                            boundary.assert_not_called(); execute.assert_not_called()
                            session[flag] = False
                session['patch'][0]['diff'] += 'forged'
                boundary.reset_mock(); execute.reset_mock()
                report = evaluation.replay({'case_id': 'neutral', 'session': session})
                self.assertEqual(report['status'], 'blocked')
                boundary.assert_not_called(); execute.assert_not_called()


if __name__ == '__main__': unittest.main()
