import unittest
from subject import nonblank_tokens

class Contract(unittest.TestCase):
    def test_blank(self): self.assertEqual(nonblank_tokens(['', '  ', 'x']), ['x'])
    def test_trim(self): self.assertEqual(nonblank_tokens([' a ', '\tb\n']), ['a', 'b'])
    def test_empty(self): self.assertEqual(nonblank_tokens([]), [])
