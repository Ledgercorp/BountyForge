import unittest

from subject import describe_seconds


class MaintenanceContract(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(describe_seconds(0), '0 seconds')

    def test_one(self):
        self.assertEqual(describe_seconds(1), '1 second')

    def test_plural(self):
        self.assertEqual(describe_seconds(8), '8 seconds')

    def test_fraction(self):
        self.assertEqual(describe_seconds(0.5), '0.5 seconds')

    def test_float_one(self):
        self.assertEqual(describe_seconds(1.0), '1.0 second')

    def test_negative(self):
        with self.assertRaises(ValueError):
            describe_seconds(-1)


if __name__ == '__main__':
    unittest.main()
