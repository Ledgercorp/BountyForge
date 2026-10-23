import unittest

from subject import can_reserve


class MaintenanceContract(unittest.TestCase):

    def test_exact_stock(self):
        self.assertTrue(can_reserve(8, 8))

    def test_some_remaining(self):
        self.assertTrue(can_reserve(8, 3))

    def test_too_many(self):
        self.assertFalse(can_reserve(8, 9))

    def test_empty_no_request(self):
        self.assertTrue(can_reserve(0, 0))

    def test_empty_request(self):
        self.assertTrue(can_reserve(9, 0))

    def test_negative_stock(self):
        with self.assertRaises(ValueError):
            can_reserve(-1, 0)

    def test_negative_request(self):
        with self.assertRaises(ValueError):
            can_reserve(1, -1)


if __name__ == '__main__':
    unittest.main()
