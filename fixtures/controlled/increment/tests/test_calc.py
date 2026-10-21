import unittest
from calc import increment

class IncrementTests(unittest.TestCase):
    def test_increment(self):
        self.assertEqual(increment(5), 6)
