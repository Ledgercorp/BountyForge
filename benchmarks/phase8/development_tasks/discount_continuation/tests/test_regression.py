import unittest
from subject import discounted_total

class DiscountTests(unittest.TestCase):
    def test_partial_discount(self): self.assertEqual(discounted_total([40, 60], 25), 75)
    def test_no_discount(self): self.assertEqual(discounted_total([4, 6], 0), 10)
    def test_full_discount(self): self.assertEqual(discounted_total([4, 6], 100), 0)
    def test_rounding(self): self.assertEqual(discounted_total([19.99], 10), 17.99)
    def test_empty(self): self.assertEqual(discounted_total([], 25), 0)
    def test_input_preserved(self):
        prices = [4, 6]
        discounted_total(prices, 25)
        self.assertEqual(prices, [4, 6])
    def test_invalid_discount(self):
        for percent in (-1, 101):
            with self.assertRaises(ValueError): discounted_total([10], percent)
