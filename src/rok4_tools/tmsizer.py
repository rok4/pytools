#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse

from rok4.tile_matrix_set import TileMatrixSet

from rok4_tools import __version__

from rok4_tools.tmsizer_utils.processors.io import *
from rok4_tools.tmsizer_utils.processors.map import *
from rok4_tools.tmsizer_utils.processors.reduce import *

args = None
tms = None

reader_processor = None
input_options = {}
output_options = {}

input_options = {}
output_options = {}

conversion_processor = None



def parse() -> None:
    """Parse call arguments and check values

    Exit program if an error occured
    """

    global args, output_options, input_options
    
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
        metavar='<TMS identifier>',
        action='store',
        type=str,
        dest='tms',
        help="tile matrix set identifier",
        required=True
    )

    parser.add_argument(
        '-i',
        '--input',
        metavar='storage://path/to/data',
        action='store',
        type=str,
        dest='input_path',
        help='file/object to read data. Read from standard input if not provided',
        required=False
    )

    parser.add_argument(
        '-if',
        '--input-format',
        metavar="<format>",
        action='store',
        type=str,
        dest='input_format',
        help="input format",
        required=True
    )

    parser.add_argument(
        '-io',
        '--input-option',
        metavar='<KEY>:<VALUE>',
        action="extend",
        nargs="+",
        type=str,
        default=[],
        dest='input_options',
        help='options for input',
        required=False
    )

    parser.add_argument(
        '-o',
        '--output',
        metavar='storage://path/to/results',
        action='store',
        type=str,
        dest='output_path',
        help='file/object to write results. Print in standard output if not provided',
        required=False
    )

    parser.add_argument(
        '-of',
        '--output-format',
        metavar="<format>",
        action='store',
        type=str,
        dest='output_format',
        help="output format",
        required=True
    )

    parser.add_argument(
        '-oo',
        '--output-option',
        metavar='<KEY>:<VALUE>',
        action="extend",
        nargs="+",
        type=str,
        default=[],
        dest='output_options',
        help='options for output',
        required=False
    )

    parser.add_argument(
        '--progress',
        action='store_true',
        dest='progress',
        help='print a progress bar (only with --output option)',
        required=False
    )

    args = parser.parse_args()

    if args.output_path is None and args.progress:
        raise Exception("Print a progress bar is not consistent with standard output use for result")

    for oo in args.output_options:
        try:
            key, value = oo.split("=")
        except Exception as e:
            raise Exception(f"Output option have to be provided separately with format <key>=<value> (issue with {oo})")
        
        output_options[key] = value

    for io in args.input_options:
        try:
            key, value = io.split("=")
        except Exception as e:
            raise Exception(f"Input option have to be provided separately with format <key>=<value> (issue with {io})")
        
        input_options[key] = value

def load_tms() -> None:
    """Load TMS
    
    Create TileMatrixSet object from the provided identifier and set it for processors
    """    

    global tms

    tms = TileMatrixSet(args.tms)
    Processor.set_tms(tms)  


def load_reader() -> None:
    """
    Create the read processor (from standard input or file/object)
    """    

    global reader_processor

    if args.input_path:
        reader_processor = PathinProcessor(args.input_format, args.input_path, args.progress)
    else:
        reader_processor = StdinProcessor(args.input_format, args.progress)


def load_conversion() -> None:
    """Create the middle processor

    To process data from input to output format, several processors can be chained

    * GETTILE_PARAMS -> COUNT : Gettile2tileindexProcessor -> CountProcessor
    * GETTILE_PARAMS -> HEATMAP : Gettile2tileindexProcessor -> Tileindex2pointProcessor -> HeatmapProcessor
    * GEOMETRY -> GETTILE_PARAMS : Geometry2tileindexProcessor -> Tileindex2gettileProcessor
    """    

    global conversion_processor

    if args.input_format == "GETTILE_PARAMS":
        tp = Gettile2tileindexProcessor(reader_processor, **input_options)

        if args.output_format == "COUNT":
            conversion_processor = CountProcessor(tp)
        elif args.output_format == "HEATMAP":
            conversion_processor = HeatmapProcessor(Tileindex2pointProcessor(tp), **output_options)

    elif args.input_format == "GEOMETRY":
        tp = Geometry2tileindexProcessor(reader_processor, **input_options)

        if args.output_format == "GETTILE_PARAMS":
            conversion_processor = Tileindex2gettileProcessor(tp)

    if conversion_processor is None:
        raise Exception(f"Unhandled conversion {args.input_format} -> {args.output_format}")


def load_writer() -> None:
    """
    Create the write processor (to standard output or file/object)
    """    

    global writer_processor

    if args.output_path:
        writer_processor = PathoutProcessor(conversion_processor, args.output_path)
    else:
        writer_processor = StdoutProcessor(conversion_processor)

def work() -> None:
    status = writer_processor.process().__next__()
    print(conversion_processor)

def main() -> None:

    try:
        parse()
        load_tms()
        load_reader()
        load_conversion()
        load_writer()
        work()

    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__": 
    main()