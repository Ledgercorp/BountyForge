import unittest

from subject import format_authority


class MaintenanceContract(unittest.TestCase):

    def test_ipv6(self):
        self.assertEqual(format_authority('2001:db8::1', 443), '[2001:db8::1]:443')

    def test_ipv4(self):
        self.assertEqual(format_authority('127.0.0.1', 80), '127.0.0.1:80')

    def test_hostname(self):
        self.assertEqual(format_authority('example.test', 8080), 'example.test:8080')

    def test_already_bracketed(self):
        self.assertEqual(format_authority('[::1]', 80), '[::1]:80')

    def test_whitespace(self):
        self.assertEqual(format_authority(' ::1 ', 1), '[::1]:1')

    def test_upper_port(self):
        self.assertEqual(format_authority('host', 65535), 'host:65535')

    def test_invalid_port(self):
        with self.assertRaises(ValueError):
            format_authority('host', 0)

    def test_empty_host(self):
        with self.assertRaises(ValueError):
            format_authority('  ', 80)


if __name__ == '__main__':
    unittest.main()
