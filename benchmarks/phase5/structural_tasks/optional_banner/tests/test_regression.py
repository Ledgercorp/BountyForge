import unittest
from subject import decorate_label

class Contract(unittest.TestCase):
    def test_default(self): self.assertEqual(decorate_label(' hello '), 'hello')
    def test_prefix(self): self.assertEqual(decorate_label('hello', ' team '), 'team hello')
    def test_empty_prefix(self): self.assertEqual(decorate_label(' hello ', ''), 'hello')
    def test_empty_label(self): self.assertEqual(decorate_label(' ', 'team'), '')
