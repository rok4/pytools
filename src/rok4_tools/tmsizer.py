#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import logging

from rok4.tile_matrix_set import TileMatrixSet

from rok4_tools import __version__

# Default logger
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)

args = None
tms = None

def parse() -> None:
    """Parse call arguments and check values

    Exit program if an error occured
    """

    global args
    
    parser = argparse.ArgumentParser(
        prog = 'tmsizer',
        description = "Tool to convert informations according to a tile matrix set",
        epilog = ''
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s ' + __version__
    )

    parser.add_argument(
        '--tms',
        metavar='tms_id',
        action='store',
        type=str,
        dest='tms',
        help="tile matrix set identifier",
        required=True
    )

    args = parser.parse_args()


def load_tms() -> None:
    """Create TileMatrixSet object from the provided identifier

    Raises:
        MissingEnvironmentError: Missing object storage informations
        Exception: No level in the TMS, CRS not recognized by OSR
        StorageError: Storage read issue
        FileNotFoundError: TMS file or object does not exist
        FormatError: Provided path is not a well formed JSON
        MissingAttributeError: Attribute is missing in the content
    """    

    global tms

    tms = TileMatrixSet(args.tms)

def work() -> None:
    logging.info(tms.path)

def main() -> None:

    try:
        parse()
        load_tms()
        work()

    except FileNotFoundError as e:
        logging.error(f"{e} does not exists")
        sys.exit(1)

    except Exception as e:
        logging.error(e)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__": 
    main()