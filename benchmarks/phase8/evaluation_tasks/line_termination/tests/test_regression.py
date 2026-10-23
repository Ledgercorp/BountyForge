import unittest

from subject import terminate_line


class MaintenanceContract(unittest.TestCase):

    def test_plain(self):
        self.assertEqual(terminate_line('hello'), 'hello\n')

    def test_multiple_lf(self):
        self.assertEqual(terminate_line('hello\n\n'), 'hello\n')

    def test_spaces(self):
        self.assertEqual(terminate_line('hello  '), 'hello  \n')

    def test_tabs_before_lf(self):
        self.assertEqual(terminate_line('hello\t\n'), 'hello\t\n')

    def test_leading_lf(self):
        self.assertEqual(terminate_line('\nhello'), '\nhello\n')

    def test_empty(self):
        self.assertEqual(terminate_line(''), '\n')

    def test_unicode(self):
        self.assertEqual(terminate_line('雪 '), '雪 \n')


if __name__ == '__main__':
    unittest.main()
