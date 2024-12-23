"""Provide an API for logging Ham Radio QSOs via text input"""

import os
import re
import json
from copy import deepcopy
import datetime
import logging

from . import __proj_name__, __version_str__

logger = logging.getLogger(__name__)


def __read_json__(file) -> list:
    try:
        logger.debug(f'Reading JSON data "{file}"...')
        with open(os.path.join(os.path.dirname(__file__), file)) as jf:
            return json.load(jf)
    except OSError:
        return []


BANDS = __read_json__('data/bands.json')
MODES = __read_json__('data/modes.json')


def adif_date2iso(date: str) -> str | None:
    if not date or len(date) != 8:
        return
    return date[:4] + '-' + date[4:6] + '-' + date[6:8]


def adif_time2iso(time: str) -> str | None:
    if not time or len(time) != 4:
        return
    return time[:2] + ':' + time[2:4]


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

    QSO_REQ_FIELDS = ['STATION_CALLSIGN',
                      'MY_GRIDSQUARE',
                      'QSO_DATE',
                      'TIME_ON',
                      'BAND',
                      'MODE',
                      'CALL',
                      'GRIDSQUARE',
                      ]

    REGEX_TIME = re.compile(r'(([0-1][0-9])|(2[0-3]))([0-5][0-9])')
    REGEX_DATE = re.compile(r'([1-9][0-9]{3})((0[1-9])|(1[0-2]))((0[1-9])|([1-2][0-9])|(3[0-1]))')
    REGEX_CALL = re.compile(
        r'([a-zA-Z0-9]{1,3}?/)?([a-zA-Z0-9]{1,3}?[0-9][a-zA-Z0-9]{0,3}?[a-zA-Z])(/[aAmMpPrRtT]{1,2}?)?')
    REGEX_RSTFIELD = re.compile(r'([1-5]([1-9]([1-9][aAcCkKmMsSxX]?)?)?)|([-+][0-9]{1,2})')
    REGEX_LOCATOR = re.compile(r'[a-rA-R]{2}[0-9]{2}([a-xA-X]{2}([0-9]{2})?)?')
    REGEX_QTH = re.compile(r'(.*?)? *\(([a-rA-R]{2}[0-9]{2}([a-xA-X]{2}([0-9]{2})?)?)\)')

    def __init__(self, my_call: str = '', my_loc: str = '', my_name: str = '',
                 event: str = '', event_ref: int = 1,
                 init_qso: dict[str, str] = None, init_worked: dict[str, tuple[str, str]] = None):
        logger.debug('Initialising...')
        if my_call and not self.check_format(self.REGEX_CALL, my_call):
            raise Exception('Wrong call format')
        self.__my_call__ = init_qso['STATION_CALLSIGN'] if init_qso and 'STATION_CALLSIGN' in init_qso else ''
        if my_call:
            self.__my_call__ = my_call

        self.__my_loc__ = init_qso['MY_GRIDSQUARE'] if init_qso and 'MY_GRIDSQUARE' in init_qso else ''
        self.__my_qth__ = init_qso['MY_CITY'] if init_qso and 'MY_CITY' in init_qso else ''
        if my_loc and (not self.check_format(self.REGEX_LOCATOR, my_loc) and not self.check_qth(my_loc)):
            raise Exception('Wrong QTH/maidenhead format')
        if self.check_format(self.REGEX_LOCATOR, my_loc):
            self.__my_loc__ = my_loc
        elif self.check_qth(my_loc):
            qth, loc = self.check_qth(my_loc)
            self.__my_loc__ = loc
            self.__my_qth__ = qth

        init_qso = {} if not init_qso else init_qso

        self.__my_name__ = init_qso.get('MY_NAME', '')
        if my_name:
            self.__my_name__ = my_name

        self.__qsos__: list[dict] = []

        # Mandatory
        self.__date__ = init_qso.get('QSO_DATE', datetime.datetime.utcnow().strftime('%Y%m%d'))
        self.__time__ = init_qso.get('TIME_ON', datetime.datetime.utcnow().strftime('%H%M'))
        self.__band__ = init_qso.get('BAND', '')
        self.__mode__ = init_qso.get('MODE', '')

        # Optional
        self.__freq__ = init_qso.get('FREQ', '')
        self.__pwr__ = init_qso.get('TX_PWR', '')
        self.__comment__ = init_qso.get('COMMENT', '')

        # Special
        self.__event__ = event
        if not self.is_sig():
            try:
                self.__event_ref__ = int(event_ref) if self.__event__ else 0
            except ValueError:
                self.__event_ref__ = event_ref
        else:
            self.__event_ref__ = event_ref

        self.__worked_calls__: dict[str, tuple[str, str]] = init_worked if type(init_worked) is dict else {}

        self.__edit_pos__ = -1
        self.__cur_seq__ = ''
        self.__long_mode__ = False

        self.__cur_qso__ = {}
        self.__qso_active__ = False
        self.clear()

    def is_sig(self):
        return self.__event__ in ('POTA', 'SOTA')

    def append_char(self, char: str) -> str:
        """Append a single char to the sequence stack
        If a backspace \\b is appended, and it is possible to delete from the end of the sequence a \\b will be returned
        :param char: the character to add
        :return: the result of evaluation or other actions"""

        if len(char) != 1:
            raise Exception('More or less than one character')

        if char == '\b':  # TODO: Is there a better way?
            if len(self.__cur_seq__) > 0:
                self.__cur_seq__ = self.__cur_seq__[:-1]
                return '\b'
        elif self.__long_mode__:
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

    def check_qth(self, qth_loc: str) -> None | tuple:
        """Test a QTH + locator against a regular expression
        :param qth_loc: "QTH (locator)"
        :return: tuple of parts ('QTH', 'locator')"""

        m = re.fullmatch(self.REGEX_QTH, qth_loc.strip())
        if m:
            return m.groups()[:2]

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
        if self.__my_qth__:
            self.__cur_qso__['MY_CITY'] = self.__my_qth__
        if self.__pwr__:
            self.__cur_qso__['TX_PWR'] = self.__pwr__
        if self.__freq__:
            self.__cur_qso__['FREQ'] = self.__freq__
        if self.__comment__:
            self.__cur_qso__['COMMENT'] = self.__comment__

        if self.__event__:
            self.clear_event()

    def clear_event(self):
        if self.is_sig():
            self.__cur_qso__['MY_SIG'] = self.__event__
            self.__cur_qso__['MY_SIG_INFO'] = self.__event_ref__
            # self.__cur_qso__[f'MY_{self.__event__}_REF'] = self.__event_ref__  # unused?
        else:
            self.__cur_qso__['CONTEST_ID'] = self.__event__
            if type(self.__event_ref__) is int:
                self.__cur_qso__['STX'] = f'{self.__event_ref__:03d}'
                self.__cur_qso__['STX_STRING'] = f'{self.__event_ref__:03d}'
            else:
                self.__cur_qso__.pop('STX', '')
                self.__cur_qso__['STX_STRING'] = self.__event_ref__

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
        self.__comment__ = ''

        # Special
        self.__event__ = ''
        self.__event_ref__: int | str = 0
        self.__worked_calls__ = []

        self.clear()

    def append_qso(self, qso: dict[str, str]):
        """Append a QSO to stack
        Missing fields will be initialised and the call will be added to 'worked before'
        :param qso: the QSO as a dictionary of ADIF compatible keys and values"""
        _qso = deepcopy(qso)

        for f in self.QSO_REQ_FIELDS:
            if f not in _qso:
                if f == 'QSO_DATE':
                    _qso[f] = self.__date__
                elif f == 'TIME_ON':
                    _qso[f] = self.__time__
                else:
                    _qso[f] = ''

        if _qso["CALL"]:
            self.__worked_calls__[_qso["CALL"]] = (qso['QSO_DATE'], qso['TIME_ON'])

        self.__qsos__.append(_qso)

    def finalize_qso(self) -> str:
        """Append the current QSO to the QSO stack and prepare for the next one
        :return: the result of evaluation"""

        res = self.evaluate(self.__cur_seq__)
        self.__cur_seq__ = ''
        self.__long_mode__ = False

        if self.__qso_active__:
            qso = deepcopy(self.__cur_qso__)

            if qso["CALL"]:
                res = f'Last QSO cached: {qso["CALL"]}'
            else:
                res = 'Warning: Callsign missing for last QSO'

            if self.__edit_pos__ == -1:
                self.__qsos__.append(qso)
                if qso["CALL"]:
                    self.__worked_calls__[qso["CALL"]] = (qso['QSO_DATE'], qso['TIME_ON'])
            else:
                self.__qsos__[self.__edit_pos__] = self.__cur_qso__

            self.clear()

            if self.__event__:
                self.finalize_event()

        return res

    def finalize_event(self):
        if not self.is_sig():
            if type(self.__event_ref__) is int:
                self.__event_ref__ += 1
                self.__cur_qso__['STX'] = f'{self.__event_ref__:03d}'
                self.__cur_qso__['STX_STRING'] = f'{self.__event_ref__:03d}'
            else:
                self.__cur_qso__['STX_STRING'] = self.__event_ref__

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
        """Tests if the string is a valid number including sign"""

        return number[1:].isnumeric() if number.startswith('-') else number.isnumeric()

    @staticmethod
    def isdecimal(number: str) -> bool:
        """Tests if the string is a valid decimal number with at most one decimal point"""

        return not number.startswith('.') and number.replace('.', '').isnumeric() and number.count('.') <= 1

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
                return 'Error: Wrong date format'
            self.__date__ = d
            self.__cur_qso__['QSO_DATE'] = d
        elif seq.endswith('t'):
            t = seq[:-1]
            if len(t) == 2:  # if only minutes are given fill hour with old time
                t = self.__time__[:2] + t
            if not self.check_format(self.REGEX_TIME, t):
                return 'Error: Wrong time format'
            self.__time__ = t
            self.__cur_qso__['TIME_ON'] = self.__time__
        elif seq.endswith('f'):
            if seq[:-1] != '0':
                self.__freq__ = f'{float(seq[:-1]) / 1000:0.6f}'.rstrip('0').rstrip('.')
                self.__cur_qso__['FREQ'] = self.__freq__
            else:
                self.__freq__ = ''
                self.__cur_qso__.pop('FREQ', '')
        elif seq.endswith('p'):
            if seq[:-1] != '0':
                self.__pwr__ = seq[:-1]
                self.__cur_qso__['TX_PWR'] = self.__pwr__
            else:
                self.__pwr__ = ''
                self.__cur_qso__.pop('TX_PWR', '')
        else:
            return 'Error: Unknown number format'
        return ''

    def evaluate_event(self, seq: str) -> str:
        if len(seq) > 1:
            self.__event__ = seq
            if self.is_sig():
                self.__event_ref__ = ''
                self.__cur_qso__['MY_SIG'] = self.__event__
                self.__cur_qso__['MY_SIG_INFO'] = self.__event_ref__
                # self.__cur_qso__[f'MY_{self.__event__}_REF'] = self.__event_ref__  # unused?
            else:
                self.__event_ref__ = 1
                self.__cur_qso__['CONTEST_ID'] = self.__event__
                self.__cur_qso__['STX'] = '001'
                self.__cur_qso__['STX_STRING'] = '001'
                self.__cur_qso__['SRX_STRING'] = ''
        else:
            self.__event__ = ''
            self.__event_ref__ = 0

            # Cleanup SIG
            self.__cur_qso__.pop('SIG', '')
            self.__cur_qso__.pop('SIG_INFO', '')
            self.__cur_qso__.pop('MY_SIG', '')
            self.__cur_qso__.pop('MY_SIG_INFO', '')
            # for x in ('POTA', 'SOTA'):  # unused?
            #     self.__cur_qso__.pop(f'{x}_REF', '')
            #     self.__cur_qso__.pop(f'MY_{x}_REF', '')

            # Cleanup contest
            self.__cur_qso__.pop('CONTEST_ID', '')
            self.__cur_qso__.pop('STX', '')
            self.__cur_qso__.pop('STX_STRING', '')
            self.__cur_qso__.pop('SRX', '')
            self.__cur_qso__.pop('SRX_STRING', '')

        return ''

    def evaluate_extended(self, seq: str) -> str:
        if seq.startswith('-c'):
            if not self.check_format(self.REGEX_CALL, seq[2:]):
                return 'Error: Wrong call format'
            self.__my_call__ = seq[2:].upper()
            self.__cur_qso__['STATION_CALLSIGN'] = self.__my_call__
        elif seq.startswith('-l'):
            if seq == '-l':
                self.__cur_qso__.pop('MY_GRIDSQUARE', '')
                self.__cur_qso__.pop('MY_CITY', '')
                self.__my_loc__ = ''
                self.__my_qth__ = ''
                return ''
            if not self.check_format(self.REGEX_LOCATOR, seq[2:]) and not self.check_qth(seq[2:]):
                return 'Error: Wrong QTH/maidenhead format'
            if self.check_format(self.REGEX_LOCATOR, seq[2:]):
                self.__my_loc__ = seq[2:4].upper() + seq[4:]
                self.__cur_qso__['MY_GRIDSQUARE'] = self.__my_loc__
                if 'MY_CITY' in self.__cur_qso__:
                    self.__cur_qso__.pop('MY_CITY', '')
                    self.__my_qth__ = ''
            else:
                self.__my_qth__, self.__my_loc__ = self.check_qth(seq[2:])
                self.__my_qth__ = self.__my_qth__.replace('_', ' ')
                self.__cur_qso__['MY_GRIDSQUARE'] = self.__my_loc__
                self.__cur_qso__['MY_CITY'] = self.__my_qth__
        elif seq.startswith('-n'):
            if seq == '-n':
                self.__cur_qso__.pop('MY_NAME', '')
                self.__my_name__ = ''
                return ''
            self.__my_name__ = seq[2:].replace('_', ' ')
            self.__cur_qso__['MY_NAME'] = self.__my_name__
        elif seq.startswith('-N'):  # Start contest qso ID
            if self.__event__:
                self.evaluate_own_event_ref(seq)
            else:
                return 'Error: No active event'
        elif seq == '-V':
            return f'{__proj_name__}: {__version_str__}'
        else:
            return 'Error: Unknown prefix'
        return ''

    def evaluate_locator(self, seq: str) -> str:
        if seq == '':
            self.__cur_qso__.pop('GRIDSQUARE', '')
            self.__cur_qso__.pop('QTH', '')
            return ''

        if not self.check_format(self.REGEX_LOCATOR, seq) and not self.check_qth(seq):
            return 'Error: Wrong QTH/maidenhead format'
        if self.check_format(self.REGEX_LOCATOR, seq):
            self.__cur_qso__['GRIDSQUARE'] = seq[:2].upper() + seq[2:]
            self.__cur_qso__.pop('QTH', '')
        else:
            qth, loc = self.check_qth(seq)
            self.__cur_qso__['GRIDSQUARE'] = loc[:2].upper() + loc[2:]
            self.__cur_qso__['QTH'] = qth.replace('_', ' ')
        return ''

    def evaluate_rst(self, seq: str) -> str:
        if not self.check_format(self.REGEX_RSTFIELD, seq[1:]):
            return 'Error: Wrong RST format'
        if seq[0] == '.':
            self.__cur_qso__['RST_RCVD'] = seq[1:].upper()
        else:
            self.__cur_qso__['RST_SENT'] = seq[1:].upper()
        return ''

    def evaluate_call(self, seq: str) -> str:
        self.__cur_qso__['CALL'] = seq.upper()
        if not self.check_format(self.REGEX_CALL, seq):
            return 'Warning: Wrong call format'
        if seq.upper() in self.__worked_calls__:
            return (f'{seq.upper()} worked on {adif_date2iso(self.__worked_calls__[seq.upper()][0])} '
                    f'at {adif_time2iso(self.__worked_calls__[seq.upper()][1])}')
        return ''

    def evaluate(self, seq: str) -> str:
        if not seq:
            return ''

        self.__qso_active__ = True

        if seq.lower().endswith('m') and seq.lower() in BANDS:
            self.__band__ = seq.lower()
            self.__cur_qso__['BAND'] = self.__band__
        elif self.isnumeric(seq) and 0 < len(seq) < 3:
            if seq in self.BANDS_HOSTI:
                self.__band__ = self.BANDS_HOSTI[seq.lower()]
                self.__cur_qso__['BAND'] = self.__band__
        elif self.isdecimal(seq[:-1]):
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
            if seq == '#':
                self.__cur_qso__.pop('COMMENT', '')
                self.__comment__ = ''
                return ''
            self.__comment__ = seq[1:].replace('_', ' ')
            self.__cur_qso__['COMMENT'] = self.__comment__
        elif seq.startswith('\''):  # Name
            if seq == '\'':
                self.__cur_qso__.pop('NAME', '')
                return ''
            self.__cur_qso__['NAME'] = seq[1:].replace('_', ' ')
        elif seq.startswith('@'):  # Locator
            return self.evaluate_locator(seq[1:])
        elif seq.startswith('$'):  # Event
            return self.evaluate_event(seq[1:].upper())
        elif seq.startswith('%'):  # Event QSO ref
            if not self.__event__:
                return 'Error: No active event'
            self.evaluate_event_ref(seq)
        elif seq[0] in '.,':  # RST
            return self.evaluate_rst(seq)
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
        elif seq[0] == '-':  # different extended infos and commands
            return self.evaluate_extended(seq)
        else:  # Assume a callsign
            return self.evaluate_call(seq)

        return ''

    def evaluate_event_ref(self, seq):
        if self.is_sig():
            self.__cur_qso__['SIG'] = self.__event__
            self.__cur_qso__['SIG_INFO'] = seq[1:].upper()
            # self.__cur_qso__[f'{self.__event__}_REF'] = seq[1:].upper()  # unused?
        else:
            try:
                self.__cur_qso__['SRX'] = str(int(seq[1:]))
            except ValueError:
                pass
            self.__cur_qso__['SRX_STRING'] = seq[1:].upper()

    def evaluate_own_event_ref(self, seq):
        if self.is_sig():
            self.__event_ref__ = seq[2:].upper()
            self.__cur_qso__['MY_SIG'] = self.__event__
            self.__cur_qso__['MY_SIG_INFO'] = self.__event_ref__
            # self.__cur_qso__[f'MY_{self.__event__}_REF'] = self.__event_ref__  # unused?
        else:
            try:
                self.__event_ref__ = int(seq[2:])
                self.__cur_qso__['STX'] = f'{self.__event_ref__:03d}'
                self.__cur_qso__['STX_STRING'] = f'{self.__event_ref__:03d}'
            except ValueError:
                self.__event_ref__ = seq[2:].upper()
                self.__cur_qso__.pop('STX', '')
                self.__cur_qso__['STX_STRING'] = self.__event_ref__
