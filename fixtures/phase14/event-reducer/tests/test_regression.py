import unittest
from subject import apply_events
class Contract(unittest.TestCase):
    def e(self, id, amount, kind="credit"): return {"id":id,"amount":amount,"kind":kind}
    def test_opening(self): self.assertEqual(apply_events({"balance":100,"seen":()},[self.e("a",20)])["balance"],120)
    def test_accumulate(self): self.assertEqual(apply_events({"balance":100,"seen":()},[self.e("a",20),self.e("b",5,"debit")])["balance"],115)
    def test_duplicate(self): self.assertEqual(apply_events({"balance":10,"seen":()},[self.e("a",3),self.e("a",3)])["balance"],13)
    def test_already_seen(self): self.assertEqual(apply_events({"balance":10,"seen":("a",)},[self.e("a",7)])["balance"],10)
    def test_unsupported(self): self.assertEqual(apply_events({"balance":10,"seen":()},[self.e("a",7,"other")]),{"balance":10,"seen":()})
    def test_sorted(self): self.assertEqual(apply_events({"balance":0,"seen":()},[self.e("z",2),self.e("a",4)])["seen"],("a","z"))
    def test_unchanged(self):
        state={"balance":10,"seen":["old"]}; apply_events(state,[self.e("a",2)]); self.assertEqual(state,{"balance":10,"seen":["old"]})
