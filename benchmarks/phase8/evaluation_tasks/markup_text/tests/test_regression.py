import unittest

from subject import escape_markup


class MaintenanceContract(unittest.TestCase):

    def test_angles(self):
        self.assertEqual(escape_markup('<x>'), '&lt;x&gt;')

    def test_ampersand(self):
        self.assertEqual(escape_markup('A & B'), 'A &amp; B')

    def test_mixed(self):
        self.assertEqual(escape_markup('<&>'), '&lt;&amp;&gt;')

    def test_entity_text(self):
        self.assertEqual(escape_markup('&lt;'), '&amp;lt;')

    def test_quotes(self):
        self.assertEqual(escape_markup("'quoted' \"text\""), "'quoted' \"text\"")

    def test_empty(self):
        self.assertEqual(escape_markup(''), '')

    def test_unicode(self):
        self.assertEqual(escape_markup('雪<'), '雪&lt;')


if __name__ == '__main__':
    unittest.main()
