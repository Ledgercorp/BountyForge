import unittest

from subject import summarize_runs


class MaintenanceContract(unittest.TestCase):

    def test_single(self):
        self.assertEqual(summarize_runs(['ready']), [('ready', 1)])

    def test_one_run(self):
        self.assertEqual(summarize_runs(['x', 'x', 'x']), [('x', 3)])

    def test_last_run(self):
        self.assertEqual(summarize_runs(['x', 'x', 'y']), [('x', 2), ('y', 1)])

    def test_separated_runs(self):
        self.assertEqual(summarize_runs(['x', 'y', 'x']), [('x', 1), ('y', 1), ('x', 1)])

    def test_empty(self):
        self.assertEqual(summarize_runs([]), [])

    def test_falsy_labels(self):
        self.assertEqual(summarize_runs([None, None, 0, '', '']), [(None, 2), (0, 1), ('', 2)])

    def test_tuple_input(self):
        self.assertEqual(summarize_runs(('雪', '雪', '雨')), [('雪', 2), ('雨', 1)])

    def test_input_preserved(self):
        events = ['x', 'y']
        summarize_runs(events)
        self.assertEqual(events, ['x', 'y'])


if __name__ == '__main__':
    unittest.main()
