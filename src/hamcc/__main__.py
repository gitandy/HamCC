# Copyright 2024 by Andreas Schawo, licensed under CC BY-SA 4.0

"""Log Ham Radio QSOs via console"""

import os
import sys
import logging
from collections.abc import Iterator
from typing import TextIO

LOG_FMT = '%(asctime)s %(levelname)-8s %(name)s: %(message)s'
logger = logging.getLogger('HamCC')
logging.basicConfig(filename='./hamcc.log', filemode='w', format=LOG_FMT,
                    level=logging.INFO)

from adif_file import adi
from adif_file import __version_str__ as __version_adif_file__

from . import __proj_name__, __version_str__, __author_name__, __copyright__
from .hamcc import CassiopeiaConsole


def qso_iterator(qso_stream: TextIO) -> Iterator:
    line = qso_stream.readline().strip()
    if line:
        yield line

    while line:
        line = qso_stream.readline().strip()
        if line:
            yield line


def process_qsos(qsos: list[list[str]] | TextIO, file: str,
                 own_call: str, own_loc: str, own_name: str, append: bool = False,  # noqa: C901
                 contest_id: str = '', qso_number: int = 1):
    """Process a list of text input from stdin or commandline as it was typed in console"""

    adi_f = None
    try:
        fmode = 'a' if append else 'w'
        fexists = os.path.isfile(file)

        last_qso = {}
        if fexists and append:
            logger.info('Loading last QSO...')
            doc = adi.load(file)
            last_qso = doc['RECORDS'][-1] if doc['RECORDS'] else {}

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

        cc = CassiopeiaConsole(own_call, own_loc, own_name, contest_id, qso_number, last_qso)
        qsos = qsos if type(qsos) is list else qso_iterator(qsos)
        for qso in qsos:
            if type(qso) is str:
                qso = qso.strip().split(' ')
                logger.info(f'Processing QSO: {qso}')
                for chunk in qso:
                    for char in chunk:
                        cc.append_char(char)
                    res = cc.append_char(' ')
                    if res:
                        if res.startswith('Warning:'):
                            logger.warning(f'{res} for "{chunk}"')
                        elif res.startswith('Error:'):
                            logger.error(f'{res} for "{chunk}"')
            else:
                logger.info(f'Processing QSO: {qso}')
                for val in qso:
                    res = cc.evaluate(val)
                    if res:
                        if res.startswith('Warning:'):
                            logger.warning(f'{res} for "{val}"')
                        elif res.startswith('Error:'):
                            logger.error(f'{res} for "{val}"')

            res = cc.finalize_qso()
            if res:
                if res.startswith('Warning:'):
                    logger.warning(res)
                elif res.startswith('Error:'):
                    logger.error(res)
                else:
                    logger.info(res)

            while cc.has_qsos():
                logger.info(f'Saving {len(cc.qsos)} QSO(s)...')
                adi_f.write('\n\n' + adi.dumps({'RECORDS': [cc.pop_qso()]}))
                adi_f.flush()
        logger.info('...done')
    except KeyboardInterrupt:
        logger.info('Received keyboard interrupt')
    finally:
        if adi_f:
            adi_f.close()
            logger.info('Closed ADIF file')


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
    parser.add_argument('-q', '--qso', dest='qso', metavar='VALUE', nargs='+', action='append',
                        help='a QSO string to import instead of running the console (argument can be used repeatedly per QSO)')
    parser.add_argument('--stdin', dest='stdin', action='store_true',
                        help='read QSO strings from STDIN instead of running the console')
    parser.add_argument('-c', '--call', dest='own_call', default='',
                        help='your callsign')
    parser.add_argument('-l', '--locator', dest='own_loc', default='',
                        help='your locator and QTH i.e. "JO30uj" or "Eitelborn(JO30uj)"')
    parser.add_argument('-n', '--name', dest='own_name', default='',
                        help='your name')
    parser.add_argument('-E', '--event', dest='event', default='',
                        help='the event (contest ID or one of POTA, SOTA) to activate at startup')
    parser.add_argument('-N', '--exchange', dest='exchange', default=1,
                        help='the first QSO number to use if a contest is activated or a textual exchange')
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

    if args.qso or args.stdin:
        stderr_handler = logging.StreamHandler()
        stderr_handler.setFormatter(logging.Formatter(LOG_FMT))
        stderr_handler.setLevel(args.log_level)
        logger.addHandler(stderr_handler)
        logging.getLogger('hamcc').addHandler(stderr_handler)

        qsos =  sys.stdin if args.stdin else args.qso
        process_qsos(qsos, args.file, args.own_call, args.own_loc, args.own_name,
                     not args.overwrite, args.event, args.exchange)
    else:
        from datetime import datetime
        from ._console_ import run_console
        logger.info('Starting console...')

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

        run_console(args.file, args.own_call, args.own_loc, args.own_name,
                    args.overwrite, args.event, args.exchange, records)

        logger.info('Stopped console')


if __name__ == '__main__':
    main()
