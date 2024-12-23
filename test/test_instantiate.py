import unittest

from hamcc import hamcc


class TestCaseInstantiate(unittest.TestCase):
    def test_10_ok(self):
        cc = hamcc.CassiopeiaConsole('XX1XXX', 'AA11aa', 'Tester')

        self.assertEqual('XX1XXX', cc.current_qso['STATION_CALLSIGN'])
        self.assertEqual('AA11aa', cc.current_qso['MY_GRIDSQUARE'])
        self.assertEqual('Tester', cc.current_qso['MY_NAME'])

    def test_20_exception(self):
        self.assertRaises(Exception, hamcc.CassiopeiaConsole, 'XX1XXX222', 'AA11aa')
        self.assertRaises(Exception, hamcc.CassiopeiaConsole, 'XX1XXX', 'AA11zz')

    def test_30_init_qso(self):
        init_qso = {
            'STATION_CALLSIGN': 'XX1XXX',
            'MY_GRIDSQUARE': 'AA11aa',
            'QSO_DATE': '20241122',
            'TIME_ON': '2233',
            'BAND': '2M',
            'MODE': 'SSB',
            'CALL': '1Y1YY',
            'GRIDSQUARE': 'BB22bb',
            'MY_NAME': 'Tester',
            'COMMENT': 'Test Comment',
            'FREQ': '123456',
            'TX_PWR': '23',
            'NAME': 'Nobody',
        }

        init_res = {
            'STATION_CALLSIGN': 'XX1XXX',
            'MY_GRIDSQUARE': 'AA11aa',
            'QSO_DATE': '20241122',
            'TIME_ON': '2233',
            'BAND': '2M',
            'MODE': 'SSB',
            'CALL': '',
            'GRIDSQUARE': '',
            'MY_NAME': 'Tester',
            'COMMENT': 'Test Comment',
            'RST_RCVD': '59',
            'RST_SENT': '59',
            'FREQ': '123456',
            'TX_PWR': '23',
        }

        cc = hamcc.CassiopeiaConsole('XX1XXX', 'AA11aa', 'Tester',
                                     init_qso=init_qso)

        self.assertDictEqual(init_res, cc.current_qso)

    def test_40_qso(self):
        qso = [
            '20241122d',
            '2233t',
            '2m',
            's',
            '1Y1YY',
            '@BB22bb',
            '#Test_Comment',
            '123456f',
            '23p',
            '\'Nobody',
        ]

        qso_res = {
            'STATION_CALLSIGN': 'XX1XXX',
            'MY_GRIDSQUARE': 'AA11aa',
            'QSO_DATE': '20241122',
            'TIME_ON': '2233',
            'BAND': '2m',
            'MODE': 'SSB',
            'CALL': '1Y1YY',
            'NAME': 'Nobody',
            'GRIDSQUARE': 'BB22bb',
            'MY_NAME': 'Tester',
            'COMMENT': 'Test Comment',
            'RST_RCVD': '59',
            'RST_SENT': '59',
            'FREQ': '123.456',
            'TX_PWR': '23',
        }

        new_qso = {
            'STATION_CALLSIGN': 'XX1XXX',
            'MY_GRIDSQUARE': 'AA11aa',
            'QSO_DATE': '20241122',
            'TIME_ON': '2233',
            'BAND': '2m',
            'MODE': 'SSB',
            'CALL': '',
            'GRIDSQUARE': '',
            'MY_NAME': 'Tester',
            'COMMENT': 'Test Comment',
            'RST_RCVD': '59',
            'RST_SENT': '59',
            'FREQ': '123.456',
            'TX_PWR': '23',
        }

        cc = hamcc.CassiopeiaConsole('XX1XXX', 'AA11aa', 'Tester')

        for e in qso:
            self.assertEqual('', cc.evaluate(e))

        self.assertDictEqual(qso_res, cc.current_qso)
        self.assertIn('Last QSO cached: 1Y1YY', cc.append_char('\n'))

        self.assertDictEqual(new_qso, cc.current_qso)


if __name__ == '__main__':
    unittest.main()
