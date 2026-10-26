import unittest
from subject import after_failure


class Regression(unittest.TestCase):
    def test_exact_limit(self):
        self.assertEqual(after_failure({"status":"retrying","attempts":2},3,5)["status"],"failed")
    def test_third_delay(self):
        self.assertEqual(after_failure({"status":"retrying","attempts":2},5,5)["delay"],20)
    def test_first(self):
        self.assertEqual(after_failure({"status":"pending","attempts":0},3,5)["delay"],5)
    def test_second(self):
        self.assertEqual(after_failure({"status":"retrying","attempts":1},4,5)["delay"],10)
    def test_terminal_delay(self):
        self.assertEqual(after_failure({"status":"retrying","attempts":1},2,5)["delay"],0)
    def test_attempt_increment(self):
        self.assertEqual(after_failure({"status":"pending","attempts":0},3,5)["attempts"],1)
    def test_cancelled(self):
        self.assertEqual(after_failure({"status":"cancelled","attempts":0},3,5),{"status":"cancelled","attempts":0})
    def test_input_unchanged(self):
        job={"status":"pending","attempts":0};after_failure(job,3,5)
        self.assertEqual(job,{"status":"pending","attempts":0})


if __name__ == "__main__":
    unittest.main()
