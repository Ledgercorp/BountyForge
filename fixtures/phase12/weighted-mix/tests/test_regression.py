import unittest
from subject import weighted_mix

class Contract(unittest.TestCase):
    def test_weighted(self):
        self.assertEqual(weighted_mix([(10, 1), (20, 3)]), 17.5)
    def test_unit_weight(self):
        self.assertEqual(weighted_mix([(2, 1), (6, 1)]), 4)
    def test_empty(self):
        self.assertEqual(weighted_mix([]), 0.0)
    def test_zero_weight(self):
        self.assertEqual(weighted_mix([(99, 0)]), 0.0)
    def test_fractional(self):
        self.assertEqual(weighted_mix([(2, .25), (6, .75)]), 5)
    def test_iterator(self):
        self.assertEqual(weighted_mix(iter([(3, 2), (9, 2)])), 6)
