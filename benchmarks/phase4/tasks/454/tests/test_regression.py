import unittest
from strutils import args2sh,args2cmd
class T(unittest.TestCase):
 def test_sh_separator(self): self.assertEqual(args2sh(['aa','bb'],sep='|'),'aa|bb')
 def test_cmd_separator(self): self.assertEqual(args2cmd(['aa','bb'],sep='|'),'aa|bb')
 def test_default(self): self.assertEqual(args2sh(['aa','bb']),'aa bb')
 def test_cmd_default(self): self.assertEqual(args2cmd(['aa','bb']),'aa bb')