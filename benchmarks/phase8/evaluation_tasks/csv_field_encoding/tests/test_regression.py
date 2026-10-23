import unittest

from subject import quote_csv_field


class MaintenanceContract(unittest.TestCase):

    def test_comma(self):
        self.assertEqual(quote_csv_field('a,b'), '"a,b"')

    def test_line_feed(self):
        self.assertEqual(quote_csv_field('a\nb'), '"a\nb"')

    def test_carriage_return(self):
        self.assertEqual(quote_csv_field('a\rb'), '"a\rb"')

    def test_embedded_quote(self):
        self.assertEqual(quote_csv_field('a"b'), '"a""b"')

    def test_plain(self):
        self.assertEqual(quote_csv_field('word'), 'word')

    def test_empty(self):
        self.assertEqual(quote_csv_field(''), '')

    def test_whitespace_unicode(self):
        self.assertEqual(quote_csv_field(' 雪 '), ' 雪 ')


if __name__ == '__main__':
    unittest.main()
