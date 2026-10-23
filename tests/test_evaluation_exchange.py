import unittest
from bountyforge.evaluation_exchange import freeze_public_tasks,bind_candidate
from tests import test_unseen_evaluation as examples


class ExchangeTests(unittest.TestCase):
    def test_engines_share_frozen_task_commitments_without_claiming_blindness(self):
        task=examples.PublicHandoffTests().task();suite=freeze_public_tasks([task]);handoff=suite['handoffs'][0]
        proposal={'changes':[{'line':2,'new':'return len(values)'}]}
        qwen=bind_candidate(handoff,'QWEN_LOCAL',proposal);codex=bind_candidate(handoff,'CODEX_AGENT',proposal)
        self.assertEqual(qwen['handoff_sha256'],codex['handoff_sha256'])
        self.assertNotEqual(qwen['submission_sha256'],codex['submission_sha256'])
        self.assertFalse(qwen['independent_evaluation']);self.assertFalse(qwen['execution_authorized'])

    def test_test_answers_flags_and_oversized_or_unbounded_submissions_are_refused(self):
        task=examples.PublicHandoffTests().task()
        with self.assertRaises(ValueError):freeze_public_tasks([dict(task,tests='hidden')])
        with self.assertRaises(ValueError):freeze_public_tasks([task,task])
        handoff=freeze_public_tasks([task])['handoffs'][0]
        with self.assertRaises(ValueError):bind_candidate(dict(handoff,independent_evaluation=True),'CODEX_AGENT',{'changes':[]})
        with self.assertRaises(ValueError):bind_candidate(handoff,'CODEX_AGENT',{'changes':[{'line':2,'new':'return 1','path':'private.py'}]})
