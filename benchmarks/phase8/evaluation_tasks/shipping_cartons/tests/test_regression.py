import unittest

from subject import carton_count


class MaintenanceContract(unittest.TestCase):

    def test_remainder(self):
        self.assertEqual(carton_count(11, 5), 3)

    def test_exact(self):
        self.assertEqual(carton_count(10, 5), 2)

    def test_single(self):
        self.assertEqual(carton_count(1, 20), 1)

    def test_zero(self):
        self.assertEqual(carton_count(0, 20), 0)

    def test_unit_capacity(self):
        self.assertEqual(carton_count(19, 1), 19)

    def test_large(self):
        self.assertEqual(carton_count(1000001, 1000), 1001)

    def test_negative(self):
        with self.assertRaises(ValueError):
            carton_count(-1, 3)

    def test_zero_capacity(self):
        with self.assertRaises(ValueError):
            carton_count(1, 0)


if __name__ == '__main__':
    unittest.main()
