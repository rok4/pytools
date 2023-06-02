#!/usr/bin/env python3

import sys
import argparse
import logging
import os
import json
from jsonschema import validate, ValidationError
import jsonschema.validators
from json.decoder import JSONDecodeError
from pathlib import Path

from rok4 import Storage, Pyramid
from rok4_tools import __version__
from rok4_tools.joincache_utils.master import work as joincache_master
from rok4_tools.joincache_utils.agent import work as joincache_agent

# Default logger
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.WARNING)

# CLI call parser
parser = argparse.ArgumentParser(
    prog = 'joincache',
    description = "Tool to generate a pyramid from other compatible pyramid",
    epilog = ''
)

parser.add_argument(
    '--version',
    action='version',
    version='%(prog)s ' + __version__
)

parser.add_argument(
    '--role',
    choices=["master", "agent", "finisher", "example", "check"],
    action='store',
    dest='role',
    help="Script's role",
    required=True
)

parser.add_argument(
    '--conf',
    metavar='storage://path/to/conf.json',
    action='store',
    dest='configuration',
    help='Configuration file or object, JSON format',
    required=False
)

parser.add_argument(
    '--split',
    type=int,
    metavar="N",
    action='store',
    dest='split',
    help='Split number, only required for the agent role',
    required=False
)

args = parser.parse_args()

if args.role != "example" and (args.configuration is None):
    print("joincache: error: argument --conf is required for all roles except 'example'")
    sys.exit(1)

if args.role == "agent" and (args.split is None or args.split < 1):
    print("joincache: error: argument --split is required for the agent role and have to be a positive integer")
    sys.exit(1)

config = dict()
def configuration():
    global config

    # Chargement de la configuration JSON
    config = json.loads(Storage.get_data_str(args.configuration))

    # Validation via le schéma JSON, à côté du script
    path = Path(os.path.abspath(os.path.dirname(__file__)))
    resolver = jsonschema.validators.RefResolver(
        base_uri=f"{path.as_uri()}/",
        referrer=True,
    )
    validate(
        instance=config,
        schema={"$ref": "joincache_utils/schema.json"},
        resolver=resolver,
    )

    # Valeurs par défaut et cohérence avec l'appel
    if "parallelization" not in config["process"]:
        config["process"]["parallelization"] = 1

    if args.role == "agent" and args.split > config["process"]["parallelization"]:
        raise Exception(f"Split number have to be consistent with the parallelization level: {args.split} > {config['process']['parallelization']}")

    if "mask" not in config["process"] :
        config["process"]["mask"] = False
        config["pyramid"]["mask"] = False
    else :
        if "mask" not in config["pyramid"] :
            config["pyramid"]["mask"] = False
        elif config["process"]["mask"] == False and config["pyramid"]["mask"] == True :
            raise Exception(f"The new pyramid cannot have mask if masks are not use during the process")

    # Logger
    if "logger" in config:
        # On supprime l'ancien logger (celui configuré par défaut) et on le reconfigure avec les nouveaux paramètres
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        if "file" in config["logger"]:
            logging.basicConfig(
                level=logging.getLevelName(config["logger"].get("level", "WARNING")),
                format=config["logger"].get("layout", "%(asctime)s %(levelname)s: %(message)s"),
                filename=config["logger"]["file"]
            )
        else:
            logging.basicConfig(
                level=logging.getLevelName(config["logger"].get("level", "WARNING")),
                format=config["logger"].get("layout", "%(asctime)s %(levelname)s: %(message)s")
            )

def main():
    if args.role == "example":
        # On veut juste afficher la configuration en exemple
        f = open(os.path.join(os.path.dirname(__file__), "joincache_utils/example.json"))
        print(f.read())
        f.close
        sys.exit(0)

    # Configuration
    try:
        configuration()

    except JSONDecodeError as e:
        logging.error(f"{args.configuration} is not a valid JSON file: {e}")
        sys.exit(1)

    except ValidationError as e:
        logging.error(f"{args.configuration} is not a valid configuration file: {e}")
        sys.exit(1)

    except Exception as e:
        logging.error(e)
        sys.exit(1)

    if args.role == "check":
        # On voulait juste valider le fichier de configuration, c'est chose faite
        # Si on est là c'est que tout est bon
        print("Valid configuration !")
        sys.exit(0)

    # Work
    try:

        if args.role == "master":
            joincache_master(config)
        elif args.role == "agent":
            joincache_agent(config, args.split)
        elif args.role == "finisher":
            pass

    except Exception as e:
        logging.error(e)
        sys.exit(1)

        sys.exit(0)
