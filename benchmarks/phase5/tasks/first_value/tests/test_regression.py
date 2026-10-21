import unittest
from subject import first_values

class Contract(unittest.TestCase):
    def test_duplicate(self): self.assertEqual(first_values([('a', 1), ('a', 9)]), {'a': 1})
    def test_distinct(self): self.assertEqual(first_values([('a', 1), ('b', 2)]), {'a': 1, 'b': 2})
    def test_empty(self): self.assertEqual(first_values([]), {})
