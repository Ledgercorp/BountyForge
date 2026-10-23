import unittest

from subject import without_keys


class MaintenanceContract(unittest.TestCase):

    def test_remove(self):
        self.assertEqual(without_keys({'a': 1, 'secret': 2}, ['secret']), {'a': 1})

    def test_input_preserved(self):
        data = {'a': 1, 'secret': 2}
        without_keys(data, ['secret'])
        self.assertEqual(data, {'a': 1, 'secret': 2})

    def test_distinct_result(self):
        data = {'a': 1}
        self.assertIsNot(without_keys(data, []), data)

    def test_absent(self):
        self.assertEqual(without_keys({'a': 1}, ['missing']), {'a': 1})

    def test_falsy(self):
        self.assertEqual(without_keys({'a': 0, 'b': None}, ['b']), {'a': 0})

    def test_empty(self):
        self.assertEqual(without_keys({}, ['secret']), {})

    def test_shallow(self):
        nested = []
        self.assertIs(without_keys({'a': nested}, [])['a'], nested)


if __name__ == '__main__':
    unittest.main()
