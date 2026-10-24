import unittest
from subject import parse_pairs

class PairTests(unittest.TestCase):
    def test_equals_in_value(self):
        self.assertEqual(parse_pairs('token=a=b=c'), {'token': 'a=b=c'})
    def test_first_duplicate(self):
        self.assertEqual(parse_pairs('x=one;x=two'), {'x': 'one'})
    def test_stripped_duplicate(self):
        self.assertEqual(parse_pairs(' x =one; x=two'), {'x': 'one'})
    def test_empty_values(self):
        self.assertEqual(parse_pairs('x=;y=0'), {'x': '', 'y': '0'})
    def test_invalid_fragments(self):
        self.assertEqual(parse_pairs('bad; =no;ok=yes;;'), {'ok': 'yes'})
    def test_case_sensitive(self):
        self.assertEqual(parse_pairs('A=one;a=two'), {'A': 'one', 'a': 'two'})
    def test_whitespace_and_equals(self):
        self.assertEqual(parse_pairs(' a = b = c ; z= t '), {'a': 'b = c', 'z': 't'})
    def test_empty(self):
        self.assertEqual(parse_pairs(''), {})
