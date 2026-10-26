import unittest
from subject import apply_response


class Regression(unittest.TestCase):
    def test_empty_items_explicit(self):
        self.assertEqual(apply_response({"items":[1],"cursor":3},{"status":200,"body":{"items":[]}})["items"],[])
    def test_no_content_clears(self):
        self.assertEqual(apply_response({"items":[1],"cursor":3},{"status":204})["items"],[])
    def test_missing_items(self):
        self.assertEqual(apply_response({"items":[1],"cursor":3},{"status":200,"body":{}})["items"],[1])
    def test_new_items(self):
        self.assertEqual(apply_response({"items":[1],"cursor":3},{"status":200,"body":{"items":[2]}})["items"],[2])
    def test_null_cursor(self):
        self.assertIsNone(apply_response({"items":[1],"cursor":3},{"status":200,"body":{"cursor":None}})["cursor"])
    def test_zero_cursor(self):
        self.assertEqual(apply_response({"items":[1],"cursor":3},{"status":200,"body":{"cursor":0}})["cursor"],0)
    def test_error_preserves(self):
        self.assertEqual(apply_response({"items":[1],"cursor":3},{"status":503}),{"items":[1],"cursor":3})
    def test_input_not_aliased(self):
        cache={"items":[1],"cursor":3};out=apply_response(cache,{"status":200,"body":{}});out["items"].append(2)
        self.assertEqual(cache,{"items":[1],"cursor":3})


if __name__ == "__main__":
    unittest.main()
