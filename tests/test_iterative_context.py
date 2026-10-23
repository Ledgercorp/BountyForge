"""Owned neutral examples, never historical solutions or live model calls."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bountyforge.drafts import DraftRejected
from bountyforge.lineedit import propose_lines, stage_lines
from bountyforge.repair_context import build_prompt


class IterativeContextTests(unittest.TestCase):
    def prompt(self, source, **extra):
        issue = dict(repair_protocol='ast_contract_v7', target_symbol='check', **extra)
        return build_prompt(source, 'module.py', {3, 4}, issue)

    def test_attribute_constraints_are_derived_from_source_without_importing(self):
        source = 'import secret_module\ndef check(value):\n    text = value.strip()\n    return text.isdigit()\n'
        system, raw = self.prompt(source)
        data = json.loads(raw)
        self.assertEqual(data['validator_constraints']['existing_attributes'], ['isdigit', 'strip'])
        self.assertTrue(data['validator_constraints']['new_attributes_prohibited'])
        self.assertIn('removes the original', system)
        self.assertNotIn('secret_module', data['validator_constraints']['existing_attributes'])

    def test_test_contract_keeps_loop_inputs_and_local_setup(self):
        contract = '''class Contract:
    def test_cases(self):
        samples = ('a1', 'b2')
        for sample in samples:
            self.assertTrue(check(sample))
'''
        _, raw = self.prompt('def check(value):\n    text = value\n    return False\n',
                             test_contract_untrusted=contract)
        data = json.loads(raw)
        self.assertIn("samples = ('a1', 'b2')", data['test_contract_untrusted'])
        self.assertIn('for sample in samples:', data['test_contract_untrusted'])
        self.assertIn('self.assertTrue(check(sample))', data['test_contract_untrusted'])

    def test_retry_retains_baseline_and_latest_error_instead_of_traceback_header(self):
        baseline = 'FAIL: test_old (Contract.test_old)\nAssertionError: old result'
        latest = '=' * 200 + '\nERROR: test_new (Contract.test_new)\nUnboundLocalError: missing local'
        _, raw = self.prompt('def check(x):\n    y=x\n    return y\n',
                             baseline_failure=baseline, test_failure_excerpt=latest,
                             prior_error=latest, previous_proposal='{"changes":[]}')
        data = json.loads(raw)
        self.assertIn('AssertionError: old result', data['baseline_failure_untrusted'])
        self.assertIn('UnboundLocalError: missing local', data['failure_untrusted'])
        self.assertNotIn('====', data['previous_error'])
        self.assertEqual(data['previous_proposal'], '{"changes":[]}')
        self.assertLessEqual(len(raw.encode()), 3600)

    def test_unchanged_validators_reject_new_attribute_and_declarations(self):
        source = 'def check(x):\n    return x.strip()\n'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'module.py').write_text(source)
            for new in ('return x.lower()', 'def unexpected():\n    return x'):
                with self.subTest(new=new), self.assertRaises(DraftRejected):
                    stage_lines(json.dumps({'changes': [{'line': 2, 'new': new}]}),
                                root, 'module.py', [2], hashlib.sha256(source.encode()).hexdigest())

    def test_v7_uses_existing_line_interface_and_preserves_v5_prompt(self):
        class Model:
            def complete_line(self, system, prompt, max_tokens):
                self.data = json.loads(prompt)
                return '{"changes":[{"line":2,"new":"return x + 2"}]}'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'module.py').write_text('def check(x):\n    return x + 1\n')
            for protocol in ('ast_contract_v5', 'ast_contract_v7'):
                model = Model()
                result = propose_lines({'verification': 'unverified_candidate',
                                        'target_symbol': 'check', 'repair_protocol': protocol},
                                       root, 'module.py', [2], model)
                self.assertEqual('validator_constraints' in model.data, protocol == 'ast_contract_v7')
                self.assertIn('return x + 2', result['files'][0]['content'])

    def test_duplicate_retry_is_rejected_without_writing_source(self):
        previous = '{"changes":[{"line":2,"new":"return x + 2"}]}'
        class Model:
            def complete_line(self, *args, **kwargs):
                return json.dumps(json.loads(previous), indent=2)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'module.py'
            original = 'def check(x):\n    return x + 1\n'; path.write_text(original)
            with self.assertRaisesRegex(DraftRejected, 'Repeated rejected proposal'):
                propose_lines({'verification': 'unverified_candidate', 'target_symbol': 'check',
                               'repair_protocol': 'ast_contract_v7', 'previous_proposal': previous},
                              root, 'module.py', [2], Model())
            self.assertEqual(path.read_text(), original)

    def test_oversized_contract_units_are_explicitly_marked_incomplete(self):
        contract = 'def test_big():\n    assert check(' + repr('x' * 1300) + ')\n'
        _, raw = self.prompt('def check(x):\n    y=x\n    return y\n',
                             test_contract_untrusted=contract)
        data = json.loads(raw)
        self.assertFalse(data['test_contract_complete'])
        self.assertEqual(data['test_contract_untrusted'], '')


if __name__ == '__main__':
    unittest.main()
