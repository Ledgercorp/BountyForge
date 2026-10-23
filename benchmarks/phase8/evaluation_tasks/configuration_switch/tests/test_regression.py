import unittest

from subject import parse_switch


class MaintenanceContract(unittest.TestCase):

    def test_false_forms(self):
        self.assertEqual([parse_switch(value) for value in ('false', 'no', 'off', '0')], [False] * 4)

    def test_true_forms(self):
        self.assertEqual([parse_switch(value) for value in ('true', 'yes', 'on', '1')], [True] * 4)

    def test_booleans(self):
        self.assertIs(parse_switch(False), False)
        self.assertIs(parse_switch(True), True)

    def test_case_space(self):
        self.assertIs(parse_switch(' OFF '), False)

    def test_empty(self):
        self.assertIs(parse_switch(''), False)

    def test_unknown(self):
        with self.assertRaises(ValueError):
            parse_switch('maybe')

    def test_number(self):
        with self.assertRaises(ValueError):
            parse_switch(1)


if __name__ == '__main__':
    unittest.main()
