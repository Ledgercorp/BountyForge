import unittest
from subject import shipment_total

class ShipmentTests(unittest.TestCase):
    def test_below_threshold_total(self):
        self.assertEqual(shipment_total([{'unit_price': 4, 'quantity': 2}], 10, 3), {'goods': 8, 'shipping': 3, 'total': 11})
    def test_exact_threshold(self):
        self.assertEqual(shipment_total([{'unit_price': 5, 'quantity': 2}], 10, 3), {'goods': 10, 'shipping': 0, 'total': 10})
    def test_above_threshold(self):
        self.assertEqual(shipment_total([{'unit_price': 6, 'quantity': 2}], 10, 3), {'goods': 12, 'shipping': 0, 'total': 12})
    def test_empty(self):
        self.assertEqual(shipment_total([], 10, 3), {'goods': 0, 'shipping': 0, 'total': 0})
    def test_cancelled(self):
        self.assertEqual(shipment_total([{'unit_price': 20, 'quantity': 3, 'cancelled': True}], 10, 3), {'goods': 0, 'shipping': 0, 'total': 0})
    def test_invalid_quantities(self):
        self.assertEqual(shipment_total([{'unit_price': 5, 'quantity': True}, {'unit_price': 8, 'quantity': -1}, {'unit_price': 3, 'quantity': '2'}], 10, 2), {'goods': 0, 'shipping': 0, 'total': 0})
    def test_accumulates_rows(self):
        self.assertEqual(shipment_total([{'unit_price': 2, 'quantity': 2}, {'unit_price': 3, 'quantity': 2}], 10, 3), {'goods': 10, 'shipping': 0, 'total': 10})
    def test_preserves_inputs(self):
        rows=[{'unit_price': 2, 'quantity': 1}]
        shipment_total(rows, 10, 3)
        self.assertEqual(rows,[{'unit_price': 2, 'quantity': 1}])
