import unittest
from subject import compact_intervals


class IntervalTests(unittest.TestCase):
    def test_empty(self):self.assertEqual(compact_intervals([]),[])
    def test_disjoint(self):self.assertEqual(compact_intervals([(1,2),(4,5)]),[(1,2),(4,5)])
    def test_touching_merge(self):self.assertEqual(compact_intervals([(1,3),(3,5)]),[(1,5)])
    def test_nested_does_not_shrink(self):self.assertEqual(compact_intervals([(1,10),(2,3)]),[(1,10)])
    def test_overlap_chain(self):self.assertEqual(compact_intervals([(1,4),(3,8),(7,10)]),[(1,10)])
    def test_unsorted_negative(self):self.assertEqual(compact_intervals([(2,4),(-3,2)]),[(-3,4)])
    def test_invalid_and_duplicate(self):self.assertEqual(compact_intervals([(3,3),(5,2),(1,4),(1,4)]),[(1,4)])
    def test_does_not_mutate_input(self):
        intervals=[(5,8),(1,3)];before=list(intervals)
        compact_intervals(intervals);self.assertEqual(intervals,before)
