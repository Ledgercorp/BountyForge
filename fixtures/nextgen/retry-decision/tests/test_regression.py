import unittest
from subject import retry_decision


class RetryTests(unittest.TestCase):
    def test_success_is_terminal(self):self.assertEqual(retry_decision(200,1,4,2,30),{'retry':False,'attempt':1,'delay':0})
    def test_client_failure_is_terminal(self):self.assertFalse(retry_decision(404,0,3,2,30)['retry'])
    def test_initial_delay(self):self.assertEqual(retry_decision(503,0,3,2,30),{'retry':True,'attempt':1,'delay':2})
    def test_exponential_delay(self):self.assertEqual(retry_decision(429,2,4,3,100)['delay'],12)
    def test_cap(self):self.assertEqual(retry_decision(408,5,7,3,20)['delay'],20)
    def test_limit_is_terminal(self):self.assertEqual(retry_decision(500,3,3,2,30),{'retry':False,'attempt':3,'delay':0})
    def test_beyond_limit_is_terminal(self):self.assertFalse(retry_decision(503,4,3,2,30)['retry'])
    def test_zero_retry_budget(self):self.assertFalse(retry_decision(503,0,0,2,30)['retry'])
