import hashlib
import importlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.drafts import DraftRejected


class StatementEditTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('bountyforge.statements'),
                             'Opt-in AST statement editor is not implemented')
        self.api = importlib.import_module('bountyforge.statements')

    def stage(self, source, changes, allowed, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'module.py').write_text(source)
            return self.api.stage_statements(json.dumps({'changes': changes}), root,
                kwargs.get('path', 'module.py'), allowed,
                kwargs.get('digest', hashlib.sha256(source.encode()).hexdigest()))

    def test_multiline_assignment_replaces_entire_statement_and_preserves_other_bytes(self):
        source = 'def format_amount(value):\n    amount = (\n        value *\n        10\n    )\n    return amount\n'
        result = self.stage(source, [{'line': 2, 'new': 'amount = value * 20'}], [2, 6])
        self.assertEqual(result['files'][0]['content'],
                         'def format_amount(value):\n    amount = value * 20\n    return amount\n')

    def test_condition_expression_preserves_both_branches_with_multiline_header(self):
        source = 'def permitted(value):\n    if (\n        value > 3\n    ):\n        return True\n    else:\n        return False\n'
        result = self.stage(source, [{'line': 2, 'new': 'value >= 3'}], [2, 5, 7])
        self.assertIn('    if (\n        value >= 3\n    ):\n', result['files'][0]['content'])
        self.assertIn('    else:\n        return False\n', result['files'][0]['content'])

    def test_multiple_disjoint_related_changes_use_original_offsets(self):
        source = 'def calc(x):\n    first = (\n        x + 1\n    )\n    second = x + 2\n    return first + second\n'
        result = self.stage(source, [{'line': 2, 'new': 'first = x + 3'},
                                    {'line': 5, 'new': 'second = x + 4'}], [2, 5, 6])
        self.assertIn('first = x + 3\n    second = x + 4', result['files'][0]['content'])

    def test_binding_loss_is_rejected_but_preserved_multistatement_replacement_is_valid(self):
        source = 'def total(x):\n    count = 0\n    return count + x\n'
        with self.assertRaisesRegex(DraftRejected, 'binding'):
            self.stage(source, [{'line': 2, 'new': 'other = 0'}], [2, 3])
        result = self.stage(source, [{'line': 2, 'new': 'count = 0\nextra = 1'},
                                    {'line': 3, 'new': 'return count + x + extra'}], [2, 3])
        self.assertIn('    count = 0\n    extra = 1\n', result['files'][0]['content'])

    def test_capability_declaration_and_scope_guards_are_preserved(self):
        source = 'def strip(x):\n    value = x.strip()\n    return value\n'
        for change in ({'line': 2, 'new': 'value = x.lower()'},
                       {'line': 2, 'new': 'import os\nvalue = x'},
                       {'line': 2, 'new': 'def hidden():\n    return 1'},
                       {'line': 2, 'new': "value = open('private')"},
                       {'line': 1, 'new': 'return x'},
                       {'line': 3, 'new': 'return value\n' * 4}):
            with self.subTest(change=change), self.assertRaises(DraftRejected):
                self.stage(source, [change], [2, 3])

    def test_ambiguous_inline_statement_tabs_stale_hash_and_semantic_noop_reject(self):
        with self.assertRaises(DraftRejected):
            self.stage('def f(x):\n    a = x; b = x\n    return a\n',
                       [{'line': 2, 'new': 'a = x+1'}], [2])
        with self.assertRaises(DraftRejected):
            self.stage('def f(x):\n\treturn x\n', [{'line': 2, 'new': 'return x+1'}], [2])
        with self.assertRaises(DraftRejected):
            self.stage('def f(x):\n    return x\n', [{'line': 2, 'new': 'return x+1'}], [2], digest='0'*64)
        with self.assertRaisesRegex(DraftRejected, 'ineffective'):
            self.stage('def f(x):\n    return x\n', [{'line': 2, 'new': 'return (x) # noise'}], [2])

    def test_model_cannot_supply_paths_ranges_or_duplicate_anchors(self):
        source = 'def f(x):\n    return x\n'
        for changes in ([{'line': 2, 'new': 'return x+1', 'path': 'elsewhere.py'}],
                        [{'line': 2, 'new': 'return x+1', 'end': 99}],
                        [{'line': True, 'new': 'return x+1'}],
                        [{'line': 2, 'new': 'return x+1'}]*2):
            with self.subTest(changes=changes), self.assertRaises(DraftRejected):
                self.stage(source, changes, [2])

    def test_indented_multistatement_and_unicode_offsets(self):
        source = 'def label(x):\n    text = "é"\n    if text == "é":\n        return x\n    return 0\n'
        result = self.stage(source, [{'line': 2, 'new': '    text = "é"\n    extra = 1'},
                                    {'line': 3, 'new': 'text != "z"'},
                                    {'line': 4, 'new': 'return x + extra'}], [2, 3, 4, 5])
        self.assertIn('text != "z"', result['files'][0]['content'])
        self.assertIn('    extra = 1', result['files'][0]['content'])

    def test_compile_context_and_definite_binding_loss_reject(self):
        with self.assertRaises(DraftRejected):
            self.stage('LIMIT = 1\ndef f():\n    return LIMIT\n',
                       [{'line':1,'new':'LIMIT = 2\nreturn 0'}], [1])
        with self.assertRaisesRegex(DraftRejected, 'binding'):
            self.stage('def f(x):\n    value = x\n    return value\n',
                       [{'line':2,'new':'if False:\n    value = x'}], [2,3])


if __name__ == '__main__': unittest.main()
