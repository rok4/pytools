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
import tempfile
import itertools

from rok4.Pyramid import Pyramid
from rok4 import Storage

# Default logger
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.WARNING)

# CLI call parser
parser = argparse.ArgumentParser(
    prog = 'pyr2pyr',
    description = "Tool to split the work to do for a pyramid copy and make slabs' copy",
    epilog = ''
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

parser.add_argument(
    '--done',
    metavar="N",
    action='store',
    dest='done',
    help='Temporary file of done work, only required for the agent role',
    required=False
)

args = parser.parse_args()

if args.role != "example" and (args.configuration is None):
    print("pyr2pyr: error: argument --conf is required for all roles execept 'example'")
    sys.exit(1)

if args.role == "agent" and (args.split is None or args.split < 1):
    print("pyr2pyr: error: argument --split is required for the agent role and have to be a positive integer")
    sys.exit(1)

if args.role == "agent" and (args.done is None):
    print("pyr2pyr: error: argument --done is required for the agent role")
    sys.exit(1)

# Tool steps

config = dict()
def configuration():
    global config

    # Chargement de la configuration JSON
    config = json.loads(Storage.get_data_str(args.configuration))

    # Validation via le sch??ma JSON, ?? c??t?? du script
    path = Path(os.path.abspath(os.path.dirname(__file__)))
    resolver = jsonschema.validators.RefResolver(
        base_uri=f"{path.as_uri()}/",
        referrer=True,
    )
    validate(
        instance=config,
        schema={"$ref": "pyr2pyr.schema.json"},
        resolver=resolver,
    )

    # Valeurs par d??faut et coh??rence avec l'appel
    if config["to"]["storage"]["type"] == "FILE" and "depth" not in config["to"]["storage"]:
        config["to"]["storage"]["depth"] = 2

    if "parallelization" not in config["process"]:
        config["process"]["parallelization"] = 1

    if args.role == "agent" and args.split > config["process"]["parallelization"]:
        raise Exception(f"Split number have to be consistent with the parallelization level: {args.split} > {config['process']['parallelization']}")

    if "follow_links" not in config["process"]:
        config["process"]["follow_links"] = False

    if "slab_limit" not in config["process"]:
        config["process"]["slab_limit"] = 0

    # Logger
    if "logger" in config:
        # On supprime l'ancien logger (celui configur?? par d??faut) et on le reconfigure avec les nouveaux param??tres
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


def master_work():
    """Master steps : prepare and split copies to do

    Inputs:
    - Configuration

    Outputs:
    - Todo lists

    Steps:
    - Load the input pyramid form the descriptor
    - Write the todo lists, splitting the copies to do
    """

    # Chargement de la pyramide ?? recopier
    try:
        from_pyramid = Pyramid.from_descriptor(config["from"]["descriptor"])
    except Exception as e:
        raise Exception(f"Cannot load source pyramid descriptor: {e}")

    # Chargement de la pyramide ?? ??crire
    try:
        to_pyramid = Pyramid.from_other(from_pyramid, config["to"]["name"], config["to"]["storage"])
    except Exception as e:
        raise Exception(f"Cannot create the destination pyramid descriptor from the source one: {e}")
        
    # Ouverture des flux vers les listes de recopies ?? faire
    file_objects = []
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
            file_objects.append(tmp)

    except Exception as e:
        raise Exception(f"Cannot open stream to write todo lists: {e}")

    round_robin = itertools.cycle(file_objects)

    # Parcours des dalles de la pyramide en entr??e et constitution des todo lists
    
    # Copie de la liste dans un fichier temporaire (cette liste peut ??tre un objet)
    try:
        from_list_obj = tempfile.NamedTemporaryFile(mode='r', delete=False)
        Storage.copy(from_pyramid.list, f"file://{from_list_obj.name}")
    except Exception as e:
        raise Exception(f"Cannot copy source pyramid's slabs list to temporary location: {e}")

    header = True
    roots = dict()

    for line in from_list_obj:
        line = line.rstrip()
        if line == "#":
            header = False
            continue

        if header:
            root_id, root_path = line.split("=", 1)
            roots[root_id] = root_path
            continue

        # On traite une dalle

        parts = line.split(" ", 1)
        slab_path = parts[0]
        slab_md5 = None
        if len(parts) == 2:
            slab_md5 = parts[1]

        root_id, slab_path = slab_path.split("/", 1)

        if root_id != "0" and not config["process"]["follow_links"]:
            # On ne veut pas traiter les dalles symboliques, et c'en est une
            continue

        from_slab_path = Storage.get_path_from_infos(from_pyramid.storage_type, roots[root_id], slab_path)

        if config["process"]["slab_limit"] != 0 and Storage.get_size(from_slab_path) < config["process"]["slab_limit"]:
            logging.debug(f"Slab {from_slab_path} too small, skip it")
            continue
        
        slab_type, level, column, row = from_pyramid.get_infos_from_slab_path(from_slab_path)

        to_slab_path = to_pyramid.get_slab_path_from_infos(slab_type, level, column, row)

        if slab_md5 is None:
            next(round_robin).write(f"cp {from_slab_path} {to_slab_path}\n")
        else:
            next(round_robin).write(f"cp {from_slab_path} {to_slab_path} {slab_md5}\n")

    from_list_obj.close()
    
    # Copie des listes de recopies ?? l'emplacement partag?? (peut ??tre du stockage objet)
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = file_objects[i]
            tmp.close()
            Storage.copy(f"file://{tmp.name}", os.path.join(config["process"]["directory"], f"todo.{i+1}.list"))
            Storage.remove(f"file://{tmp.name}")
        
        Storage.remove(f"file://{from_list_obj.name}")

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location and clean: {e}")

def agent_work():
    """Agent steps : make slabs' copy

    Inputs:
    - Configuration
    - Todo list
    - The done list : if exists, work does not start from the beginning, but after the last copied slab. This file contains only the destination path of the already processed slabs

    Steps:
    - Write the output pyramid's descriptor to the final location
    - Write the output pyramid's list to the final location (from the todo lists)
    - Remove the todo lists
    """

    # On r??cup??re la todo list sous forme de fichier temporaire
    try:
        todo_list_obj = tempfile.NamedTemporaryFile(mode='r', delete=False)
        Storage.copy(os.path.join(config["process"]["directory"], f"todo.{args.split}.list"), f"file://{todo_list_obj.name}")
        
    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location: {e}")

    try:

        last_done = None

        if os.path.exists(args.done):
            # Le fichier local du travail fait existe d??j??, on en r??cup??re la derni??re ligne
            with open(args.done) as f:
                line = ""
                for line in f:
                    pass
                last_line = line
            
            last_done = last_line.rstrip()
            if last_done is not None and last_done != "":
                logging.debug(f"The done file already exists, last slab to have been copied is {last_done}")
            else:
                # Dans le cas o?? le fichier avait ??t?? cr???? mais vide
                last_done = None

        elif os.path.dirname(args.done) != "":
            os.makedirs(os.path.dirname(args.done), exist_ok=True)

        with open(args.done, "a") as done_list_obj:
            for line in todo_list_obj:
                line = line.rstrip()
                parts = line.split(" ")

                if (len(parts) != 3 and len(parts) != 4) or parts[0] != "cp":
                    raise Exception(f"Invalid todo list line: we need a cp command and 3 or 4 more elements (source and destination): {line}")                   

                if last_done is not None:
                    if parts[2] == last_done:
                        # On est retomb?? sur la derni??re dalles trait??es, on passe ?? la suivante mais on arr??te de passer
                        logging.debug(f"Last copied slab reached, copies can start again")
                        last_done = None

                    next

                slab_md5 = None
                if len(parts) == 4:
                    slab_md5 = parts[3]

                Storage.copy(parts[1], parts[2], slab_md5)
                done_list_obj.write(f"{parts[2]}\n")
        
        # On nettoie les fichiers locaux et comme tout s'est bien pass??, on peut supprimer aussi le fichier local du travail fait
        todo_list_obj.close()
        Storage.remove(f"file://{todo_list_obj.name}")
        Storage.remove(f"file://{args.done}")

    except Exception as e:
        raise Exception(f"Cannot process the todo list: {e}")


def finisher_work():
    """Finisher steps : finalize the pyramid's transfer

    Inputs:
    - Configuration
    - Todo lists

    Steps:
    - Write the output pyramid's descriptor to the final location
    - Write the output pyramid's list to the final location (from the todo lists)
    - Remove the todo lists
    """

    # Chargement de la pyramide ?? recopier
    try:
        from_pyramid = Pyramid.from_descriptor(config["from"]["descriptor"])
    except Exception as e:
        raise Exception(f"Cannot load source pyramid descriptor: {e}")

    # Chargement de la pyramide ?? ??crire
    try:
        to_pyramid = Pyramid.from_other(from_pyramid, config["to"]["name"], config["to"]["storage"])
    except Exception as e:
        raise Exception(f"Cannot create the destination pyramid descriptor from the source one: {e}")

    try:
        to_pyramid.write_descriptor()
    except Exception as e:
        raise Exception(f"Cannot write output pyramid's descriptor to final location: {e}")
    
    try:

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as list_file_obj:

            list_file_tmp = list_file_obj.name

            # ??criture de l'en-t??te du fichier liste : une seule racine, celle de la pyramide en sortie
            to_root = os.path.join(to_pyramid.storage_root, to_pyramid.name)
            list_file_obj.write(f"0={to_root}\n#\n")

            for i in range(0, config["process"]["parallelization"]):

                todo_list_obj = tempfile.NamedTemporaryFile(mode='r', delete=False)
                Storage.copy(os.path.join(config["process"]["directory"], f"todo.{i+1}.list"), f"file://{todo_list_obj.name}")

                for line in todo_list_obj:
                    line = line.rstrip()
                    parts = line.split(" ")

                    if (len(parts) != 3 and len(parts) != 4) or parts[0] != "cp":
                        raise Exception(f"Invalid todo list line: we need a cp command and 3 or 4 more elements (source and destination): {line}")  

                    storage_type, path, tray, base_name = Storage.get_infos_from_path(parts[2])
                    path = path.replace(to_root, "0")
                    list_file_obj.write(f"{path}\n")

                todo_list_obj.close()
                Storage.remove(f"file://{todo_list_obj.name}")
                Storage.remove(os.path.join(config["process"]["directory"], f"todo.{i+1}.list"))

        Storage.copy(f"file://{list_file_tmp}", to_pyramid.list)
        Storage.remove(f"file://{list_file_tmp}")

    except Exception as e:
        raise Exception(f"Cannot concatenate splits' done lists and write the final output pyramid's list to the final location: {e}")

if __name__ == "__main__": 

    if args.role == "example":
        # On veut juste afficher la configuration en exemple
        f = open(os.path.join(os.path.dirname(__file__), "pyr2pyr.example.json"))
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
        # Si on est l?? c'est que tout est bon
        print("Valid configuration !")
        sys.exit(0)

    # Work
    try:
        
        if args.role == "master":
            master_work()
        elif args.role == "agent":
            agent_work()
        elif args.role == "finisher":
            finisher_work()

    except Exception as e:
        logging.error(e)
        sys.exit(1)

    sys.exit(0)