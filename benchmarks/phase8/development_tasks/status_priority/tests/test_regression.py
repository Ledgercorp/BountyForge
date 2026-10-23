import unittest
from subject import classify_status

class StatusTests(unittest.TestCase):
    def test_unknown_is_rejected_even_at_limit(self): self.assertEqual(classify_status('invalid', 3, 3), 'rejected')
    def test_success_has_priority(self): self.assertEqual(classify_status('ok', 5, 1), 'complete')
    def test_transient_with_allowance(self):
        for status in ('busy', 'transient'): self.assertEqual(classify_status(status, 1, 3), 'retry')
    def test_transient_at_limit(self):
        for status in ('busy', 'transient'): self.assertEqual(classify_status(status, 3, 3), 'held')
    def test_no_retries(self): self.assertEqual(classify_status('busy', 0, 0), 'held')
    def test_unknown_below_limit(self): self.assertEqual(classify_status('invalid', 0, 3), 'rejected')
    def test_negative_counts(self):
        for attempts, limit in ((-1, 3), (1, -1)):
            with self.assertRaises(ValueError): classify_status('busy', attempts, limit)
