import unittest
from cacheutils import ThresholdCounter
class T(unittest.TestCase):
 def test_omitted(self): self.assertEqual(ThresholdCounter({'a':2,'b':4}).most_common(),[('b',4),('a',2)])
 def test_zero(self): self.assertEqual(ThresholdCounter({'a':2}).most_common(0),[])
 def test_one(self): self.assertEqual(ThresholdCounter({'a':2,'b':4}).most_common(1),[('b',4)])