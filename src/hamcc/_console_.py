# Copyright 2024 by Andreas Schawo, licensed under CC BY-SA 4.0

"""Log Ham Radio QSOs via console"""

import os
import sys
import time
import logging
from platform import python_implementation
from curses import wrapper, error

if python_implementation() == 'PyPy':
    # noinspection PyUnresolvedReferences,PyPep8Naming
    from curses import Window as window
else:
    # noinspection PyUnresolvedReferences
    from curses import window

logger = logging.getLogger('HamCC')

from adif_file import adi

from . import __version_str__
from .hamcc import CassiopeiaConsole, adif_date2iso, adif_time2iso

PROMPT = 'QSO> '
LN_MYDATA = 0
LN_QSODATA = 1
LN_INPUT = 2
LN_INFO = 3


def qso2str(qso, pos, cnt) -> tuple[str, str]:
    d = adif_date2iso(qso["QSO_DATE"])
    t = adif_time2iso(qso["TIME_ON"])

    opt_info = ''
    for i, f in (
            ('.', 'RST_RCVD'),
            (',', 'RST_SENT'),
            ('\'', 'NAME'),
            ('f', 'FREQ'),
            ('p', 'TX_PWR'),
            ('*', 'QSL_RCVD'),
            ('#', 'COMMENT'),
    ):
        if f in qso:
            val = qso[f]
            if f == 'FREQ':
                val = f'{float(val) * 1000:0.3f}'.rstrip('0').rstrip('.')
            if f in ('FREQ', 'TX_PWR'):
                opt_info += f'| {val} {i} '
            else:
                opt_info += f'| {i} {val} '

    event_info = ''
    if 'CONTEST_ID' in qso and qso["CONTEST_ID"]:
        event_info = (f'[ $ {qso["CONTEST_ID"]} | -N {qso.get("STX", qso["STX_STRING"])} | '
                      f'% {qso.get("SRX", qso.get("SRX_STRING", ""))} ]')
    elif 'MY_SIG' in qso:
        event_info = f'[ $ {qso["MY_SIG"]} | -N {qso["MY_SIG_INFO"]} | % {qso.get("SIG_INFO", "")} ]'

    loc = ''
    if 'GRIDSQUARE' in qso:
        loc = f'{qso["QTH"]} ({qso["GRIDSQUARE"]})' if 'QTH' in qso else qso["GRIDSQUARE"]

    my_loc = ''
    if 'MY_GRIDSQUARE' in qso:
        my_loc = f'{qso["MY_CITY"]} ({qso["MY_GRIDSQUARE"]})' if 'MY_CITY' in qso else qso["MY_GRIDSQUARE"]

    line1 = (f'[ {"*" if pos == -1 else pos + 1}/{"-" if cnt == 0 else cnt} ] '
             f'[ -c {qso["STATION_CALLSIGN"]} | -l {my_loc} | -n {qso.get("MY_NAME", "")} ] {event_info}')
    line2 = (f'[ {d} d | {t} t | {qso["BAND"] if qso["BAND"] else "Band"} | {qso["MODE"] if qso["MODE"] else "Mode"} | '
             f'{qso["CALL"] if qso["CALL"] else "Call"} | @ {loc} {opt_info}]')

    return line1, line2


def read_adi(file: str) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    last_qso = {}
    worked_calls = {}

    doc = adi.load(file)
    for r in doc['RECORDS']:
        if all(f in r for f in ('CALL', 'QSO_DATE', 'TIME_ON')):
            last_qso = r
            worked_calls[r['CALL']] = (r['QSO_DATE'], r['TIME_ON'])
    return last_qso, worked_calls


def command_console(stdscr, file, own_call, own_loc, own_name, append=False,  # noqa: C901
                    contest_id='', qso_number=1, records: list = []):
    adi_f = None
    try:
        fmode = 'a' if append else 'w'
        fexists = os.path.isfile(file)

        last_qso = {}
        worked_calls = []
        if fexists and append:
            logger.info('Loading last QSO and worked before...')
            last_qso, worked_calls = read_adi(file)

        adi_f = open(file, fmode)

        if not append or not fexists:
            logger.info('Initialising ADIF file...')
            adi_header = {
                'HEADER': {
                    'PROGRAMID': 'HamCC',
                    'PROGRAMVERSION': __version_str__,
                }}

            adi_f.write(adi.dumps(adi_header, comment='ADIF export by hamcc'))
            adi_f.flush()
            logger.info('...done')

        if records:
            last_qso = records[-1]

        cc = CassiopeiaConsole(own_call, own_loc, own_name, contest_id, qso_number, last_qso, worked_calls)
        if records:
            logger.info('Loading QSOs...')
            for r in records:
                cc.append_qso(r)
            logger.info(f'...done {len(cc.qsos)} QSOs')

        # Clear screen
        stdscr.clear()
        ln1, ln2 = qso2str(cc.current_qso, cc.edit_pos, 0)
        stdscr.addstr(LN_MYDATA, 0, ln1)
        stdscr.addstr(LN_QSODATA, 0, ln2)

        fname = '...' + adi_f.name[-40:] if len(adi_f.name) > 40 else adi_f.name
        last_qso_str = (f'. Last QSO: {last_qso["CALL"]} '
                        f'worked on {adif_date2iso(last_qso["QSO_DATE"])} '
                        f'at {adif_time2iso(last_qso["TIME_ON"])}') if last_qso and 'CALL' in last_qso else ''
        stdscr.addstr(LN_INFO, 0, f'{"Appending to" if append else "Overwriting"} "{fname}"{last_qso_str}')
        stdscr.addstr(LN_INPUT, 0, PROMPT)

        stdscr.refresh()
        stdscr.nodelay(True)

        try:
            logger.info('Entering main loop...')
            while True:
                py, px = stdscr.getyx()
                ln1, ln2 = qso2str(cc.current_qso, cc.edit_pos, len(cc.qsos))
                stdscr.addstr(LN_MYDATA, 0, ln1)
                stdscr.clrtoeol()
                stdscr.addstr(LN_QSODATA, 0, ln2)
                stdscr.clrtoeol()
                stdscr.addstr(py, px, '')

                while True:
                    try:
                        c = stdscr.getkey()
                        break
                    except error:
                        time.sleep(.01)

                if c == 'KEY_UP':
                    cc.load_prev()
                    stdscr.addstr(LN_INFO, 0, '')
                    stdscr.clrtoeol()
                    stdscr.addstr(LN_INPUT, 0, PROMPT)
                    stdscr.clrtoeol()
                elif c == 'KEY_DOWN':
                    cc.load_next()
                    stdscr.addstr(LN_INFO, 0, '')
                    stdscr.clrtoeol()
                    stdscr.addstr(LN_INPUT, 0, PROMPT)
                    stdscr.clrtoeol()
                elif c == 'KEY_DC':
                    res = cc.del_selected()
                    if res >= 0:
                        stdscr.addstr(LN_INFO, 0, f'Deleted QSO #{res + 1}')
                    else:
                        stdscr.addstr(LN_INFO, 0, '')
                    stdscr.clrtoeol()
                    stdscr.addstr(LN_INPUT, 0, PROMPT)
                    stdscr.clrtoeol()
                elif len(c) > 1 or c in '\r\t':
                    continue
                elif c == '\n':  # Flush QSO to stack
                    res = cc.append_char(c)
                    stdscr.addstr(LN_INFO, 0, res)
                    stdscr.clrtoeol()
                    stdscr.addstr(LN_INPUT, 0, PROMPT)
                    stdscr.clrtoeol()
                elif c == '!':  # Write QSOs to disk
                    cc.append_char('\n')
                    i = 0
                    msg = ''
                    while cc.has_qsos():
                        adi_f.write('\n\n' + adi.dumps({'RECORDS': [cc.pop_qso()]}))
                        adi_f.flush()
                        i += 1
                        msg = f'{i} QSO(s) written to disk'
                    stdscr.addstr(LN_INFO, 0, msg)
                    stdscr.clrtoeol()
                    stdscr.addstr(LN_INPUT, 0, PROMPT)
                    stdscr.clrtoeol()
                else:  # Concat sequence
                    res = cc.append_char(c)
                    stdscr.addstr(LN_INFO, 0, res)
                    stdscr.clrtoeol()
                    if c in ('~', '?'):
                        stdscr.addstr(LN_INPUT, 0, PROMPT)
                        stdscr.clrtoeol()
                    else:
                        stdscr.addstr(py, px, '')
                        if c == '\b':  # TODO: Is there a better way?
                            if res == '\b':
                                stdscr.addstr(c)
                                stdscr.clrtoeol()
                        else:
                            stdscr.addstr(c)
        except KeyboardInterrupt:
            logger.info('Received keyboard interrupt')
        finally:
            logger.info(f'Saving {len(cc.qsos)} QSO(s)...')
            while cc.has_qsos():
                adi_f.write('\n\n' + adi.dumps({'RECORDS': [cc.pop_qso()]}))
                adi_f.flush()
            logger.info('...done')
    except Exception as exc:  # Print exception info due to curses wrapper removes traceback
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        logger.exception(exc)
    finally:
        if adi_f:
            adi_f.close()
            logger.info('Closed ADIF file')


def run_console(file, own_call, own_loc, own_name, overwrite, event, exchange, records):
    if os.name == 'nt':
        os.system("mode con cols=120 lines=25")

    wrapper(command_console, file, own_call, own_loc, own_name,
            not overwrite, event, exchange, records)
