import unittest

from subject import stable_unique


class MaintenanceContract(unittest.TestCase):

    def test_encounter_order(self):
        self.assertEqual(stable_unique([3, 1, 3, 2]), [3, 1, 2])

    def test_strings(self):
        self.assertEqual(stable_unique(['z', 'a', 'z']), ['z', 'a'])

    def test_empty(self):
        self.assertEqual(stable_unique([]), [])

    def test_duplicates(self):
        self.assertEqual(stable_unique([2, 2, 2]), [2])

    def test_tuple_items(self):
        self.assertEqual(stable_unique([(2, 0), (1, 0), (2, 0)]), [(2, 0), (1, 0)])

    def test_unchanged(self):
        items = [3, 1, 3]
        stable_unique(items)
        self.assertEqual(items, [3, 1, 3])

    def test_unhashable(self):
        with self.assertRaises(TypeError):
            stable_unique([[1]])


if __name__ == '__main__':
    unittest.main()
