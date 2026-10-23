import unittest
from subject import allocate_orders
class Contract(unittest.TestCase):
    def test_multiple(self): self.assertEqual(allocate_orders(10,0,[4,4,4]),[4,4,2])
    def test_reserved(self): self.assertEqual(allocate_orders(10,6,[3,3,3]),[3,1,0])
    def test_exhausted(self): self.assertEqual(allocate_orders(0,0,[2,2]),[0,0])
    def test_invalid_requests(self): self.assertEqual(allocate_orders(5,0,[-1,0,4,4]),[0,0,4,1])
    def test_single(self): self.assertEqual(allocate_orders(10,2,[20]),[8])
    def test_empty(self): self.assertEqual(allocate_orders(10,0,[]),[])
    def test_unchanged(self):
        requests=[4,4,4]; allocate_orders(10,0,requests); self.assertEqual(requests,[4,4,4])
