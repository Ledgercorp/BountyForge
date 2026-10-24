import unittest
from subject import reconcile_inventory

class InventoryTests(unittest.TestCase):
    def test_accumulated_adjustments(self):
        self.assertEqual(reconcile_inventory({'a': 5}, [{'sku': 'a', 'delta': 2, 'approved': True}, {'sku': 'a', 'delta': 3, 'approved': True}]), {'a': 10})
    def test_missing_approval(self):
        self.assertEqual(reconcile_inventory({'a': 5}, [{'sku': 'a', 'delta': 2}]), {'a': 5})
    def test_nonboolean_approval(self):
        self.assertEqual(reconcile_inventory({'a': 5}, [{'sku': 'a', 'delta': 2, 'approved': 'yes'}]), {'a': 5})
    def test_rejected(self):
        self.assertEqual(reconcile_inventory({'a': 5}, [{'sku': 'a', 'delta': 2, 'approved': False}]), {'a': 5})
    def test_clamp_each_step(self):
        self.assertEqual(reconcile_inventory({'a': 2}, [{'sku': 'a', 'delta': -5, 'approved': True}, {'sku': 'a', 'delta': 4, 'approved': True}]), {'a': 4})
    def test_new_skus(self):
        self.assertEqual(reconcile_inventory({}, [{'sku': 'a', 'delta': 2, 'approved': True}, {'sku': 'b', 'delta': 3, 'approved': True}]), {'a': 2, 'b': 3})
    def test_invalid_delta(self):
        self.assertEqual(reconcile_inventory({'a': 5}, [{'sku': 'a', 'delta': True, 'approved': True}, {'sku': 'b', 'delta': '3', 'approved': True}]), {'a': 5, 'b': 0})
    def test_preserves_inputs(self):
        stock={'a': 2};rows=[{'sku': 'a', 'delta': 1, 'approved': True}]
        result=reconcile_inventory(stock, rows)
        self.assertIsNot(result, stock)
        self.assertEqual(stock, {'a': 2});self.assertEqual(rows,[{'sku': 'a', 'delta': 1, 'approved': True}])
