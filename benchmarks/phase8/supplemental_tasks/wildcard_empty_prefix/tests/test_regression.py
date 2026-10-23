import unittest

from subject import matches_pattern


class MaintenanceContract(unittest.TestCase):

    def test_empty_star(self):
        self.assertTrue(matches_pattern('', '*'))

    def test_zero_width_star(self):
        self.assertTrue(matches_pattern('report', '*report'))

    def test_repeated_stars(self):
        self.assertTrue(matches_pattern('a', '**a**'))

    def test_star_consumption(self):
        self.assertTrue(matches_pattern('dir/file.txt', 'dir/*.txt'))

    def test_question_mark(self):
        self.assertTrue(matches_pattern('ax', 'a?'))
        self.assertFalse(matches_pattern('a', 'a?'))

    def test_whole_match(self):
        self.assertFalse(matches_pattern('prefix', 'pre'))
        self.assertFalse(matches_pattern('Prefix', 'prefix'))

    def test_empty_literals(self):
        self.assertTrue(matches_pattern('', ''))
        self.assertFalse(matches_pattern('x', ''))

    def test_literal_brackets(self):
        self.assertTrue(matches_pattern('[x]', '[x]'))
        self.assertFalse(matches_pattern('x', '[x]'))


if __name__ == '__main__':
    unittest.main()
