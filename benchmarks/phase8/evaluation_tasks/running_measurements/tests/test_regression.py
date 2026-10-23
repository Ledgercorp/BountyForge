import unittest

from subject import running_totals


class MaintenanceContract(unittest.TestCase):

    def test_positive(self):
        self.assertEqual(running_totals([2, 3, 4]), [2, 5, 9])

    def test_negative(self):
        self.assertEqual(running_totals([-2, 5, -4]), [-2, 3, -1])

    def test_zeros(self):
        self.assertEqual(running_totals([3, 0, 0]), [3, 3, 3])

    def test_empty(self):
        self.assertEqual(running_totals([]), [])

    def test_tuple(self):
        self.assertEqual(running_totals((1, 2)), [1, 3])

    def test_unchanged(self):
        values = [1, 2, 3]
        running_totals(values)
        self.assertEqual(values, [1, 2, 3])

    def test_fractional(self):
        self.assertEqual(running_totals([0.5, 0.25, -0.5]), [0.5, 0.75, 0.25])


if __name__ == '__main__':
    unittest.main()
