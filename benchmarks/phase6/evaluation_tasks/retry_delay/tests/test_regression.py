import unittest
from subject import retry_delay


class Contract(unittest.TestCase):
    def test_exponential_progression(self):
        self.assertEqual([retry_delay(i, 3, 1000) for i in range(5)], [3, 6, 12, 24, 48])

    def test_ceiling_applies(self):
        self.assertEqual(retry_delay(5, 2, 10), 10)
        self.assertEqual(retry_delay(0, 30, 10), 10)

    def test_zero_base_and_ceiling(self):
        self.assertEqual(retry_delay(6, 0, 30), 0)
        self.assertEqual(retry_delay(6, 2, 0), 0)

    def test_fractional_base_preserved(self):
        self.assertEqual(retry_delay(3, 0.125, 9), 1.0)

    def test_exact_ceiling(self):
        self.assertEqual(retry_delay(4, 1, 16), 16)
        self.assertEqual(retry_delay(5, 1, 16), 16)

    def test_invalid_values_rejected(self):
        for values in ((-1, 1, 9), (0, -1, 9), (0, 1, -1)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                retry_delay(*values)
