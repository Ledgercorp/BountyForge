import unittest
from subject import optional_setting
class Contract(unittest.TestCase):
    def test_false(self): self.assertIs(optional_setting(False,True),False)
    def test_zero(self): self.assertEqual(optional_setting(0,8),0)
    def test_empty(self): self.assertEqual(optional_setting("","auto"),"")
    def test_missing(self): self.assertEqual(optional_setting(None,"auto"),"auto")
    def test_value(self): self.assertEqual(optional_setting("manual","auto"),"manual")
    def test_identity(self):
        value=[]
        self.assertIs(optional_setting(value,[1]),value)
