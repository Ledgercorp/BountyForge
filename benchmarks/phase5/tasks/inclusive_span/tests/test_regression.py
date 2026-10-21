import unittest
from subject import integer_span

class Contract(unittest.TestCase):
    def test_endpoints(self): self.assertEqual(integer_span(2, 4), [2, 3, 4])
    def test_equal(self): self.assertEqual(integer_span(3, 3), [3])
    def test_reversed(self): self.assertEqual(integer_span(4, 2), [])
