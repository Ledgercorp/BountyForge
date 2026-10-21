import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.drafts import DraftRejected
from bountyforge.lineedit import propose_lines, stage_lines
from bountyforge.repair_context import build_prompt, physical_lines


class RepairContextTests(unittest.TestCase):
    def test_complete_flow_and_multiline_dependencies_without_docstrings(self):
        source = ('BASE = (1,\n        2)\nUNUSED = 9\n'
                  'def adjust(x):\n    """noise"""\n    value = BASE[0]\n'
                  '    if x:\n        value += x\n    return value\n')
        _, raw = build_prompt(source, 'a.py', {6, 7, 8, 9}, {
            'target_symbol': 'adjust', 'test_contract_untrusted': 'assert adjust(2)==3',
            'previous_proposal': '{"changes":[]}', 'prior_error': 'assertion mismatch'})
        data = json.loads(raw)
        self.assertIn('2:         2)', data['source_lines_untrusted'])
        self.assertIn('7:     if x:', data['source_lines_untrusted'])
        self.assertNotIn('noise', data['source_lines_untrusted'])
        self.assertNotIn('UNUSED', data['source_lines_untrusted'])
        self.assertEqual(data['previous_proposal'], '{"changes":[]}')
        self.assertIn('adjust(2)', data['test_contract_untrusted'])

    def test_ambiguous_symbol_and_budget_fail_before_inference(self):
        for source in ('def f(): pass\ndef f(): pass\n',
                       'def f():\n    return "' + 'x'*2300 + '"\n'):
            with self.assertRaises(DraftRejected):
                build_prompt(source, 'a.py', {2}, {'target_symbol': 'f'})

    def test_unicode_literals_do_not_shift_ast_physical_line_numbers(self):
        source = 'TEXT = "a\u2028b\u2029c"\ndef f():\n    return 1\n'
        self.assertEqual(len(physical_lines(source)), 3)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'a.py').write_text(source)
            fixed = stage_lines(json.dumps({'changes': [{'line': 3, 'new': 'return 2'}]}),
                                root, 'a.py', [3], hashlib.sha256(source.encode()).hexdigest())
        self.assertIn('a\u2028b\u2029c', fixed['files'][0]['content'])
        self.assertIn('    return 2\n', fixed['files'][0]['content'])

    def test_opt_in_routes_through_existing_validator(self):
        class Model:
            def complete_line(self, system, user, max_tokens):
                self.data = json.loads(user)
                assert max_tokens == 150
                return '{"changes":[{"line":2,"new":"return open(\'secret\')"}]}'
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'a.py').write_text('def f():\n    return 1\n')
            model = Model()
            with self.assertRaises(DraftRejected):
                propose_lines({'verification': 'unverified_candidate',
                               'repair_protocol': 'ast_contract_v5', 'target_symbol': 'f'},
                              root, 'a.py', [2], model)
            self.assertEqual(model.data['editable_lines'], [2])
