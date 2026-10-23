import unittest
from subject import ingest_page
class Contract(unittest.TestCase):
    def test_next(self): self.assertEqual(ingest_page({"status":200,"items":[1],"next_cursor":"b"},"a"),{"rows":[1],"cursor":"b","complete":False,"retry":False})
    def test_empty(self): self.assertEqual(ingest_page({"status":200,"next_cursor":""},"a")["cursor"],"")
    def test_missing(self): self.assertIsNone(ingest_page({"status":200},"a")["cursor"])
    def test_terminal(self): self.assertTrue(ingest_page({"status":200,"next_cursor":""},"a")["complete"])
    def test_rate_limit(self): self.assertEqual(ingest_page({"status":429},"a"),{"rows":[],"cursor":"a","complete":False,"retry":True})
    def test_server_error(self): self.assertFalse(ingest_page({"status":503},"a")["retry"])
    def test_unchanged(self):
        response={"status":200,"items":[1],"next_cursor":"b"}; ingest_page(response,"a"); self.assertEqual(response,{"status":200,"items":[1],"next_cursor":"b"})
