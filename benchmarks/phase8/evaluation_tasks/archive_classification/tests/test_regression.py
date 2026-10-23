import unittest

from subject import archive_suffix


class MaintenanceContract(unittest.TestCase):

    def test_compound(self):
        self.assertEqual(archive_suffix('source.tar.gz'), '.tar.gz')

    def test_simple_gzip(self):
        self.assertEqual(archive_suffix('source.gz'), '.gz')

    def test_zip(self):
        self.assertEqual(archive_suffix('source.zip'), '.zip')

    def test_case(self):
        self.assertEqual(archive_suffix('SOURCE.TAR.GZ'), '.tar.gz')

    def test_unknown(self):
        self.assertEqual(archive_suffix('source.txt'), '')

    def test_middle_only(self):
        self.assertEqual(archive_suffix('source.tar.gz.backup'), '')

    def test_empty(self):
        self.assertEqual(archive_suffix(''), '')


if __name__ == '__main__':
    unittest.main()
