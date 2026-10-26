import unittest
from subject import latest_records


class Regression(unittest.TestCase):
    def test_zero_id(self):
        self.assertIn(0,latest_records([{"id":0,"version":1}]))
    def test_newer_wins(self):
        self.assertEqual(latest_records([{"id":"a","version":1},{"id":"a","version":3}])["a"]["version"],3)
    def test_older_loses(self):
        self.assertEqual(latest_records([{"id":"a","version":3},{"id":"a","version":1}])["a"]["version"],3)
    def test_equal_preserves_first(self):
        self.assertEqual(latest_records([{"id":"a","version":1,"x":1},{"id":"a","version":1,"x":2}])["a"]["x"],1)
    def test_none_ignored(self):
        self.assertEqual(latest_records([{"id":None,"version":1}]),{})
    def test_empty_id(self):
        self.assertIn("",latest_records([{"id":"","version":1}]))
    def test_copies_records(self):
        row={"id":"a","version":1};out=latest_records([row]);out["a"]["version"]=9
        self.assertEqual(row["version"],1)
    def test_empty(self):
        self.assertEqual(latest_records([]),{})


if __name__ == "__main__":
    unittest.main()
