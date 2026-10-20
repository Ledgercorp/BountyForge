import unittest
from strutils import bytes2human

class Bytes2HumanUpstreamIssue524(unittest.TestCase):
    def test_boundary_just_below_megabyte(self): self.assertEqual(bytes2human(1048575), '1M')
    def test_boundary_fractional_kib(self): self.assertEqual(bytes2human(1023.5), '1K')
    def test_boundary_fractional_ndigits(self): self.assertEqual(bytes2human(1023.99, 1), '1.0K')
    def test_existing_example(self): self.assertEqual(bytes2human(128991), '126K')
    def test_existing_magnitude(self): self.assertEqual(bytes2human(1024**8), '1Y')