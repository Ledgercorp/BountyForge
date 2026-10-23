import unittest
from subject import label_order

class Contract(unittest.TestCase):
    def test_first_spelling_order(self):
        self.assertEqual(label_order(['Alpha', 'BETA', 'alpha', 'Gamma']), ['Alpha', 'BETA', 'Gamma'])
    def test_unicode(self):
        self.assertEqual(label_order(['Straße', 'STRASSE', 'X']), ['Straße', 'X'])
    def test_empty(self):
        self.assertEqual(label_order([]), [])
    def test_single(self):
        self.assertEqual(label_order(['X', 'x']), ['X'])
    def test_preserves_input(self):
        labels = ['b', 'a']
        label_order(labels)
        self.assertEqual(labels, ['b', 'a'])
