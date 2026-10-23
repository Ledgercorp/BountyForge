import unittest

from subject import normalize_rooted_path


class MaintenanceContract(unittest.TestCase):

    def test_above_root(self):
        self.assertEqual(normalize_rooted_path('/../../docs'), '/docs')

    def test_root_parent(self):
        self.assertEqual(normalize_rooted_path('/..'), '/')

    def test_normal_parent(self):
        self.assertEqual(normalize_rooted_path('/a/b/../c'), '/a/c')

    def test_repeated_separators(self):
        self.assertEqual(normalize_rooted_path('//a///b/'), '/a/b')

    def test_dot_components(self):
        self.assertEqual(normalize_rooted_path('/./a/./b/.'), '/a/b')

    def test_root(self):
        self.assertEqual(normalize_rooted_path('/'), '/')

    def test_literal_names(self):
        self.assertEqual(normalize_rooted_path('/.../%2e%2e/雪'), '/.../%2e%2e/雪')

    def test_relative_rejected(self):
        with self.assertRaises(ValueError):
            normalize_rooted_path('a/b')


if __name__ == '__main__':
    unittest.main()
