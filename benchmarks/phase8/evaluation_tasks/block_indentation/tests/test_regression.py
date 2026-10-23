import unittest

from subject import indent_block


class MaintenanceContract(unittest.TestCase):

    def test_single(self):
        self.assertEqual(indent_block('one', '> '), '> one')

    def test_multiple(self):
        self.assertEqual(indent_block('a\nb', '>'), '>a\n>b')

    def test_terminal_lf(self):
        self.assertEqual(indent_block('a\n', '>'), '>a\n')

    def test_interior_blank(self):
        self.assertEqual(indent_block('a\n\nb\n', '>'), '>a\n>\n>b\n')

    def test_empty(self):
        self.assertEqual(indent_block('', '>'), '')

    def test_empty_prefix(self):
        self.assertEqual(indent_block('a\n', ''), 'a\n')

    def test_default_prefix(self):
        self.assertEqual(indent_block('雪'), '    雪')


if __name__ == '__main__':
    unittest.main()
