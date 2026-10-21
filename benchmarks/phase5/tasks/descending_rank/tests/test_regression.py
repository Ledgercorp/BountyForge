import unittest
from subject import rank_scores

class Contract(unittest.TestCase):
    def test_order(self): self.assertEqual(rank_scores([3, 8, 1]), [8, 3, 1])
    def test_duplicates(self): self.assertEqual(rank_scores([2, 2, 1]), [2, 2, 1])
    def test_original(self):
        scores = [1, 4]
        rank_scores(scores)
        self.assertEqual(scores, [1, 4])
