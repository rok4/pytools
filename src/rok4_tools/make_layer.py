#!/usr/bin/env python3

import argparse
import logging
import sys

from rok4.layer import Layer

from rok4_tools import __version__

# Default logger
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=logging.INFO)

args = None


def parse() -> None:
    """Parse call arguments and check values

    Exit program if an error occured
    """

    global args

    # CLI call parser
    parser = argparse.ArgumentParser(
        prog="make-layer",
        description="Tool to generate layer descriptor from pyramids' descriptor",
        epilog="",
    )

    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)

    parser.add_argument(
        "--pyramids",
        metavar="storage://path/to/pyr.json[>BOTTOM>TOP]",
        action="extend",
        nargs="+",
        type=str,
        dest="pyramids",
        help="Pyramids' descriptors, with extrem levels to use if not all levels have to be used",
        required=True,
    )

    parser.add_argument(
        "--name",
        metavar="my_data",
        action="store",
        dest="name",
        help="Layer's technical name",
        required=True,
    )

    parser.add_argument(
        "--styles",
        metavar="normal",
        action="extend",
        nargs="+",
        type=str,
        default=["normal"],
        dest="styles",
        help="Styles ID available for the layer (no controls, ID are added as provided)",
        required=False,
    )

    parser.add_argument(
        "--title",
        metavar="my data",
        action="store",
        dest="title",
        help="Layer title",
        required=False,
    )

    parser.add_argument(
        "--abstract",
        metavar="my data description",
        action="store",
        dest="abstract",
        help="Layer description",
        required=False,
    )

    parser.add_argument(
        "--resampling",
        choices=["nn", "linear", "bicubic", "lanczos_2", "lanczos_3", "lanczos_4"],
        action="store",
        dest="abstract",
        help="Layer resampling",
        required=False,
    )

    parser.add_argument(
        "--directory",
        action="store",
        dest="directory",
        metavar="s3://layers_bucket",
        help="Directory (file or object) where to write layer's descriptor. Print in standard output if not provided",
        required=False,
    )

    args = parser.parse_args()


def work() -> None:
    """Load informations and write layer descriptor

    If the directory option is provided, descriptor will be written in it, else it is print into standard output.

    Raises:
        Exception: name contains forbidden characters or used pyramids do not shared same parameters (format, tms...)
        MissingEnvironmentError: Missing object storage informations
        StorageError: Storage write issue
    """

    # Chargement des pyramides à utiliser dans la couche
    pyramids = []
    for p in args.pyramids:
        if p.find(">") != -1:
            # Les niveaux du haut et du bas sont précisés
            descriptor, bottom, top = p.split(">", 2)
        else:
            # On utilisera la pyramide dans son intégralité
            descriptor = p
            bottom = None
            top = None

        pyramids.append({"path": descriptor, "bottom_level": bottom, "top_level": top})

    name = args.name
    kwa = vars(args)
    # On supprime ces deux clés pour qu'elles ne rentre pas en conflit avec les paramètres positionnels dans le constructeur de Layer
    del kwa["pyramids"]
    del kwa["name"]
    layer = Layer.from_parameters(pyramids, name, **kwa)

    layer.write_descriptor(args.directory)


def main() -> None:
    """Main function

    Return 0 if success, 1 if an error occured
    """

    parse()

    try:
        work()

    except Exception as e:
        logging.error(e)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
