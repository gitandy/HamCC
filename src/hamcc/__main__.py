"""Log Ham Radio QSOs via console"""

import os
import sys
from curses import wrapper, window

from adif_file import adi
from adif_file import __version_str__ as __version_adif_file__

from . import __proj_name__, __version_str__, __author_name__, __copyright__
from .hamcc import CassiopeiaConsole

PROMPT = 'QSO> '


def qso2str(qso, pos, cnt):
    d = qso["QSO_DATE"][:4] + '-' + qso["QSO_DATE"][4:6] + '-' + qso["QSO_DATE"][6:8]
    t = qso["TIME_ON"][:2] + ':' + qso["TIME_ON"][2:4]

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
                val = str(float(val)*1000)
            opt_info += f' {i} {val} |'

    cntst_info = ''
    if 'CONTEST_ID' in qso and qso["CONTEST_ID"]:
        cntst_info = f' $ {qso["CONTEST_ID"]} | N {qso["STX"]} | % {qso["SRX"] if "SRX" in qso else ""} |'

    loc = f'{qso["QTH"]} ({qso["GRIDSQUARE"]})' if 'QTH' in qso else qso["GRIDSQUARE"]

    return (f'| {"*" if pos == -1 else pos+1}/{"-" if cnt == 0 else cnt} | d {d} | t {t} | B {qso["BAND"]} | '
            f'M {qso["MODE"]} | C {qso["CALL"]} | @ {loc} |{cntst_info}{opt_info}')


def command_console(stdscr: window, file, own_call, own_loc, own_name, append=False, contest_id='', qso_number=1):
    adi_f = None
    try:
        cc = CassiopeiaConsole(own_call, own_loc, own_name, contest_id, qso_number)

        fmode = 'a' if append else 'w'
        fexists = os.path.isfile(file)
        adi_f = open(file, fmode)

        if not append or not fexists:
            adi_header = {
                'HEADER': {
                    'PROGRAMID': 'hamcc',
                    'PROGRAMVERSION': __version_str__,
                }}

            adi_f.write(adi.dumps(adi_header, comment='ADIF export by hamcc'))
            adi_f.flush()

        # Clear screen
        stdscr.clear()
        stdscr.addstr(0, 0, qso2str(cc.current_qso, cc.edit_pos, 0))
        fname = '...'+adi_f.name[-60:] if len(adi_f.name) > 60 else adi_f.name
        stdscr.addstr(2, 0, f'{"Appending to" if append else "Overwriting"} "{fname}"')
        stdscr.addstr(1, 0, PROMPT)

        stdscr.refresh()

        try:
            while True:
                py, px = stdscr.getyx()
                stdscr.addstr(0, 0, qso2str(cc.current_qso, cc.edit_pos, len(cc.qsos)))
                stdscr.clrtoeol()
                stdscr.addstr(py, px, '')

                c = stdscr.getkey()

                if c == 'KEY_UP':
                    cc.load_prev()
                    stdscr.addstr(2, 0, '')
                    stdscr.clrtoeol()
                    stdscr.addstr(1, 0, PROMPT)
                    stdscr.clrtoeol()
                elif c == 'KEY_DOWN':
                    cc.load_next()
                    stdscr.addstr(2, 0, '')
                    stdscr.clrtoeol()
                    stdscr.addstr(1, 0, PROMPT)
                    stdscr.clrtoeol()
                elif c == 'KEY_DC':
                    res = cc.del_selected()
                    if res >= 0:
                        stdscr.addstr(2, 0, f'Deleted QSO #{res+1}')
                    else:
                        stdscr.addstr(2, 0, '')
                    stdscr.clrtoeol()
                    stdscr.addstr(1, 0, PROMPT)
                    stdscr.clrtoeol()
                elif len(c) > 1 or c in '\r\b\t':
                    continue
                elif c == '\n':  # Flush QSO to stack
                    res = cc.append_char(c)
                    stdscr.addstr(2, 0, res)
                    stdscr.clrtoeol()
                    stdscr.addstr(1, 0, PROMPT)
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
                    stdscr.addstr(2, 0, msg)
                    stdscr.clrtoeol()
                    stdscr.addstr(1, 0, PROMPT)
                    stdscr.clrtoeol()
                else:  # Concat sequence
                    res = cc.append_char(c)
                    stdscr.addstr(2, 0, res)
                    stdscr.clrtoeol()
                    if c in ('~', '?'):
                        stdscr.addstr(1, 0, PROMPT)
                        stdscr.clrtoeol()
                    else:
                        stdscr.addstr(py, px, '')
                        stdscr.addstr(c)
        except KeyboardInterrupt:
            while cc.has_qsos():
                adi_f.write('\n\n' + adi.dumps({'RECORDS': [cc.pop_qso()]}))
                adi_f.flush()
    except Exception as exc:  # Print exception info due to curses wrapper removes traceback
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
    finally:
        if adi_f:
            adi_f.close()


def main():
    import argparse

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
    parser.add_argument('-x', '--overwrite', dest='overwrite', action='store_true',
                        help='overwriting the file instead of appending the QSOs')

    args = parser.parse_args()

    if os.name == 'nt':
        os.system("mode con cols=120 lines=25")

    wrapper(command_console, args.file, args.own_call, args.own_loc, args.own_name,
            not args.overwrite, args.contest_id, args.qso_number)


if __name__ == '__main__':
    main()
