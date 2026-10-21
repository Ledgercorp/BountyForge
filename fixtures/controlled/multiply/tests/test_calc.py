import unittest
from calc import multiply

class MultiplyTests(unittest.TestCase):
    def test_multiply(self):
        self.assertEqual(multiply(2, 3), 6)
