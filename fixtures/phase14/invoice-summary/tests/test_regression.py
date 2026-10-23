import unittest
from subject import invoice_summary
class Contract(unittest.TestCase):
    def row(self, qty=2, unit=50, state="active"): return {"qty":qty,"unit":unit,"state":state}
    def test_discount_tax(self): self.assertEqual(invoice_summary([self.row()],.1,.2), {"subtotal":100,"discount":10,"tax":18,"total":108})
    def test_discount_without_tax(self): self.assertEqual(invoice_summary([self.row()],.25,0)["total"],75)
    def test_full_discount(self): self.assertEqual(invoice_summary([self.row()],1,.2)["total"],0)
    def test_cancelled(self): self.assertEqual(invoice_summary([self.row(),self.row(state="cancelled")],.1,.2)["total"],108)
    def test_rounding(self): self.assertEqual(invoice_summary([self.row(3,19.99)],.15,.075), {"subtotal":59.97,"discount":9.0,"tax":3.82,"total":54.79})
    def test_unchanged(self):
        rows=[self.row()]; before=[dict(rows[0])]; invoice_summary(rows,.1,.2); self.assertEqual(rows,before)
    def test_empty(self): self.assertEqual(invoice_summary([],0,.2)["total"],0)
    def test_bad_rate(self):
        with self.assertRaises(ValueError): invoice_summary([],2,.1)
