import copy
import unittest
from subject import apply_release


class ReleaseContract(unittest.TestCase):
    def test_settled_accumulates(self):
        self.assertEqual(apply_release({'held':10,'released':3,'seen':[]},
            [{'id':'a','status':'settled','amount':4},{'id':'b','status':'settled','amount':2}]),
            {'held':4,'released':9,'seen':['a','b']})

    def test_pending_can_later_settle(self):
        self.assertEqual(apply_release({'held':10,'released':0,'seen':[]},
            [{'id':'a','status':'pending','amount':8},{'id':'a','status':'settled','amount':3}]),
            {'held':7,'released':3,'seen':['a']})

    def test_cancelled_ignored(self):
        self.assertEqual(apply_release({'held':10,'released':2,'seen':[]},
            [{'id':'a','status':'cancelled','amount':4}]),{'held':10,'released':2,'seen':[]})

    def test_clamp_and_duplicates(self):
        self.assertEqual(apply_release({'held':3,'released':5,'seen':[]},
            [{'id':'a','status':'settled','amount':10},{'id':'a','status':'settled','amount':10}]),
            {'held':0,'released':8,'seen':['a']})

    def test_invalid_amount_preserves_balance(self):
        self.assertEqual(apply_release({'held':10,'released':7,'seen':[]},
            [{'id':'a','status':'settled','amount':True}]),{'held':10,'released':7,'seen':['a']})

    def test_already_seen(self):
        self.assertEqual(apply_release({'held':9,'released':4,'seen':['a']},
            [{'id':'a','status':'settled','amount':3}]),{'held':9,'released':4,'seen':['a']})

    def test_missing_status_ignored(self):
        self.assertEqual(apply_release({'held':9,'released':4,'seen':[]},
            [{'id':'a','amount':3}]),{'held':9,'released':4,'seen':[]})

    def test_empty_and_input_custody(self):
        state={'held':9,'released':4,'seen':['a']};before=copy.deepcopy(state)
        self.assertEqual(apply_release(state,[]),before)
        self.assertEqual(state,before)
