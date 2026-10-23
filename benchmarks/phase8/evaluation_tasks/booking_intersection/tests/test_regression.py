import unittest

from subject import intervals_overlap


class MaintenanceContract(unittest.TestCase):

    def test_touching_right(self):
        self.assertFalse(intervals_overlap(1, 3, 3, 5))

    def test_touching_left(self):
        self.assertFalse(intervals_overlap(3, 5, 1, 3))

    def test_nested(self):
        self.assertTrue(intervals_overlap(1, 9, 3, 5))

    def test_partial(self):
        self.assertTrue(intervals_overlap(-4, 2, 1, 6))

    def test_disjoint(self):
        self.assertFalse(intervals_overlap(1, 2, 4, 8))

    def test_empty(self):
        self.assertFalse(intervals_overlap(2, 2, 1, 4))

    def test_inverted(self):
        self.assertFalse(intervals_overlap(7, 1, 0, 8))


if __name__ == '__main__':
    unittest.main()
