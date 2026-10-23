"""Offline DeepSeek Harness candidate-handoff contract tests."""
import copy
import hashlib
import json
import unittest
from deepseek_harness_handoff import HarnessHandoffRejected, prepare_harness_handoff

TASK = {
    'engine': 'CODEX_AGENT', 'proposal_protocol': 'ast_statement_v1',
    'approved_file': 'subject.py', 'task_id': 'a'*32, 'case_id': 'owned_example',
    'revision': 0, 'source': 'def sample():\n    return 0\n',
    'tests_sha256': 'c'*64, 'state': 'AWAITING_CODEX_CANDIDATE',
    'max_attempts': 2, 'classification': 'OWNED_DEVELOPMENT',
    'independent_evaluation': False, 'customer_execution_authorized': False,
    'delivery_authorized': False,
    'editable_lines': [4, 7, 19]
}
TASK['source_sha256'] = hashlib.sha256(TASK['source'].encode()).hexdigest()


class HarnessHandoffContract(unittest.TestCase):
    def convert(self, response='{"changes":[{"line":7,"new":"return x + 1"}]}', task=None):
        return prepare_harness_handoff(response, TASK if task is None else task)

    def rejects(self, response, task=None):
        with self.assertRaises(HarnessHandoffRejected):
            self.convert(response, task)

    def test_valid_candidate_never_claims_verified(self):
        a = self.convert()
        self.assertEqual(a['admission'], 'UNADMITTED_EXTERNAL_CANDIDATE')
        for key in ('independently_verified', 'model_identity_attested',
                    'customer_execution_authorized', 'delivery_authorized'):
            self.assertFalse(a[key])
        self.assertEqual(a['task_id'], TASK['task_id'])
        self.assertEqual(json.loads(a['proposal_json'])['changes'][0]['line'], 7)

    def test_deterministic_canonical_digest(self):
        self.assertEqual(self.convert('{"changes":[{"new":"x=1","line":4}]}'),
                         self.convert('{ "changes": [ {"line":4,"new":"x=1"} ] }'))

    def test_multiple_valid_changes(self):
        candidate = self.convert('{"changes":[{"line":4,"new":"x=1"},{"line":19,"new":"return x"}]}')
        self.assertEqual(len(json.loads(candidate['proposal_json'])['changes']), 2)

    def test_disallow_markdown_fences(self):
        self.rejects(chr(96)*3 + 'json\n{"changes":[{"line":7,"new":"x=1"}]}\n' + chr(96)*3)

    def test_disallow_extra_explanations(self):
        self.rejects('{"changes":[]} I tested it')

    def test_disallow_duplicate_json_keys(self):
        self.rejects('{"changes":[{"line":7,"new":"x=1","new":"x=2"}]}')

    def test_disallow_extra_commands_or_claimed_results(self):
        self.rejects('{"changes":[{"line":7,"new":"x=1"}],"tests_passed":true}')
        self.rejects('{"changes":[{"line":7,"new":"x=1"}],"command":"rm -rf /"}')

    def test_no_arbitrary_path(self):
        self.rejects('{"changes":[{"line":7,"new":"x=1","file":"/tmp/z"}]}')

    def test_outside_scope(self):
        self.rejects('{"changes":[{"line":9,"new":"x=1"}]}')
        self.rejects('{"changes":[{"line":true,"new":"x=1"}]}')
        self.rejects('{"changes":[{"line":7,"new":"x=1"},{"line":7,"new":"x=2"}]}')

    def test_budget(self):
        self.rejects('{"changes":[]}')
        self.rejects('{"changes":[{"line":7,"new":"x=1"}]}' + ' '*3000)
        self.rejects('{"changes":[{"line":7,"new":"' + 'x'*1600 + '"}]}')
        self.rejects('{"changes":[{"line":4,"new":"a"},{"line":7,"new":"b"},{"line":19,"new":"c"},{"line":4,"new":"d"}]}')

    def test_disallow_nonfinite(self):
        self.rejects('{"changes":[{"line":7,"new":NaN}]}')
        self.rejects('{"changes":[{"line":7,"new":Infinity}]}')

    def test_disallow_surrogate(self):
        self.rejects('{"changes":[{"line":7,"new":"\\ud800"}]}')

    def test_disallow_nulls_and_cr(self):
        self.rejects('{"changes":[{"line":7,"new":"\\u0000"}]}')
        self.rejects('{"changes":[{"line":7,"new":"\\r"}]}')

    def test_disallow_invalid_task_engine(self):
        bad = copy.deepcopy(TASK); bad['engine'] = 'QWEN_LOCAL'
        self.rejects('{"changes":[{"line":7,"new":"x=1"}]}', bad)

    def test_disallow_invalid_task_hash(self):
        bad = copy.deepcopy(TASK); bad['source_sha256'] = '?'*64
        self.rejects('{"changes":[{"line":7,"new":"x=1"}]}', bad)

    def test_disallow_invalid_task_protocol(self):
        bad = copy.deepcopy(TASK); bad['approved_file'] = 'tests/test_regression.py'
        self.rejects('{"changes":[{"line":7,"new":"x=1"}]}', bad)

    def test_disallow_nonstring_candidate(self):
        self.rejects({'changes': [{'line': 7, 'new': 'x'}]})

    def test_source_tampering_rejected(self):
        bad = copy.deepcopy(TASK)
        bad['source'] += 'evil'
        self.rejects('{"changes":[{"line":7,"new":"x=1"}]}', bad)

    def test_rejects_claimed_customer_authorization(self):
        bad = copy.deepcopy(TASK)
        bad['customer_execution_authorized'] = True
        self.rejects('{"changes":[{"line":7,"new":"x=1"}]}', bad)

    def test_rejects_false_evaluation_claim(self):
        bad = copy.deepcopy(TASK)
        bad['independent_evaluation'] = True
        self.rejects('{"changes":[{"line":7,"new":"x=1"}]}', bad)

    def test_rejects_terminal_state(self):
        bad = copy.deepcopy(TASK)
        bad['state'] = 'AWAITING_OWNER_APPROVAL'
        self.rejects('{"changes":[{"line":7,"new":"x=1"}]}', bad)

    def test_no_data_mutation(self):
        task = copy.deepcopy(TASK)
        self.convert(task=task)
        self.assertEqual(task, TASK)


if __name__ == '__main__':
    unittest.main()
