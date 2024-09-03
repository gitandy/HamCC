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


if __name__ == '__main__':
    unittest.main()
