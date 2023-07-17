from typing import Dict, List, Tuple, Union
import tempfile
import itertools
import logging
import os

from rok4.Pyramid import Pyramid
from rok4 import Storage


def work(config: Dict) -> None:
    """Master steps : prepare and split copies to do

    Load the input pyramid from the descriptor and write the todo lists, splitting the copies to do

    Args:
        config (Dict): PYR2PYR configuration

    Raises:
        Exception: Cannot load the input or the output pyramid
        Exception: Cannot write temporary todo lists
        StorageError: Cannot read source pyramid list
        MissingEnvironmentError: Missing object storage informations
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
        raise Exception(
            f"Cannot create the destination pyramid descriptor from the source one: {e}"
        )

    # Ouverture des flux vers les listes de recopies à faire
    file_objects = []
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False)
            file_objects.append(tmp)

    except Exception as e:
        raise Exception(f"Cannot open stream to write todo lists: {e}")

    round_robin = itertools.cycle(file_objects)

    for (slab_type, level, column, row), infos in from_pyramid.list_generator():
        # On traite une dalle

        if infos["link"] and not config["process"]["follow_links"]:
            # On ne veut pas traiter les dalles symboliques, et c'en est une
            continue

        from_slab_path = Storage.get_path_from_infos(
            from_pyramid.storage_type, infos["root"], infos["slab"]
        )

        if (
            config["process"]["slab_limit"] != 0
            and Storage.get_size(from_slab_path) < config["process"]["slab_limit"]
        ):
            logging.debug(f"Slab {from_slab_path} too small, skip it")
            continue

        to_slab_path = to_pyramid.get_slab_path_from_infos(slab_type, level, column, row)

        if infos["md5"] is None:
            next(round_robin).write(f"cp {from_slab_path} {to_slab_path}\n")
        else:
            next(round_robin).write(f"cp {from_slab_path} {to_slab_path} {infos['md5']}\n")

    # Copie des listes de recopies à l'emplacement partagé (peut être du stockage objet)
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = file_objects[i]
            tmp.close()
            Storage.copy(
                f"file://{tmp.name}",
                os.path.join(config["process"]["directory"], f"todo.{i+1}.list"),
            )
            Storage.remove(f"file://{tmp.name}")

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location and clean: {e}")
