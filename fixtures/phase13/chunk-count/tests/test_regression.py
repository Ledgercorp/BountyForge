import unittest
from subject import chunk_count
class Contract(unittest.TestCase):
    def test_partial(self): self.assertEqual(chunk_count(11, 4), 3)
    def test_exact(self): self.assertEqual(chunk_count(12, 4), 3)
    def test_empty(self): self.assertEqual(chunk_count(0, 7), 0)
    def test_one(self): self.assertEqual(chunk_count(1, 9), 1)
    def test_unit(self): self.assertEqual(chunk_count(5, 1), 5)
    def test_invalid(self):
        for count,size in [(-1,2),(1,0),(2,-1)]:
            with self.assertRaises(ValueError): chunk_count(count,size)
