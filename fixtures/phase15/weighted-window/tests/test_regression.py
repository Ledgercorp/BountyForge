import copy
import unittest
from subject import summarize_window


class WindowContract(unittest.TestCase):
    def test_weighted_mean(self):
        self.assertEqual(summarize_window([{'at':1,'value':2,'weight':3},{'at':2,'value':10,'weight':1}],0,3),4)

    def test_upper_bound_excluded(self):
        self.assertEqual(summarize_window([{'at':1,'value':2},{'at':3,'value':50}],0,3),2)

    def test_lower_bound_included(self):
        self.assertEqual(summarize_window([{'at':0,'value':6,'weight':2}],0,3),6)

    def test_zero_width_is_empty(self):
        self.assertIsNone(summarize_window([{'at':2,'value':8}],2,2))

    def test_null_and_invalid_weights(self):
        self.assertEqual(summarize_window([{'at':1,'value':None,'weight':2},
            {'at':1,'value':100,'weight':False},{'at':1,'value':5,'weight':2}],0,3),5)

    def test_zero_value_and_fractional_weight(self):
        self.assertEqual(summarize_window([{'at':1,'value':0,'weight':0.5},{'at':2,'value':9,'weight':1}],0,3),6)

    def test_empty(self):
        self.assertIsNone(summarize_window([],0,3))

    def test_input_custody(self):
        rows=[{'at':2,'value':8}];before=copy.deepcopy(rows)
        self.assertEqual(summarize_window(rows,0,3),8)
        self.assertEqual(rows,before)
