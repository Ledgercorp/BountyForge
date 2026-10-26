import unittest
from subject import apply_events


class Regression(unittest.TestCase):
    def test_release_exact_usage(self):
        self.assertEqual(apply_events({"used":2,"seen":set()},[{"id":"r","kind":"release","units":2}],5)["used"],0)
    def test_latest_usage(self):
        events=[{"id":"a","kind":"acquire","units":2},{"id":"r","kind":"release","units":1}]
        self.assertEqual(apply_events({"used":1,"seen":set()},events,5)["used"],2)
    def test_acquire_exact_capacity(self):
        self.assertEqual(apply_events({"used":1,"seen":set()},[{"id":"a","kind":"acquire","units":2}],3)["used"],3)
    def test_rejected_event_not_seen(self):
        self.assertEqual(apply_events({"used":1,"seen":set()},[{"id":"a","kind":"acquire","units":9}],3)["seen"],set())
    def test_duplicate(self):
        e={"id":"a","kind":"acquire","units":1};self.assertEqual(apply_events({"used":0,"seen":set()},[e,e],3)["used"],1)
    def test_count(self):
        self.assertEqual(apply_events({"used":1,"seen":set()},[{"id":"r","kind":"release","units":1}],3)["accepted"],1)
    def test_invalid_kind(self):
        self.assertEqual(apply_events({"used":1,"seen":set()},[{"id":"r","kind":"other","units":1}],3)["used"],1)
    def test_state_preserved(self):
        state={"used":1,"seen":set()};apply_events(state,[{"id":"a","kind":"acquire","units":1}],3)
        self.assertEqual(state,{"used":1,"seen":set()})


if __name__ == "__main__":
    unittest.main()
