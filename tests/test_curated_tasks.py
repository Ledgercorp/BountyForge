import json
import tempfile
import unittest
from pathlib import Path
from bountyforge import curated_tasks as ct
from bountyforge.drafts import DraftRejected


class CuratedTaskTests(unittest.TestCase):
    def test_scope_is_statements_and_referenced_globals(self):
        source = 'DATA = [1]\nUNRELATED = 2\ndef f():\n    "doc"\n    return DATA[0]\n'
        self.assertEqual(ct.editable_scope(source, 'f'), [1, 5])

    def test_duplicate_or_unknown_symbol_rejected(self):
        for source in ('def f(): pass\ndef f(): pass\n', 'def other(): pass\n'):
            with self.assertRaises(DraftRejected):
                ct.editable_scope(source, 'f')

    def test_scope_budget_rejects_large_functions(self):
        with self.assertRaises(DraftRejected):
            ct.editable_scope('def f():\n' + '    x = 1\n' * 31, 'f')

    def test_validated_proposal_replay_is_bound_to_original(self):
        # A neutral semantic change, deliberately not a historical solution.
        raw = json.dumps({'changes': [{'line': 22, 'new': 'abs_bytes = abs(nbytes) + 0'}]})
        result = ct.replay('459', [{'symbol': 'bytes2human', 'response': raw}])
        self.assertIn('abs(nbytes) + 0', result)
        with self.assertRaises(DraftRejected):
            ct.replay('459', [{'symbol': 'not_allowed', 'response': raw}])

    def test_declarations_and_unapproved_lines_remain_blocked(self):
        for change in ({'line': 8, 'new': 'def evil(): pass'},
                       {'line': 22, 'new': 'def evil():\n    pass'}):
            with self.assertRaises(DraftRejected):
                ct.replay('459', [{'symbol': 'bytes2human', 'response': json.dumps({'changes': [change]})}])
