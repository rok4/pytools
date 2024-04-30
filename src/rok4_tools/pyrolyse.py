#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import logging
import json
import os
import numpy
import time
import tempfile
import copy
from tqdm import tqdm

from rok4.pyramid import Pyramid, ROK4_IMAGE_HEADER_SIZE, SlabType
from rok4.storage import put_data_str, get_size, get_path_from_infos, get_data_binary

from rok4_tools import __version__

# Default logger
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)

args = None
pyramid = None
total = None
pbar = None

stat_part = {
    "slab_count": 0,
    "slab_sizes": [],
    "link_count": 0
}

stats = {
    "global": {
        "slab_count": 0,
        "slab_sizes": [],
        "link_count": 0
    },
    "levels": {}
}


quantiles = [0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1]

def parse() -> None:
    """Parse call arguments and check values

    Exit program if an error occured

    Raises:
        Exception: option --progress is used without --json
    """

    global args, stat_part, stats
    
    parser = argparse.ArgumentParser(
        prog = 'pyrolyse',
        description = "Tool to process statistics about pyramid's data : count and size of tiles and slabs, min and max, by level",
        epilog = ''
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s ' + __version__
    )

    parser.add_argument(
        '--pyramid',
        metavar='storage://path/to/pyr.json',
        action='store',
        type=str,
        dest='pyramid',
        help="Pyramid's descriptor, to analyse",
        required=True
    )

    parser.add_argument(
        '--output',
        metavar='storage://path/to/conf.json',
        action='store',
        dest='output_path',
        help='File/object to write results. Print in standard output if not provided',
        required=False
    )

    parser.add_argument(
        '--tiles',
        action='store_true',
        dest='tiles',
        help='Get size analysis for tiles',
        required=False
    )

    parser.add_argument(
        '--progress',
        action='store_true',
        dest='progress',
        help='Print a progress bar (only with --output option)',
        required=False
    )

    parser.add_argument(
        '--deciles',
        action='store_true',
        dest='deciles',
        help='Get deciles for sizes and read times rather than values',
        required=False
    )

    parser.add_argument(
        '--ratio',
        type=int,
        metavar="N",
        action='store',
        dest='ratio',
        default=100,
        help='Ratio of measured slabs and tiles (<ratio> choose one). All slabs are counted',
        required=False
    )

    args = parser.parse_args()

    if args.tiles:
        stat_part["tile_sizes"] = []
        stats["global"]["tile_sizes"] = []
        stats["perfs"] = []

    if args.progress and args.output_path is None:
        raise Exception("Print a progress bar is not possible without output file for statistics (--json option)")


def load() -> None:
    """Create Pyramid object from the descriptor's path

    Raises:
        FormatError: Provided path or the TMS is not a well formed JSON
        Exception: Level issue : no one in the pyramid or the used TMS, or level ID not defined in the TMS
        MissingAttributeError: Attribute is missing in the content
        StorageError: Storage read issue (pyramid descriptor or TMS)
        MissingEnvironmentError: Missing object storage informations or TMS root directory
    """    

    global pyramid, total, pbar

    pyramid = Pyramid.from_descriptor(args.pyramid)
    total = pyramid.load_list()

    if args.progress:
        pbar = tqdm(total=total)

def work() -> None:
    """Browse pyramid's list and memorize wanted informations

    If tiles' statistics wanted, we keep only one non null tile size by slab. We don't consider size of slab link but the slab target one.
    """

    global stat_part, stats, pyramid, pbar

    slab_tiles_count = pyramid.bottom_level.slab_width * pyramid.bottom_level.slab_height
    slab_sizes_offset = ROK4_IMAGE_HEADER_SIZE + 4 * slab_tiles_count
    slab_sizes_size = 4 * slab_tiles_count

    for (slab_type, level, column, row), infos in pyramid.list_generator():
        if slab_type != SlabType.DATA:
            continue

        if level not in stats["levels"]:
            stats["levels"][level] = copy.deepcopy(stat_part)

        stats["global"]["slab_count"] += 1
        stats["levels"][level]["slab_count"] += 1
        
        if infos["link"]:
            stats["global"]["link_count"] += 1
            stats["levels"][level]["link_count"] += 1

        if (stats["levels"][level]["slab_count"] - 1) % args.ratio == 0:
            slab_path = get_path_from_infos(pyramid.storage_type, infos["root"], infos["slab"])
            size = get_size(slab_path)
            stats["global"]["slab_sizes"].append(size)
            stats["levels"][level]["slab_sizes"].append(size)

            if args.tiles:
                tic = time.perf_counter()
                binary_sizes = get_data_binary(slab_path, (slab_sizes_offset, slab_sizes_size))
                toc = time.perf_counter()
                stats["perfs"].append(toc - tic)
                sizes = list(filter(
                    lambda e: e != 0,
                    numpy.frombuffer(
                        binary_sizes,
                        dtype = numpy.dtype('uint32'),
                        count = slab_tiles_count
                    ).tolist()
                ))

                # On ne garde que la première taille de tuile non nulle pour les statistiques
                stats["levels"][level]["tile_sizes"].append(sizes[0])
                stats["global"]["tile_sizes"].append(sizes[0])

        if args.progress:
            pbar.update(1)

    if args.progress:
        pbar.close()

    # calcul des quantiles
    if len(stats["global"]["slab_sizes"]) > 1 and args.deciles:
        stats["global"]["slab_sizes"] = numpy.quantile(stats["global"]["slab_sizes"], quantiles).tolist()

    if args.tiles:
        if len(stats["perfs"]) > 1 and args.deciles:
            stats["perfs"] = numpy.quantile(stats["perfs"], quantiles).tolist()

        if len(stats["global"]["tile_sizes"]) > 1 and args.deciles:
            stats["global"]["tile_sizes"] = numpy.quantile(stats["global"]["tile_sizes"], quantiles).tolist()

    for level in stats["levels"]:
        if len(stats["levels"][level]["slab_sizes"]) > 1 and args.deciles:
            stats["levels"][level]["slab_sizes"] = numpy.quantile(stats["levels"][level]["slab_sizes"], quantiles).tolist()

        if args.tiles and len(stats["levels"][level]["tile_sizes"]) > 1 and args.deciles:
            stats["levels"][level]["tile_sizes"] = numpy.quantile(stats["levels"][level]["tile_sizes"], quantiles).tolist()


def write() -> None:
    """Write the informations as JSON, in the standard output or a file
    """    
    if args.output_path is None:
        print(json.dumps(stats))
    else:
        put_data_str(json.dumps(stats), args.output_path)


def main() -> None:

    try:
        parse()
        load()
        work()
        write()

    except FileNotFoundError as e:
        logging.error(f"{e} does not exists")
        sys.exit(1)

    except Exception as e:
        logging.error(e)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__": 
    main()