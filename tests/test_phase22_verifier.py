import json
from pathlib import Path
import unittest
from unittest.mock import patch


class VerifierFailureTests(unittest.TestCase):
    def test_sandbox_failure_is_not_misclassified_as_source_rejection(self):
        import phase22_repair as m
        from bountyforge.phase8_evaluation import EvaluationRejected
        record=json.loads((Path(m.ROOT)/'evidence/phase22/baseline-preparation.json').read_text())
        task=record['cases'][0]['task'];service=m.OwnedSession.__new__(m.OwnedSession)
        # Only the external Docker operation is replaced; real pinned material,
        # handoff, scope, AST/capability validators run before it.
        from bountyforge.curated_tasks import editable_scope
        service.sessions={task['case_id']:{'public':task,'spec':m.selected_case(task['case_id']),
            'scope':list(editable_scope(task['source'],task['target_symbol'])),
            'seen':set(),'semantics':set(),'attempts':[]}}
        raw=json.dumps({'changes':[{'line':9,'new':'discount = subtotal * rate'}]})
        with patch.object(service,'_observe',side_effect=EvaluationRejected('Owned Docker unavailable or exhausted budget')):
            result=service.submit(task,raw)
        self.assertEqual(result['outcome'],'SANDBOX_UNAVAILABLE')
        self.assertEqual(result['state'],'BLOCKED')
        self.assertFalse(result['independently_verified'])
