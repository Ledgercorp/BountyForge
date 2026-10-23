import unittest
from subject import parse_configuration

class ConfigurationTests(unittest.TestCase):
    def test_colons_in_value(self):
        self.assertEqual(parse_configuration(['endpoint: https://example.test:8443/api']),
                         {'endpoint': 'https://example.test:8443/api'})
    def test_comments_whitespace_and_empty_lines(self):
        self.assertEqual(parse_configuration([' ', '# ignored', ' mode : safe ']), {'mode': 'safe'})
    def test_empty_value(self): self.assertEqual(parse_configuration(['token:']), {'token': ''})
    def test_later_value_wins(self):
        self.assertEqual(parse_configuration(['mode:first', 'mode:second']), {'mode': 'second'})
    def test_empty_input(self): self.assertEqual(parse_configuration([]), {})
    def test_invalid_record(self):
        with self.assertRaises(ValueError): parse_configuration(['not a setting'])
