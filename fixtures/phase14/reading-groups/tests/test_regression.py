import unittest
from subject import group_readings
class Contract(unittest.TestCase):
    def test_missing(self): self.assertEqual(group_readings([("a",4),("a",None)]),{"a":4})
    def test_zero(self): self.assertEqual(group_readings([("a",0),("a",4)]),{"a":2})
    def test_zero_only(self): self.assertEqual(group_readings([("a",0)]),{"a":0})
    def test_normalized(self): self.assertEqual(group_readings([(" A ",2),("a",4)]),{"a":3})
    def test_all_missing(self): self.assertEqual(group_readings([("b",None)]),{"b":None})
    def test_groups(self): self.assertEqual(group_readings([("a",1),("b",8),("a",3)]),{"a":2,"b":8})
    def test_empty(self): self.assertEqual(group_readings([]),{})
