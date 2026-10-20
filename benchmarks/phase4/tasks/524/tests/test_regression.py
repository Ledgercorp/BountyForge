import unittest
from strutils import bytes2human
class T(unittest.TestCase):
 def test_rounded_megabyte(self): self.assertEqual(bytes2human(1048575),'1M')
 def test_rounded_kib(self): self.assertEqual(bytes2human(1023.5),'1K')
 def test_rounded_one_digit(self): self.assertEqual(bytes2human(1023.99,1),'1.0K')
 def test_existing(self): self.assertEqual(bytes2human(1024),'1K')