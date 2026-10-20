import unittest
from strutils import bytes2human
class T(unittest.TestCase):
 def test_yotta(self): self.assertEqual(bytes2human(1024**8),'1Y')
 def test_five_yotta(self): self.assertEqual(bytes2human(5*1024**8),'5Y')
 def test_zetta(self): self.assertEqual(bytes2human(1024**7),'1Z')