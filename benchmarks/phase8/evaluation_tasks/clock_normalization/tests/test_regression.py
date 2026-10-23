import unittest

from subject import clock_parts


class MaintenanceContract(unittest.TestCase):

    def test_within_day(self):
        self.assertEqual(clock_parts(125), (2, 5))

    def test_midnight(self):
        self.assertEqual(clock_parts(1440), (0, 0))

    def test_multiple_days(self):
        self.assertEqual(clock_parts(4381), (1, 1))

    def test_negative_minute(self):
        self.assertEqual(clock_parts(-1), (23, 59))

    def test_negative_day(self):
        self.assertEqual(clock_parts(-1440), (0, 0))

    def test_zero(self):
        self.assertEqual(clock_parts(0), (0, 0))

    def test_day_equivalence(self):
        self.assertEqual(clock_parts(91), clock_parts(91 + 1440 * 7))


if __name__ == '__main__':
    unittest.main()
