import unittest

from hamcc import hamcc


class TestCaseEvaluateEvent(unittest.TestCase):
    def setUp(self):
        self.cc = hamcc.CassiopeiaConsole('XX1XXX', 'AA11aa', 'Tester')

    def test_010_contest_nr(self):
        # New contest
        self.assertEqual('', self.cc.evaluate('$TESTCONTEST'))
        self.assertEqual('TESTCONTEST', self.cc.current_qso['CONTEST_ID'])
        self.assertEqual('001', self.cc.current_qso['STX'])
        self.assertEqual('001', self.cc.current_qso['STX_STRING'])

        # Set rcvd exch
        self.assertEqual('', self.cc.evaluate('%991'))
        self.assertEqual('991', self.cc.current_qso['SRX'])
        self.assertEqual('991', self.cc.current_qso['SRX_STRING'])

        # Push QSO and check auto number and cleared sent exch
        self.assertEqual('Warning: Callsign missing for last QSO', self.cc.finalize_qso())
        self.assertEqual('002', self.cc.current_qso['STX'])
        self.assertEqual('002', self.cc.current_qso['STX_STRING'])
        self.assertNotIn('SRX', self.cc.current_qso)
        self.assertNotIn('SRX_STRING', self.cc.current_qso)

    def test_020_contest_setnr(self):
        # New contest
        self.assertEqual('', self.cc.evaluate('$TESTCONTEST'))
        self.assertEqual('TESTCONTEST', self.cc.current_qso['CONTEST_ID'])
        self.assertEqual('001', self.cc.current_qso['STX'])
        self.assertEqual('001', self.cc.current_qso['STX_STRING'])

        # Set another start number
        self.assertEqual('', self.cc.evaluate('-N222'))
        self.assertEqual('222', self.cc.current_qso['STX'])
        self.assertEqual('222', self.cc.current_qso['STX_STRING'])

        # Push QSO and check auto number
        self.assertEqual('Warning: Callsign missing for last QSO', self.cc.finalize_qso())
        self.assertEqual('223', self.cc.current_qso['STX'])
        self.assertEqual('223', self.cc.current_qso['STX_STRING'])

    def test_030_contest_str(self):
        # New contest
        self.assertEqual('', self.cc.evaluate('$TESTCONTEST'))
        self.assertEqual('TESTCONTEST', self.cc.current_qso['CONTEST_ID'])

        # Set non number exchanges
        self.assertEqual('', self.cc.evaluate('-Nxx11'))
        self.assertNotIn('STX', self.cc.current_qso)
        self.assertEqual('XX11', self.cc.current_qso['STX_STRING'])
        self.assertEqual('', self.cc.evaluate('%yy22'))
        self.assertNotIn('SRX', self.cc.current_qso)
        self.assertEqual('YY22', self.cc.current_qso['SRX_STRING'])

        # Push QSO and check reuse non number and cleared sent exch
        self.assertEqual('Warning: Callsign missing for last QSO', self.cc.finalize_qso())
        self.assertNotIn('STX', self.cc.current_qso)
        self.assertEqual('XX11', self.cc.current_qso['STX_STRING'])
        self.assertNotIn('SRX', self.cc.current_qso)
        self.assertNotIn('SRX_STRING', self.cc.current_qso)

    def test_030_no_contest(self):
        self.assertEqual('Error: No active event', self.cc.evaluate('-N333'))
        self.assertNotIn('STX', self.cc.current_qso)
        self.assertNotIn('STX_STRING', self.cc.current_qso)
        self.assertEqual('Error: No active event', self.cc.evaluate('%444'))
        self.assertNotIn('SRX', self.cc.current_qso)
        self.assertNotIn('SRX_STRING', self.cc.current_qso)


if __name__ == '__main__':
    unittest.main()