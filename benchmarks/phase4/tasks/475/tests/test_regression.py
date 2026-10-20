import unittest
from strutils import iter_splitlines
class T(unittest.TestCase):
 def test_unicode(self): self.assertEqual(list(iter_splitlines('A\u2028B\u2029C')),['A','B','C'])
 def test_regular_date(self): self.assertEqual(list(iter_splitlines('February 28, 2026')),['February 28, 2026'])
 def test_newline(self): self.assertEqual(list(iter_splitlines('A\nB')),['A','B'])