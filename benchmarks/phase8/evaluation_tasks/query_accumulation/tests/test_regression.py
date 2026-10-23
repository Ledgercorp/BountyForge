import unittest

from subject import collect_values


class MaintenanceContract(unittest.TestCase):

    def test_repeated(self):
        self.assertEqual(collect_values([('a', 1), ('a', 2)]), {'a': [1, 2]})

    def test_interleaved(self):
        self.assertEqual(collect_values([('b', 1), ('a', 2), ('b', 3)]), {'b': [1, 3], 'a': [2]})

    def test_falsy(self):
        self.assertEqual(collect_values([('a', None), ('a', 0), ('a', '')]), {'a': [None, 0, '']})

    def test_empty(self):
        self.assertEqual(collect_values([]), {})

    def test_input_unchanged(self):
        pairs = [('a', 1), ('a', 2)]
        collect_values(pairs)
        self.assertEqual(pairs, [('a', 1), ('a', 2)])

    def test_independent_lists(self):
        result = collect_values([('a', 1), ('b', 2)])
        self.assertIsNot(result['a'], result['b'])

    def test_key_order(self):
        self.assertEqual(list(collect_values([('b', 1), ('a', 2), ('b', 3)])), ['b', 'a'])


if __name__ == '__main__':
    unittest.main()
