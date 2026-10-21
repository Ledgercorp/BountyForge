import unittest
from subject import parse_integer_fields


class Contract(unittest.TestCase):
    def test_zero_is_a_value(self):
        self.assertEqual(parse_integer_fields('1,0,2'), [1, 0, 2])
        self.assertEqual(parse_integer_fields('0,00,-0,+0'), [0, 0, 0, 0])

    def test_signed_values_and_spacing(self):
        self.assertEqual(parse_integer_fields(' -3 , +7 , 42 '), [-3, 7, 42])

    def test_blank_fields_only_are_ignored(self):
        self.assertEqual(parse_integer_fields(', , 5,,'), [5])
        self.assertEqual(parse_integer_fields(''), [])
        self.assertEqual(parse_integer_fields('  ,  '), [])

    def test_order_and_duplicates_are_preserved(self):
        self.assertEqual(parse_integer_fields('2,0,2,-1,0'), [2, 0, 2, -1, 0])

    def test_large_integer_is_not_truncated(self):
        self.assertEqual(parse_integer_fields('12345678901234567890'), [12345678901234567890])

    def test_malformed_fields_fail(self):
        for text in ('1,bad,2', '1.5', '--3'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_integer_fields(text)
