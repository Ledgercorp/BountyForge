import unittest

from subject import remove_suffix


class MaintenanceContract(unittest.TestCase):

    def test_repeated(self):
        self.assertEqual(remove_suffix('log.log.log', '.log'), 'log.log')

    def test_whole_string(self):
        self.assertEqual(remove_suffix('done', 'done'), '')

    def test_internal(self):
        self.assertEqual(remove_suffix('abXYZcdXYZ', 'XYZ'), 'abXYZcd')

    def test_prefix_only(self):
        self.assertEqual(remove_suffix('XYZtail', 'XYZ'), 'XYZtail')

    def test_absent(self):
        self.assertEqual(remove_suffix('report.txt', '.csv'), 'report.txt')

    def test_empty(self):
        self.assertEqual(remove_suffix('text', ''), 'text')

    def test_unicode(self):
        self.assertEqual(remove_suffix('雪-雪', '雪'), '雪-')


if __name__ == '__main__':
    unittest.main()
