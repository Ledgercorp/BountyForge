import unittest
from bountyforge.repair_engines import digest
from bountyforge.unseen_evaluation import prepare_handoff


class PublicHandoffTests(unittest.TestCase):
    def task(self):
        source='def count(values):\n    return len(values) - 1\n'
        return {'task_id':'external-example','source':source,'source_sha256':digest(source.encode()),
                'requirements':'Return the item count.','verifier_commitment_sha256':'a'*64}

    def test_public_handoff_is_hash_bound_without_claiming_unseen_accuracy(self):
        result=prepare_handoff(self.task())
        self.assertEqual(len(result['handoff_sha256']),64)
        self.assertFalse(result['held_out_blindness_verified'])
        self.assertFalse(result['execution_authorized'])

    def test_answers_tests_and_caller_admission_flags_are_refused(self):
        for key in ('tests','reference_solution','held_out_blindness_verified','execution_authorized'):
            with self.assertRaises(ValueError):prepare_handoff(dict(self.task(),**{key:True}))
        task=self.task();task['source']+='pass\n'
        with self.assertRaises(ValueError):prepare_handoff(task)
