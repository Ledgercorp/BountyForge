import unittest
from subject import merge_settings

class Contract(unittest.TestCase):
    def test_precedence(self): self.assertEqual(merge_settings({'x': 1}, {'x': 2}), {'x': 2})
    def test_missing(self): self.assertEqual(merge_settings({'x': 1}, {'y': 2}), {'x': 1, 'y': 2})
    def test_inputs(self):
        defaults, overrides = {'x': 1}, {'x': 2}
        result = merge_settings(defaults, overrides)
        self.assertEqual((defaults, overrides), ({'x': 1}, {'x': 2}))
        self.assertIsNot(result, defaults)
        self.assertIsNot(result, overrides)
