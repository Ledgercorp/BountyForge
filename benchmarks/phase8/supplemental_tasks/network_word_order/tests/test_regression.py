import unittest

from subject import decode_network_word


class MaintenanceContract(unittest.TestCase):

    def test_asymmetric(self):
        self.assertEqual(decode_network_word(b'\x12\x34'), 4660)

    def test_high_byte(self):
        self.assertEqual(decode_network_word(b'\x80\x00'), 32768)

    def test_low_byte(self):
        self.assertEqual(decode_network_word(b'\x00\xff'), 255)

    def test_zero(self):
        self.assertEqual(decode_network_word(b'\x00\x00'), 0)

    def test_maximum(self):
        self.assertEqual(decode_network_word(b'\xff\xff'), 65535)

    def test_short(self):
        with self.assertRaises(ValueError):
            decode_network_word(b'\x01')

    def test_long(self):
        with self.assertRaises(ValueError):
            decode_network_word(b'\x00\x01\x02')

    def test_type(self):
        with self.assertRaises(ValueError):
            decode_network_word([1, 2])


if __name__ == '__main__':
    unittest.main()
