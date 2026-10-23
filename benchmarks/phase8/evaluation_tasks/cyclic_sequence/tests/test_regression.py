import unittest

from subject import rotate_left


class MaintenanceContract(unittest.TestCase):

    def test_within(self):
        self.assertEqual(rotate_left([1, 2, 3, 4], 1), [2, 3, 4, 1])

    def test_zero(self):
        self.assertEqual(rotate_left([1, 2], 0), [1, 2])

    def test_over_length(self):
        self.assertEqual(rotate_left([1, 2, 3], 4), [2, 3, 1])

    def test_negative_large(self):
        self.assertEqual(rotate_left([1, 2, 3], -4), [3, 1, 2])

    def test_empty(self):
        self.assertEqual(rotate_left([], 8), [])

    def test_singleton(self):
        self.assertEqual(rotate_left([7], 101), [7])

    def test_tuple(self):
        self.assertEqual(rotate_left((1, 2, 3), 5), (3, 1, 2))

    def test_unchanged(self):
        items = [1, 2, 3]
        rotate_left(items, 1)
        self.assertEqual(items, [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
