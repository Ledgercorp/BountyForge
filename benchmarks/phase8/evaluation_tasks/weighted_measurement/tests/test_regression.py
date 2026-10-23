import unittest

from subject import weighted_mean


class MaintenanceContract(unittest.TestCase):

    def test_unequal_weights(self):
        self.assertEqual(weighted_mean([10, 20], [1, 3]), 17.5)

    def test_equal_weights(self):
        self.assertEqual(weighted_mean([3, 9], [1, 1]), 6)

    def test_zero_weight_item(self):
        self.assertEqual(weighted_mean([500, 7], [0, 3]), 7)

    def test_fractional_weights(self):
        self.assertAlmostEqual(weighted_mean([-4, 8], [0.25, 0.5]), 4)

    def test_preserve_inputs(self):
        values, weights = [2, 6], [1, 3]
        weighted_mean(values, weights)
        self.assertEqual((values, weights), ([2, 6], [1, 3]))

    def test_bad_lengths(self):
        with self.assertRaises(ValueError):
            weighted_mean([1], [1, 2])

    def test_zero_total(self):
        with self.assertRaises(ValueError):
            weighted_mean([1, 2], [0, 0])

    def test_negative_weight(self):
        with self.assertRaises(ValueError):
            weighted_mean([1, 2], [-1, 2])


if __name__ == '__main__':
    unittest.main()
