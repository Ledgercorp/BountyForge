import unittest
from subject import sparse_average

class Contract(unittest.TestCase):
    def test_zero_is_present(self):
        self.assertEqual(sparse_average([0, 6, None]), 3)
    def test_all_zeros(self):
        self.assertEqual(sparse_average([0, 0]), 0)
    def test_all_missing(self):
        self.assertIsNone(sparse_average([None, None]))
    def test_empty(self):
        self.assertIsNone(sparse_average([]))
    def test_signed(self):
        self.assertEqual(sparse_average([-2, 0, 8]), 2)
    def test_preserves_input(self):
        values = [None, 0, 2]
        sparse_average(values)
        self.assertEqual(values, [None, 0, 2])
