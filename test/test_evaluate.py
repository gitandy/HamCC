import unittest

from hamcc import hamcc


class TestCaseEvaluate(unittest.TestCase):
    def setUp(self):
        self.cc = hamcc.CassiopeiaConsole('XX1XXX', 'AA11aa', 'Tester')

    def test_10_band(self):
        self.assertEqual('', self.cc.evaluate('20m'))
        self.assertEqual('20m', self.cc.current_qso['BAND'])

        self.assertEqual('', self.cc.evaluate('40M'))
        self.assertEqual('40m', self.cc.current_qso['BAND'])

        self.assertEqual('', self.cc.evaluate('8'))
        self.assertEqual('80m', self.cc.current_qso['BAND'])

        self.assertEqual('', self.cc.evaluate('-4'))
        self.assertEqual('4m', self.cc.current_qso['BAND'])


if __name__ == '__main__':
    unittest.main()
