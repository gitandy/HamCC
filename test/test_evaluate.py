import unittest

from hamcc import hamcc


class TestCaseEvaluate(unittest.TestCase):
    def setUp(self):
        self.cc = hamcc.CassiopeiaConsole('XX1XXX', 'AA11aa', 'Tester')

    def test_010_band(self):
        self.assertEqual('', self.cc.evaluate('20m'))
        self.assertEqual('20m', self.cc.current_qso['BAND'])

        self.assertEqual('', self.cc.evaluate('40M'))
        self.assertEqual('40m', self.cc.current_qso['BAND'])

        # Test shortcuts
        self.assertEqual('', self.cc.evaluate('8'))
        self.assertEqual('80m', self.cc.current_qso['BAND'])

        self.assertEqual('', self.cc.evaluate('-4'))
        self.assertEqual('4m', self.cc.current_qso['BAND'])

    def test_020_numeric(self):
        self.assertEqual('Error: Unknown number format', self.cc.evaluate('1o'))

        self.assertEqual('', self.cc.evaluate('12p'))
        self.assertEqual('12', self.cc.current_qso['TX_POWER'])

        self.assertEqual('', self.cc.evaluate('14312f'))
        self.assertEqual('14.312', self.cc.current_qso['FREQ'])
        self.assertEqual('', self.cc.evaluate('145312.5f'))
        self.assertEqual('145.3125', self.cc.current_qso['FREQ'])

    def test_022_numeric_time(self):
        self.assertEqual('Error: Wrong time format', self.cc.evaluate('1t'))
        self.assertEqual('Error: Wrong time format', self.cc.evaluate('123t'))
        self.assertEqual('Error: Wrong time format', self.cc.evaluate('2400t'))
        self.assertEqual('Error: Wrong time format', self.cc.evaluate('0060t'))
        self.assertEqual('', self.cc.evaluate('0000t'))
        self.assertEqual('0000', self.cc.current_qso['TIME_ON'])
        self.assertEqual('', self.cc.evaluate('2359t'))
        self.assertEqual('2359', self.cc.current_qso['TIME_ON'])
        self.assertEqual('', self.cc.evaluate('1234t'))
        self.assertEqual('1234', self.cc.current_qso['TIME_ON'])

        # Test shortcut
        self.assertEqual('', self.cc.evaluate('45t'))
        self.assertEqual('1245', self.cc.current_qso['TIME_ON'])

    def test_024_numeric_date(self):
        self.assertEqual('Error: Wrong date format', self.cc.evaluate('1d'))
        self.assertEqual('Error: Wrong date format', self.cc.evaluate('123d'))
        self.assertEqual('Error: Wrong date format', self.cc.evaluate('12345d'))
        self.assertEqual('Error: Wrong date format', self.cc.evaluate('1234567d'))
        self.assertEqual('Error: Wrong date format', self.cc.evaluate('00000101d'))
        self.assertEqual('Error: Wrong date format', self.cc.evaluate('20000001d'))
        self.assertEqual('Error: Wrong date format', self.cc.evaluate('20001301d'))
        self.assertEqual('Error: Wrong date format', self.cc.evaluate('20000100d'))
        self.assertEqual('Error: Wrong date format', self.cc.evaluate('20000132d'))

        self.assertEqual('', self.cc.evaluate('10000101d'))
        self.assertEqual('10000101', self.cc.current_qso['QSO_DATE'])
        self.assertEqual('', self.cc.evaluate('99991231d'))
        self.assertEqual('99991231', self.cc.current_qso['QSO_DATE'])
        self.assertEqual('', self.cc.evaluate('20210813d'))

        # Test shortcuts
        self.assertEqual('20210813', self.cc.current_qso['QSO_DATE'])
        self.assertEqual('', self.cc.evaluate('220914d'))
        self.assertEqual('20220914', self.cc.current_qso['QSO_DATE'])
        self.assertEqual('', self.cc.evaluate('1015d'))
        self.assertEqual('20221015', self.cc.current_qso['QSO_DATE'])
        self.assertEqual('', self.cc.evaluate('16d'))
        self.assertEqual('20221016', self.cc.current_qso['QSO_DATE'])

    def test_030_mode(self):
        self.assertEqual('', self.cc.evaluate('SSB'))
        self.assertEqual('SSB', self.cc.current_qso['MODE'])

        self.assertEqual('', self.cc.evaluate('am'))
        self.assertEqual('AM', self.cc.current_qso['MODE'])

        # Test shortcuts
        self.assertEqual('', self.cc.evaluate('m'))
        self.assertEqual('MFSK', self.cc.current_qso['MODE'])

        self.assertEqual('', self.cc.evaluate('F'))
        self.assertEqual('FM', self.cc.current_qso['MODE'])

        self.assertEqual('', self.cc.evaluate('ssb'))
        self.assertEqual('59', self.cc.current_qso['RST_RCVD'])
        self.assertEqual('59', self.cc.current_qso['RST_SENT'])
        self.assertEqual('', self.cc.evaluate('cw'))
        self.assertEqual('599', self.cc.current_qso['RST_RCVD'])
        self.assertEqual('599', self.cc.current_qso['RST_SENT'])

    def test_040_comment(self):
        self.assertEqual('', self.cc.evaluate('#Comment'))
        self.assertEqual('Comment', self.cc.current_qso['COMMENT'])

    def test_050_name(self):
        self.assertEqual('', self.cc.evaluate('\'Name'))
        self.assertEqual('Name', self.cc.current_qso['NAME'])

    def test_060_locator(self):
        self.assertEqual('', self.cc.evaluate('@Test(AA11aa)'))
        self.assertEqual('AA11aa', self.cc.current_qso['GRIDSQUARE'])
        self.assertEqual('Test', self.cc.current_qso['QTH'])

        self.assertEqual('', self.cc.evaluate('@AA11aa'))
        self.assertEqual('AA11aa', self.cc.current_qso['GRIDSQUARE'])
        self.assertNotIn('QTH', self.cc.current_qso)

        self.assertEqual('Error: Wrong QTH/maidenhead format', self.cc.evaluate('@ZZ11aa'))
        self.assertEqual('AA11aa', self.cc.current_qso['GRIDSQUARE'])
        self.assertEqual('Error: Wrong QTH/maidenhead format', self.cc.evaluate('@TestAA22aa)'))
        self.assertEqual('AA11aa', self.cc.current_qso['GRIDSQUARE'])

    @unittest.expectedFailure
    def test_070_contest(self):
        self.fail('Test missing')

    def test_090_rst(self):
        self.assertEqual('', self.cc.evaluate('.44'))
        self.assertEqual('', self.cc.evaluate(',55'))
        self.assertEqual('44', self.cc.current_qso['RST_RCVD'])
        self.assertEqual('55', self.cc.current_qso['RST_SENT'])

        self.assertEqual('Error: Wrong RST format', self.cc.evaluate('.94'))
        self.assertEqual('44', self.cc.current_qso['RST_RCVD'])
        self.assertEqual('Error: Wrong RST format', self.cc.evaluate(',75'))
        self.assertEqual('55', self.cc.current_qso['RST_SENT'])

    def test_100_qsl(self):
        self.assertNotIn('QSL_RCVD', self.cc.current_qso)

        self.assertEqual('', self.cc.evaluate('*'))
        self.assertEqual('Y', self.cc.current_qso['QSL_RCVD'])

        self.assertEqual('', self.cc.evaluate('*'))
        self.assertEqual('N', self.cc.current_qso['QSL_RCVD'])

        self.assertEqual('', self.cc.evaluate('*'))
        self.assertEqual('Y', self.cc.current_qso['QSL_RCVD'])

    def test_110_autotime(self):
        self.assertEqual('', self.cc.evaluate('0000t'))
        self.assertEqual('0000', self.cc.current_qso['TIME_ON'])
        self.assertEqual('', self.cc.evaluate('20000101d'))
        self.assertEqual('20000101', self.cc.current_qso['QSO_DATE'])

        self.assertEqual('', self.cc.evaluate('='))
        self.assertNotEqual('0000', self.cc.current_qso['TIME_ON'])
        self.assertRegex(self.cc.current_qso['TIME_ON'],
                         r'(([0-1][0-9])|(2[0-3]))([0-5][0-9])')
        self.assertNotEqual('20000101', self.cc.current_qso['QSO_DATE'])
        self.assertRegex(self.cc.current_qso['QSO_DATE'],
                         r'([1-9][0-9]{3})((0[1-9])|(1[0-2]))((0[1-9])|([1-2][0-9])|(3[0-2]))')

    def test_120_extended_c(self):
        self.assertEqual('', self.cc.evaluate('-cBB1BBB'))
        self.assertEqual('BB1BBB', self.cc.current_qso['STATION_CALLSIGN'])

        self.assertEqual('Error: Wrong call format', self.cc.evaluate('-cBB1BBB1'))
        self.assertEqual('BB1BBB', self.cc.current_qso['STATION_CALLSIGN'])

    def test_122_extended_l(self):
        self.assertEqual('', self.cc.evaluate('-lCheck(BB22bb)'))
        self.assertEqual('BB22bb', self.cc.current_qso['MY_GRIDSQUARE'])
        self.assertEqual('Check', self.cc.current_qso['MY_CITY'])

        self.assertEqual('', self.cc.evaluate('-lBB22bb'))
        self.assertEqual('BB22bb', self.cc.current_qso['MY_GRIDSQUARE'])
        self.assertNotIn('MY_CITY', self.cc.current_qso)

        self.assertEqual('Error: Wrong QTH/maidenhead format', self.cc.evaluate('-lZZ11aa'))
        self.assertEqual('BB22bb', self.cc.current_qso['MY_GRIDSQUARE'])
        self.assertEqual('Error: Wrong QTH/maidenhead format', self.cc.evaluate('-lTestAA22aa)'))
        self.assertEqual('BB22bb', self.cc.current_qso['MY_GRIDSQUARE'])

    def test_124_extended_n(self):
        self.assertEqual('', self.cc.evaluate('-nTestuser'))
        self.assertEqual('Testuser', self.cc.current_qso['MY_NAME'])
        self.assertEqual('', self.cc.evaluate('-nTest_User'))
        self.assertEqual('Test User', self.cc.current_qso['MY_NAME'])

    @unittest.expectedFailure
    def test_126_extended_N(self):
        self.fail('Test missing')

    def test_126_extended_V(self):
        self.assertIn('HamCC: ', self.cc.evaluate('-V'))

    def test_130_call(self):
        self.assertEqual('', self.cc.evaluate('AA1AAA'))
        self.assertEqual('AA1AAA', self.cc.current_qso['CALL'])

        self.assertEqual('Error: Wrong call format', self.cc.evaluate('AA1AAA1'))
        self.assertEqual('AA1AAA', self.cc.current_qso['CALL'])

        self.assertEqual('Last QSO cached: AA1AAA', self.cc.finalize_qso())
        self.assertIn('AA1AAA worked on', self.cc.evaluate('AA1AAA'))


if __name__ == '__main__':
    unittest.main()
