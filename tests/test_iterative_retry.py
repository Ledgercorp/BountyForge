"""Neutral owned orchestration example; no upstream repair answers or inference."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from benchmarks.phase4 import benchmark_runner as runner


class IterativeRetryTests(unittest.TestCase):
    def test_validated_sibling_can_repeat_after_other_symbol_is_rejected(self):
        class NeutralModel:
            responses = []
            def complete_line(self, system, prompt, max_tokens):
                data = json.loads(prompt)
                if data['target_symbol'] == 'first':
                    response = '{"changes":[{"line":2,"new":"return x # UNIT_ONLY"}]}'
                elif len(self.responses) == 1:
                    response = '{"changes":[{"line":4,"new":"return ("}]}'
                else:
                    response = '{"changes":[{"line":4,"new":"return x # UNIT_ONLY"}]}'
                self.responses.append(response)
                return response
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); task = root / 'unit'; task.mkdir()
            (task / 'module.py').write_text('def first(x):\n    return x\ndef second(x):\n    return x\n')
            (task / 'tests').mkdir()
            (task / 'tests/test_regression.py').write_text('# UNIT_ONLY; not executed\n')
            spec = {'id': 'unit', 'issue': 'owned:unit', 'blob': 'UNIT_ONLY', 'file': 'module.py',
                    'description': 'Neutral two-symbol retry coordination.', 'symbols': ['first', 'second']}
            baseline = {'passed': False, 'returncode': 1, 'output': 'FAILED (failures=1)'}
            model = NeutralModel()
            with patch.object(runner, 'MANIFEST', {'tasks': [spec]}), \
                    patch('bountyforge.curated_tasks.TASKS', root), \
                    patch.dict('os.environ', {'BOUNTYFORGE_CURATED_DOCKER': '1'}), \
                    patch('bountyforge.curated_docker.verify_runtime_boundary', return_value={}), \
                    patch.object(runner, 'tests', side_effect=[baseline, {'passed': True}]) as tests:
                result = runner.run(model=model, output=root/'report.json', protocol='ast_contract_v7')
        self.assertEqual(result['model_calls'], 4)
        self.assertEqual(len(model.responses), 4)
        self.assertEqual(model.responses[0], model.responses[2])
        attempts = result['tasks'][0]['attempts']
        self.assertEqual(attempts[0]['failure_reason'], 'proposal_rejected')
        self.assertEqual(attempts[1]['status'], 'passed')
        self.assertEqual(tests.call_count, 2)  # Baseline and second candidate only.
        retry_prompt = json.loads(attempts[1]['calls'][0]['prompt'])
        self.assertEqual(retry_prompt['previous_proposal'], model.responses[0])
        self.assertEqual(retry_prompt['previous_proposal_status'], 'source_validated_partial')
        rejected_prompt = json.loads(attempts[1]['calls'][1]['prompt'])
        self.assertEqual(rejected_prompt['previous_proposal_status'], 'rejected_candidate')


if __name__ == '__main__':
    unittest.main()
