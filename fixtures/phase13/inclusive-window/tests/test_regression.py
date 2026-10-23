import unittest
from subject import inclusive_window
class Contract(unittest.TestCase):
    def test_endpoints(self): self.assertEqual(inclusive_window([1,2,3],1,3),[1,2,3])
    def test_equal(self): self.assertEqual(inclusive_window([3,2,3],3,3),[3,3])
    def test_order(self): self.assertEqual(inclusive_window([4,2,4,1,3],2,4),[4,2,4,3])
    def test_outside(self): self.assertEqual(inclusive_window([1,9],3,7),[])
    def test_inverted(self): self.assertEqual(inclusive_window([1,2,3],3,1),[])
    def test_empty(self): self.assertEqual(inclusive_window([],0,5),[])
