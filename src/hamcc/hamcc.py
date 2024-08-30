"""Provide an API for logging Ham Radio QSOs via text input"""

import os
import re
import json
from copy import deepcopy
import datetime

from . import __proj_name__, __version_str__


def __read_json__(file) -> list:
    try:
        with open(os.path.join(os.path.dirname(__file__), file)) as jf:
            return json.load(jf)
    except OSError:
        return []


BANDS = __read_json__('data/bands.json')
MODES = __read_json__('data/modes.json')


class CassiopeiaConsole:
    # These are some hostilog compatible definitions
    # Credits to Peter, DF1LX the author of hostilog which inspired me to write hamcc
    BANDS_HOSTI = {
        '0': '160m',
        '1': '10m',
        '2': '20m',
        '3': '30m',
        '4': '40m',
        '5': '15m',
        '6': '12m',
        '7': '17m',
        '8': '80m',
        '9': '60m',
        '-2': '2m',
        '-4': '4m',
        '-5': '6m',
        '-6': '60m',
        '-7': '70cm',
    }
    MODES_HOSTI = {
        'S': 'SSB',
        'C': 'CW',
        'R': 'RTTY',
        'A': 'AMTOR',
        'D': 'MFSK',  # ADIF compatible mode name
        'F': 'FM',
        'H': 'HELL',
        'J': 'JT65',
        'P': 'PSK',
        'T': 'FT8',
        # Extension
        'M': 'MFSK',
        'DV': 'DIGITALVOICE',
    }

    REGEX_TIME = re.compile(r'(([0-1][0-9])|(2[0-3]))([0-5][0-9])')
    REGEX_DATE = re.compile(r'([1-9][0-9]{3})((0[1-9])|(1[0-2]))((0[1-9])|([1-2][0-9])|(3[0-1]))')
    REGEX_CALL = re.compile(
        r'([a-zA-Z0-9]{1,3}?/)?([a-zA-Z0-9]{1,3}?[0-9][a-zA-Z0-9]{0,3}?[a-zA-Z])(/[aAmMpPrRtT]{1,2}?)?')
    REGEX_RSTFIELD = re.compile(r'([1-5][1-9][1-9aAcCkKmMsSxX]?)|([-+][0-9]{1,2})')
    REGEX_LOCATOR = re.compile(r'[a-rA-R]{2}[0-9]{2}([a-xA-X]{2}([0-9]{2})?)?')

    def __init__(self, my_call: str, my_loc: str, my_name: str = ''):
        if my_call and not self.check_format(self.REGEX_CALL, my_call):
            raise Exception('Wrong call format')
        self.__my_call__ = my_call

        if my_loc and not self.check_format(self.REGEX_LOCATOR, my_loc):
            raise Exception('Wrong locator format')
        self.__my_loc__ = my_loc

        self.__my_name__ = my_name

        self.__qsos__: list[dict] = []

        # Mandatory
        self.__date__ = datetime.datetime.utcnow().strftime('%Y%m%d')
        self.__time__ = datetime.datetime.utcnow().strftime('%H%M')
        self.__band__ = ''
        self.__mode__ = ''

        # Optional
        self.__freq__ = ''
        self.__pwr__ = ''

        # Special
        self.__contest_id__ = ''
        self.__cntstqso_id__ = 0

        self.__edit_pos__ = -1
        self.__cur_seq__ = ''
        self.__long_mode__ = False

        self.__cur_qso__ = {}
        self.__qso_active__ = False
        self.clear()

    def append_char(self, char: str) -> str:
        """Append a char to the sequence stack
        :return: the result of evaluation or other actions"""

        if len(char) != 1:
            raise Exception('More or less than one character')

        if self.__long_mode__:
            if char in ('"', '\n'):
                if char == '\n':
                    res = self.finalize_qso()
                else:
                    res = self.evaluate(self.__cur_seq__)
                    self.__cur_seq__ = ''
                    self.__long_mode__ = False
                return res
            else:
                self.__cur_seq__ += char
        elif char == ' ':
            res = self.evaluate(self.__cur_seq__)
            self.__cur_seq__ = ''
            return res
        elif char == '"':
            self.__long_mode__ = True
        elif char == '\n':
            res = self.finalize_qso()
            return res
        elif char == '~':
            self.__cur_seq__ = ''
            self.clear()
        elif char == '?':
            return str(self.current_qso)
        else:
            self.__cur_seq__ += char

        return ''

    @staticmethod
    def check_format(exp: re.Pattern, txt: str) -> bool:
        """Test the given text against a regular expression
        :param exp: a compiled pattern
        :param txt: a text
        :return: True if pattern matches"""
        return bool(re.fullmatch(exp, txt))

    def clear(self):
        """Clear current QSO (input cache)"""

        self.__edit_pos__ = -1
        self.__qso_active__ = False
        self.__long_mode__ = False

        # Mandatory
        self.__cur_qso__ = {'STATION_CALLSIGN': self.__my_call__,
                            'MY_GRIDSQUARE': self.__my_loc__,
                            'QSO_DATE': self.__date__,
                            'TIME_ON': self.__time__,
                            'BAND': self.__band__,
                            'MODE': self.__mode__,
                            'CALL': '',
                            'GRIDSQUARE': '',
                            }

        self.set_rst_default(self.__mode__)

        # Optional
        if self.__my_name__:
            self.__cur_qso__['MY_NAME'] = self.__my_name__
        if self.__pwr__:
            self.__cur_qso__['TX_PWR'] = self.__pwr__
        if self.__freq__:
            self.__cur_qso__['FREQ'] = self.__freq__

    def reset(self):
        """Reset whole session"""

        self.__cur_seq__ = ''
        self.__qsos__ = []
        self.__long_mode__ = False

        # Mandatory
        self.__band__ = ''
        self.__mode__ = ''

        # Optional
        self.__freq__ = ''
        self.__pwr__ = ''

        # Special
        self.__contest_id__ = ''
        self.__cntstqso_id__ = 0

        self.clear()

    def finalize_qso(self) -> str:
        """Append the current QSO to the QSO stack and prepare for the next one
        :return: the result of evaluation"""

        res = self.evaluate(self.__cur_seq__)
        self.__cur_seq__ = ''
        self.__long_mode__ = False

        if self.__qso_active__:
            qso = deepcopy(self.__cur_qso__)

            if self.__edit_pos__ == -1:
                self.__qsos__.append(qso)
            else:
                self.__qsos__[self.__edit_pos__] = self.__cur_qso__

            self.clear()
            if self.__contest_id__:
                self.__cur_qso__['CONTEST_ID'] = self.__contest_id__
                self.__cntstqso_id__ += 1
                self.__cur_qso__['STX'] = str(self.__cntstqso_id__)

        return res

    @property
    def qsos(self) -> list[dict]:
        """Return the list of QSOs"""
        return self.__qsos__

    @property
    def current_qso(self) -> dict:
        """Return the current QSO"""
        return self.__cur_qso__

    def has_qsos(self) -> bool:
        """Test if QSOs are available in the QSO stack"""
        return bool(self.__qsos__)

    def pop_qso(self, __index=0) -> dict:
        """Remove a QSO from the stack and return it
        :param __index: the index of the QSO to remove from stack (default: first)
        :return: a QSO"""
        self.clear()
        return self.__qsos__.pop(__index)

    @property
    def edit_pos(self):
        return self.__edit_pos__

    def load_prev(self):
        if self.qsos:
            if self.__edit_pos__ in (-1, 0):
                self.__edit_pos__ = len(self.qsos) - 1
            else:
                self.__edit_pos__ -= 1

            self.__cur_qso__ = self.__qsos__[self.__edit_pos__]

    def load_next(self):
        if self.qsos:
            if self.__edit_pos__ in (-1, len(self.qsos) - 1):
                self.__edit_pos__ = 0
            else:
                self.__edit_pos__ += 1

            self.__cur_qso__ = self.__qsos__[self.__edit_pos__]

    def del_selected(self) -> int:
        if self.__edit_pos__ != -1:
            del_pos = self.__edit_pos__
            self.pop_qso(self.__edit_pos__)
            return del_pos

        return -1

    def evaluate_numeric(self, seq: str) -> str:
        if seq.endswith('d'):
            d = seq[:-1]
            if len(d) == 6:  # fill to last century
                d = self.__date__[:2] + d
            elif len(d) == 4:  # fill to last year
                d = self.__date__[:4] + d
            elif len(d) == 2:  # fill to last year and month
                d = self.__date__[:6] + d
            if not self.check_format(self.REGEX_DATE, d):
                return 'Wrong date format'
            self.__date__ = d
            self.__cur_qso__['QSO_DATE'] = d
        elif seq.endswith('t'):
            t = seq[:-1]
            if len(t) == 2:  # if only minutes are given fill hour with old time
                t = self.__time__[:2] + t
            if not self.check_format(self.REGEX_TIME, t):
                return 'Wrong time format'
            self.__time__ = t
            self.__cur_qso__['TIME_ON'] = self.__time__
        elif seq.endswith('f'):
            self.__freq__ = seq[:-1]
            self.__cur_qso__['FREQ'] = self.__freq__
        elif seq.endswith('p'):
            self.__pwr__ = seq[:-1]
            self.__cur_qso__['TX_POWER'] = self.__pwr__
        else:
            return 'Unknown number format'
        return ''

    def set_rst_default(self, mode):
        rst = ''
        if mode in ('CW',):
            rst = '599'
        elif mode in ('AM', 'FM', 'SSB', 'DIGITALVOICE'):
            rst = '59'

        if rst:
            self.__cur_qso__['RST_RCVD'] = rst
            self.__cur_qso__['RST_SENT'] = rst
        else:
            if 'RST_RCVD' in self.__cur_qso__:
                self.__cur_qso__.pop('RST_RCVD')
            if 'RST_SENT' in self.__cur_qso__:
                self.__cur_qso__.pop('RST_SENT')

    @staticmethod
    def isnumeric(number: str) -> bool:
        for d in number:
            if d not in '-0123456789':
                return False

        return True

    # flake8: noqa: C901
    def evaluate(self, seq: str) -> str:
        if seq:
            self.__qso_active__ = True

            if seq.lower().endswith('m') and seq.lower() in BANDS:
                self.__band__ = seq.lower()
                self.__cur_qso__['BAND'] = self.__band__
            elif self.isnumeric(seq) and 0 < len(seq) < 3:
                if seq in self.BANDS_HOSTI:
                    self.__band__ = self.BANDS_HOSTI[seq.lower()]
                    self.__cur_qso__['BAND'] = self.__band__
            elif seq[:-1].isnumeric():
                return self.evaluate_numeric(seq)
            elif seq.upper() in MODES:
                self.__mode__ = seq.upper()
                self.__cur_qso__['MODE'] = self.__mode__
                self.set_rst_default(self.__mode__)
            elif seq.upper() in self.MODES_HOSTI:
                self.__mode__ = self.MODES_HOSTI[seq.upper()]
                self.__cur_qso__['MODE'] = self.__mode__
                self.set_rst_default(self.__mode__)
            elif seq.startswith('#'):  # Comment
                self.__cur_qso__['COMMENT'] = seq[1:].replace('_', ' ')
            elif seq.startswith('\''):  # Name
                self.__cur_qso__['NAME'] = seq[1:].replace('_', ' ')
            elif seq.startswith('@'):  # Locator
                if not self.check_format(self.REGEX_LOCATOR, seq[1:]):
                    return 'Wrong maidenhead format'
                self.__cur_qso__['GRIDSQUARE'] = seq[1:3].upper() + seq[3:]
            elif seq.startswith('$'):  # Contest ID
                if len(seq) > 1:
                    if self.__contest_id__:  # Reset QSO ID for new contest
                        self.__cntstqso_id__ = 1
                    self.__contest_id__ = seq[1:].upper()
                    self.__cur_qso__['CONTEST_ID'] = self.__contest_id__
                    self.__cur_qso__['STX'] = str(self.__cntstqso_id__)
                else:
                    self.__contest_id__ = ''
                    if 'CONTEST_ID' in self.__cur_qso__:
                        self.__cur_qso__.pop('CONTEST_ID')
                    self.__cntstqso_id__ = 0
            elif seq.startswith('%'):  # Contest received QSO id
                if not self.__contest_id__:
                    return 'No active contest'
                self.__cur_qso__['SRX'] = seq[1:]
            elif seq[0] in '.,':  # RST
                if not self.check_format(self.REGEX_RSTFIELD, seq[1:]):
                    return 'Wrong RST format'
                if seq[0] == '.':
                    self.__cur_qso__['RST_RCVD'] = seq[1:].upper()
                else:
                    self.__cur_qso__['RST_SENT'] = seq[1:].upper()
            elif seq == '*':  # Toggle QSL received
                if 'QSL_RCVD' in self.__cur_qso__ and self.__cur_qso__['QSL_RCVD'] == 'Y':
                    self.__cur_qso__['QSL_RCVD'] = 'N'
                else:
                    self.__cur_qso__['QSL_RCVD'] = 'Y'
            elif seq == '=':  # Sync date/time to now
                self.__date__ = datetime.datetime.utcnow().strftime('%Y%m%d')
                self.__time__ = datetime.datetime.utcnow().strftime('%H%M')
                self.__cur_qso__['QSO_DATE'] = self.__date__
                self.__cur_qso__['TIME_ON'] = self.__time__
            elif seq[0] == '-':  # different extended infos
                if seq.startswith('-c'):
                    if not self.check_format(self.REGEX_CALL, seq[2:]):
                        return 'Wrong call format'
                    self.__my_call__ = seq[2:]
                    self.__cur_qso__['STATION_CALLSIGN'] = self.__my_call__
                elif seq.startswith('-l'):
                    if not self.check_format(self.REGEX_LOCATOR, seq[2:]):
                        return 'Wrong maidenhead format'
                    self.__my_loc__ = seq[2:]
                    self.__cur_qso__['MY_GRIDSQUARE'] = self.__my_loc__
                elif seq.startswith('-n'):
                    self.__my_name__ = seq[2:].replace('_', ' ')
                    self.__cur_qso__['MY_NAME'] = self.__my_name__
                elif seq == '-V':
                    return f'{__proj_name__}: {__version_str__}'
            else:  # Call
                if not self.check_format(self.REGEX_CALL, seq):
                    return 'Wrong call format'
                self.__cur_qso__['CALL'] = seq.upper()

        return ''
