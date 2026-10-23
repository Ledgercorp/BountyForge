import unittest
from subject import canonical_header

class HeaderTests(unittest.TestCase):
    def test_repeated_separators(self): self.assertEqual(canonical_header('X--Trace---Id'), 'x_trace_id')
    def test_leading_and_trailing_separators(self): self.assertEqual(canonical_header('--X-Id-'), 'x_id')
    def test_only_separators(self): self.assertEqual(canonical_header('---'), '')
    def test_ordinary_header(self): self.assertEqual(canonical_header(' Content-Type '), 'content_type')
    def test_existing_underscore(self): self.assertEqual(canonical_header('X_TRACE'), 'x_trace')
    def test_empty(self): self.assertEqual(canonical_header(' '), '')
