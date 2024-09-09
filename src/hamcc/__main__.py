"""Log Ham Radio QSOs via console"""

import os
import sys
import time
from curses import wrapper, window, error
import logging

logger = logging.getLogger('HamCC')
logging.basicConfig(filename='./hamcc.log', filemode='w', format='%(asctime)s %(levelname)-8s %(name)s: %(message)s',
                    level=logging.INFO)

from adif_file import adi
from adif_file import __version_str__ as __version_adif_file__

from . import __proj_name__, __version_str__, __author_name__, __copyright__
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
            ('p', 'TX_POWER'),
            ('*', 'QSL_RCVD'),
            ('#', 'COMMENT'),
    ):
        if f in qso:
            val = qso[f]
            if f == 'FREQ':
                val = str(float(val) * 1000)
            if f in ('FREQ', 'TX_POWER'):
                opt_info += f'| {val} {i} '
            else:
                opt_info += f'| {i} {val} '

    cntst_info = ''
    if 'CONTEST_ID' in qso and qso["CONTEST_ID"]:
        cntst_info = (f'[ $ {qso["CONTEST_ID"]} | -N {qso.get("STX", qso["STX_STRING"])} | '
                      f'% {qso.get("SRX", qso.get("SRX_STRING", ""))} ]')

    loc = ''
    if 'GRIDSQUARE' in qso:
        loc = f'{qso["QTH"]} ({qso["GRIDSQUARE"]})' if 'QTH' in qso else qso["GRIDSQUARE"]

    my_loc = ''
    if 'MY_GRIDSQUARE' in qso:
        my_loc = f'{qso["MY_CITY"]} ({qso["MY_GRIDSQUARE"]})' if 'MY_CITY' in qso else qso["MY_GRIDSQUARE"]

    line1 = (f'[ {"*" if pos == -1 else pos + 1}/{"-" if cnt == 0 else cnt} ] '
             f'[ -c {qso["STATION_CALLSIGN"]} | -l {my_loc} | -n {qso.get("MY_NAME", "")} ] {cntst_info}')
    line2 = (f'[ {d} d | {t} t | B {qso["BAND"]} | '
             f'M {qso["MODE"]} | C {qso["CALL"]} | @ {loc} {opt_info}]')

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


# flake8: noqa: C901
def command_console(stdscr: window, file, own_call, own_loc, own_name, append=False,
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
        logger.info('Loading QSOs (if available)...')
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
            logger.info(f'Saving {len(cc.qsos)} QSOs...')
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


def main():
    import argparse
    from datetime import datetime
    logger.info('Starting...')

    parser = argparse.ArgumentParser(description='Log Ham Radio QSOs via console',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=f'Author: {__author_name__}\n{__copyright__}')

    parser.add_argument('-V', '--version', action='version',
                        version=f'{__proj_name__}: {__version_str__}\nPyADIF-File: {__version_adif_file__}',
                        help='show version and exit')
    parser.add_argument('file', metavar='ADIF_FILE', nargs='?',
                        default=os.path.expanduser('~/hamcc_log.adi'),
                        help='the file to store the QSOs')
    parser.add_argument('-c', '--call', dest='own_call', default='',
                        help='your callsign')
    parser.add_argument('-l', '--locator', dest='own_loc', default='',
                        help='your locator and QTH i.e. "JO30uj" or "Eitelborn(JO30uj)"')
    parser.add_argument('-n', '--name', dest='own_name', default='',
                        help='your name')
    parser.add_argument('-C', '--contest', dest='contest_id', default='',
                        help='the contest ID to activate at startup')
    parser.add_argument('-N', '--qso-number', dest='qso_number', type=int, default=1,
                        help='the first QSO number to use if a contest is activated')
    parser.add_argument('-L', '--load-qsos', dest='load_qsos', action='store_true',
                        help='load stored QSOs to edit them (creates backup and opens a new file)')
    parser.add_argument('-x', '--overwrite', dest='overwrite', action='store_true',
                        help='overwriting the file instead of appending the QSOs')
    parser.add_argument('--log-level', dest='log_level', choices=['DEBUG', 'INFO', 'WARNING'],
                        default='INFO',
                        help='set level for messages')

    args = parser.parse_args()

    if args.log_level:
        logger.setLevel(args.log_level)
        logging.getLogger('hamcc').setLevel(args.log_level)

    if os.name == 'nt':
        os.system("mode con cols=120 lines=25")

    records = []
    if args.load_qsos:
        if os.path.isfile(args.file):
            bak_date = datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
            phead, ptail = os.path.split(args.file)
            bak_file = os.path.join(phead, f'{bak_date}_{ptail}')
            logger.info(f'Creating backup "{bak_file}" from "{args.file}"...')
            os.rename(args.file, bak_file)
            doc = adi.load(bak_file)
            records = doc['RECORDS']

    wrapper(command_console, args.file, args.own_call, args.own_loc, args.own_name,
            not args.overwrite, args.contest_id, args.qso_number, records)

    logger.info('Stopped')


if __name__ == '__main__':
    main()
