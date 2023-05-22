from typing import Dict, List, Tuple, Union
import tempfile
import itertools
import logging
import os

from rok4.Pyramid import Pyramid
from rok4 import Storage

def work(config: Dict):
    """Master steps : prepare and split copies to do

    Inputs:
    - Configuration

    Outputs:
    - Todo lists

    Steps:
    - Load the input pyramid form the descriptor
    - Write the todo lists, splitting the copies to do

    Args:
        config (dict): PYR2PYR configuration
    """

    # Chargement de la pyramide à recopier
    try:
        from_pyramid = Pyramid.from_descriptor(config["from"]["descriptor"])
    except Exception as e:
        raise Exception(f"Cannot load source pyramid descriptor: {e}")

    # Chargement de la pyramide à écrire
    try:
        to_pyramid = Pyramid.from_other(from_pyramid, config["to"]["name"], config["to"]["storage"])
    except Exception as e:
        raise Exception(f"Cannot create the destination pyramid descriptor from the source one: {e}")
        
    # Ouverture des flux vers les listes de recopies à faire
    file_objects = []
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
            file_objects.append(tmp)

    except Exception as e:
        raise Exception(f"Cannot open stream to write todo lists: {e}")

    round_robin = itertools.cycle(file_objects)

    
    # Copie de la liste dans un fichier temporaire (cette liste peut être un objet)
    try:
        from_list_obj = tempfile.NamedTemporaryFile(mode='r', delete=False)
        Storage.copy(from_pyramid.list, f"file://{from_list_obj.name}")
        from_list_obj.close()
    except Exception as e:
        raise Exception(f"Cannot copy source pyramid's slabs list to temporary location: {e}")

    header = True
    roots = dict()

    # Parcours des dalles de la pyramide en entrée et constitution des todo lists
    with open(from_list_obj.name, "r") as listin:

        from_s3_cluster = from_pyramid.storage_s3_cluster

        for line in listin:
            line = line.rstrip()
            
            if line == "#":
                header = False
                continue

            if header:
                root_id, root_path = line.split("=", 1)
                if from_s3_cluster is None:
                    roots[root_id] = root_path
                else:
                    # On a un nom de cluster S3, on l'ajoute au nom du bucket dans les racines
                    root_bucket, root_path = root_path.split("/", 1)
                    roots[root_id] = f"{root_bucket}@{from_s3_cluster}/{root_path}"

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
    
    # Copie des listes de recopies à l'emplacement partagé (peut être du stockage objet)
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = file_objects[i]
            tmp.close()
            Storage.copy(f"file://{tmp.name}", os.path.join(config["process"]["directory"], f"todo.{i+1}.list"))
            Storage.remove(f"file://{tmp.name}")
        
        Storage.remove(f"file://{from_list_obj.name}")

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location and clean: {e}")
