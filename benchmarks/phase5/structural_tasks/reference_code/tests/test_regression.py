import unittest
from subject import valid_reference

class Contract(unittest.TestCase):
    def test_letter_case(self):
        for value in ('AB-123', 'ab-123', 'aB-123'): self.assertTrue(valid_reference(value))
    def test_whitespace(self): self.assertTrue(valid_reference(' AB-123 '))
    def test_invalid(self):
        for value in ('AB-1234', 'ABC-123', 'AK-123', 'AB-１２３', None): self.assertFalse(valid_reference(value))
