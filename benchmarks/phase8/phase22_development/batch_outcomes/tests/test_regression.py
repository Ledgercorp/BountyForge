import unittest
from subject import summarize_batch


class Regression(unittest.TestCase):
    def test_zero_preserved(self):
        self.assertEqual(summarize_batch([{"ok":True,"value":0}])["values"],[0])
    def test_false_preserved(self):
        self.assertEqual(summarize_batch([{"ok":True,"value":False}])["count"],1)
    def test_empty_string(self):
        self.assertEqual(summarize_batch([{"ok":True,"value":""}])["values"],[""])
    def test_non_boolean_retryable(self):
        self.assertEqual(summarize_batch([{"ok":False,"retryable":1}])["failures"],1)
    def test_retryable_true(self):
        self.assertEqual(summarize_batch([{"ok":False,"retryable":True}])["retries"],1)
    def test_none_skipped(self):
        self.assertEqual(summarize_batch([{"ok":True,"value":None}])["count"],0)
    def test_normal_value(self):
        self.assertEqual(summarize_batch([{"ok":True,"value":8}])["values"],[8])
    def test_input_preserved(self):
        responses=[{"ok":True,"value":2}];summarize_batch(responses)
        self.assertEqual(responses,[{"ok":True,"value":2}])


if __name__ == "__main__":
    unittest.main()
