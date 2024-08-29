import unittest

from hamcc import hamcc


class TestCaseAppendChar(unittest.TestCase):
    def setUp(self):
        self.cc = hamcc.CassiopeiaConsole('XX1XXX', 'AA11aa', 'Tester')

    def insert_sequence(self, seq):
        for c in seq:
            self.cc.append_char(c)

    def test_10_simple_sp(self):
        self.insert_sequence('YY1YYY')
        self.assertEqual('', self.cc.append_char(' '))
        self.assertEqual('YY1YYY', self.cc.current_qso['CALL'])  # add assertion here

        self.insert_sequence('\'Test')
        self.assertEqual('', self.cc.append_char(' '))
        self.assertEqual('Test', self.cc.current_qso['NAME'])  # add assertion here

    def test_15_simple_lf(self):
        self.insert_sequence('\'Test')
        self.assertEqual('', self.cc.append_char('\n'))
        self.assertEqual('Test', self.cc.qsos[0]['NAME'])  # add assertion here

    def test_20_quoted(self):
        self.insert_sequence('"\'Test Tester"')
        self.assertEqual('Test Tester', self.cc.current_qso['NAME'])  # add assertion here

    def test_25_quoted_lf(self):
        self.insert_sequence('"#Long Comment\n')
        self.assertEqual('Long Comment', self.cc.qsos[0]['COMMENT'])  # add assertion here

    def test_30_simple_sp_lf(self):
        self.insert_sequence('YY1YYY')
        self.assertEqual('', self.cc.append_char(' '))
        self.assertEqual('', self.cc.append_char('\n'))
        self.assertEqual('YY1YYY', self.cc.qsos[0]['CALL'])  # add assertion here

    def test_40_clear(self):
        self.test_10_simple_sp()
        self.cc.clear()
        self.assertEqual('', self.cc.current_qso['CALL'])
        self.assertNotIn('NAME', self.cc.current_qso)


if __name__ == '__main__':
    unittest.main()
