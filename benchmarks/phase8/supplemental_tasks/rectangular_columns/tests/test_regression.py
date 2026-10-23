import unittest

from subject import transpose_cells


class MaintenanceContract(unittest.TestCase):

    def test_shorter_later_row(self):
        with self.assertRaises(ValueError):
            transpose_cells([[1, 2], [3]])

    def test_longer_later_row(self):
        with self.assertRaises(ValueError):
            transpose_cells([[1], [2, 3]])

    def test_empty_later_row(self):
        with self.assertRaises(ValueError):
            transpose_cells([[1], []])

    def test_rectangular(self):
        self.assertEqual(transpose_cells([[1, 2, 3], [4, 5, 6]]), [[1, 4], [2, 5], [3, 6]])

    def test_empty(self):
        self.assertEqual(transpose_cells([]), [])

    def test_zero_width(self):
        self.assertEqual(transpose_cells([[], []]), [])

    def test_tuple_rows(self):
        self.assertEqual(transpose_cells(((None, 'x'), (False, 'y'))), [[None, False], ['x', 'y']])

    def test_input_preserved(self):
        rows = [[1, 2], [3, 4]]
        transpose_cells(rows)
        self.assertEqual(rows, [[1, 2], [3, 4]])


if __name__ == '__main__':
    unittest.main()
