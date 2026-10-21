import unittest
from subject import signed_offset_minutes


class Contract(unittest.TestCase):
    def test_negative_fractional_offset(self):
        self.assertEqual(signed_offset_minutes(-5, 30), -330)
        self.assertEqual(signed_offset_minutes(-3, 45), -225)

    def test_positive_fractional_offset(self):
        self.assertEqual(signed_offset_minutes(5, 30), 330)
        self.assertEqual(signed_offset_minutes(9, 45), 585)

    def test_whole_hour_offsets(self):
        self.assertEqual(signed_offset_minutes(-12, 0), -720)
        self.assertEqual(signed_offset_minutes(2, 0), 120)

    def test_zero_hour_is_nonnegative(self):
        self.assertEqual(signed_offset_minutes(0, 45), 45)
        self.assertEqual(signed_offset_minutes(0, 0), 0)

    def test_extremes(self):
        self.assertEqual(signed_offset_minutes(-23, 59), -1439)
        self.assertEqual(signed_offset_minutes(23, 59), 1439)

    def test_invalid_components_rejected(self):
        for hours, minutes in ((24, 0), (-24, 0), (0, -1), (2, 60)):
            with self.subTest(hours=hours, minutes=minutes), self.assertRaises(ValueError):
                signed_offset_minutes(hours, minutes)
