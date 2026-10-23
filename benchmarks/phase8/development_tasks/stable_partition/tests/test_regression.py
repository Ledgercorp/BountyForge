import unittest
from subject import stable_partition

class PartitionTests(unittest.TestCase):
    def test_both_orders(self):
        self.assertEqual(stable_partition([1, 2, 3, 4], {2, 4}), ([2, 4], [1, 3]))
    def test_duplicates_preserved(self):
        self.assertEqual(stable_partition([3, 1, 3, 2, 1], {3}), ([3, 3], [1, 2, 1]))
    def test_nothing_selected(self):
        self.assertEqual(stable_partition([0, 2, 1], set()), ([], [0, 2, 1]))
    def test_all_selected(self): self.assertEqual(stable_partition([2, 1], {1, 2}), ([2, 1], []))
    def test_empty_input(self): self.assertEqual(stable_partition([], {1}), ([], []))
    def test_inputs_not_mutated(self):
        values, selected = [1, 3, 2], {2}
        stable_partition(values, selected)
        self.assertEqual(values, [1, 3, 2])
        self.assertEqual(selected, {2})
