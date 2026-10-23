import unittest
from subject import retry_decision
class Contract(unittest.TestCase):
    def test_backoff(self): self.assertEqual(retry_decision(503,2,None,1,30),(True,4))
    def test_cap(self): self.assertEqual(retry_decision(503,10,None,1,30),(True,30))
    def test_header(self): self.assertEqual(retry_decision(429,0,"2.5",1,30),(True,2.5))
    def test_negative(self): self.assertEqual(retry_decision(429,0,"-8",1,30),(True,0))
    def test_malformed(self): self.assertEqual(retry_decision(503,1,"bad",2,30),(True,4))
    def test_success(self): self.assertEqual(retry_decision(200,4,None,1,30),(False,0))
    def test_permanent(self): self.assertEqual(retry_decision(404,4,None,1,30),(False,0))
