import unittest
from subject import select_page


class Contract(unittest.TestCase):
    def test_requested_count(self):
        self.assertEqual(select_page(['a', 'b', 'c', 'd'], 1, 2), ['b', 'c'])

    def test_single_record(self):
        self.assertEqual(select_page([4, 5], 0, 1), [4])

    def test_zero_limit(self):
        self.assertEqual(select_page([4, 5], 0, 0), [])
        self.assertEqual(select_page([4, 5], 1, 0), [])

    def test_offset_clamps_without_mutation(self):
        records = [8, 9, 10]
        self.assertEqual(select_page(records, -4, 2), [8, 9])
        self.assertEqual(records, [8, 9, 10])

    def test_end_clamps(self):
        self.assertEqual(select_page([1, 2, 3], 2, 10), [3])
        self.assertEqual(select_page([1, 2, 3], 6, 2), [])

    def test_empty_records_and_sequence_type(self):
        self.assertEqual(select_page([], 0, 3), [])
        self.assertEqual(select_page((1, 2, 3), 1, 2), (2, 3))

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            select_page([1, 2], 0, -1)
