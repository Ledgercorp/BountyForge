import unittest
from subject import weighted_mean

class WeightedTests(unittest.TestCase):
    def test_different_weights(self): self.assertAlmostEqual(weighted_mean([(2, 1), (8, 3)]), 6.5)
    def test_zero_weight_ignored(self): self.assertAlmostEqual(weighted_mean([(100, 0), (4, 2)]), 4.0)
    def test_all_zero(self): self.assertIsNone(weighted_mean([(3, 0), (9, 0)]))
    def test_empty(self): self.assertIsNone(weighted_mean([]))
    def test_equal_weights(self): self.assertAlmostEqual(weighted_mean([(2, 2), (6, 2)]), 4.0)
    def test_negative_value(self): self.assertAlmostEqual(weighted_mean([(-2, 3), (6, 1)]), 0.0)
    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError): weighted_mean([(4, -1)])
