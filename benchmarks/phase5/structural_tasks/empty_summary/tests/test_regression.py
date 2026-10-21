import unittest
from subject import summarize_numbers

class Contract(unittest.TestCase):
    def test_empty(self): self.assertEqual(summarize_numbers([]), {'count': 0, 'total': 0})
    def test_values(self): self.assertEqual(summarize_numbers([2, 4]), {'count': 2, 'total': 6})
    def test_negative(self): self.assertEqual(summarize_numbers([-3, 3]), {'count': 2, 'total': 0})
    def test_zero(self): self.assertEqual(summarize_numbers([0]), {'count': 1, 'total': 0})
