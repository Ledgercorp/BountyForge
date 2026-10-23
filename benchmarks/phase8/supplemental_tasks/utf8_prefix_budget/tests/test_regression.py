import unittest

from subject import fit_utf8_prefix


class MaintenanceContract(unittest.TestCase):

    def test_ascii(self):
        self.assertEqual(fit_utf8_prefix('abcd', 2), 'ab')

    def test_multibyte(self):
        self.assertEqual(fit_utf8_prefix('a雪b', 3), 'a')

    def test_exact_multibyte(self):
        self.assertEqual(fit_utf8_prefix('a雪b', 4), 'a雪')

    def test_emoji(self):
        self.assertEqual(fit_utf8_prefix('🙂x', 4), '🙂')

    def test_no_skipping(self):
        self.assertEqual(fit_utf8_prefix('雪ab', 2), '')

    def test_zero_empty(self):
        self.assertEqual(fit_utf8_prefix('x', 0), '')
        self.assertEqual(fit_utf8_prefix('', 5), '')

    def test_combining_code_points(self):
        self.assertEqual(fit_utf8_prefix('éx', 2), 'e')

    def test_negative(self):
        with self.assertRaises(ValueError):
            fit_utf8_prefix('x', -1)


if __name__ == '__main__':
    unittest.main()
