import unittest

from subject import sample_median


class MaintenanceContract(unittest.TestCase):

    def test_even(self):
        self.assertEqual(sample_median([2, 8]), 5)

    def test_odd(self):
        self.assertEqual(sample_median([9, 1, 4]), 4)

    def test_unordered_even(self):
        self.assertEqual(sample_median([10, 2, 8, 4]), 6)

    def test_negative(self):
        self.assertEqual(sample_median([-9, -3]), -6)

    def test_singleton(self):
        self.assertEqual(sample_median([7]), 7)

    def test_unchanged(self):
        values = [4, 2, 9, 1]
        sample_median(values)
        self.assertEqual(values, [4, 2, 9, 1])

    def test_empty(self):
        with self.assertRaises(ValueError):
            sample_median([])


if __name__ == '__main__':
    unittest.main()
