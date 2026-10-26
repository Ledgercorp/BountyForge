import unittest
from subject import checkout_total


class Regression(unittest.TestCase):
    def test_equal_threshold(self):
        self.assertEqual(checkout_total([{"price":100,"quantity":1}],100,0.1,0)["discount"],10)
    def test_tax_after_discount(self):
        self.assertAlmostEqual(checkout_total([{"price":200,"quantity":1}],100,0.1,0.2)["tax"],36)
    def test_total(self):
        self.assertEqual(checkout_total([{"price":200,"quantity":1}],100,0.1,0.2)["total"],216)
    def test_below_threshold(self):
        self.assertEqual(checkout_total([{"price":40,"quantity":1}],100,0.1,0.2)["total"],48)
    def test_cancelled(self):
        self.assertEqual(checkout_total([{"price":200,"quantity":1,"cancelled":True}],100,0.1,0.2)["total"],0)
    def test_quantity(self):
        self.assertEqual(checkout_total([{"price":50,"quantity":3}],100,0.1,0)["total"],135)
    def test_empty(self):
        self.assertEqual(checkout_total([],100,0.1,0.2)["total"],0)
    def test_input_unchanged(self):
        rows=[{"price":100,"quantity":1}];checkout_total(rows,100,0.1,0.2)
        self.assertEqual(rows,[{"price":100,"quantity":1}])


if __name__ == "__main__":
    unittest.main()
