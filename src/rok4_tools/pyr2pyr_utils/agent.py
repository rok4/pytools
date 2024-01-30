import logging
import os
import tempfile
from typing import Dict, List, Tuple, Union

from rok4 import storage
from rok4.pyramid import Pyramid


def work(config: Dict, split: int) -> None:
    """Agent steps : make slabs' copy

    Expects the configuration, the todo list and the optionnal last done slab name : if exists, work
    does not start from the beginning, but after the last copied slab. This file contains only the
    destination path of the last processed slab.

    For each line in the todo list, a slab copy is done.

    Args:
        config (Dict): PYR2PYR configuration
        split (int): Split number

    Raises:
        Exception: Cannot get todo list
        Exception: Invalid todo list line
        storageError: Slab copy issue
        MissingEnvironmentError: Missing object storage informations
    """

    # On récupère la todo list sous forme de fichier temporaire
    try:
        todo_list_obj = tempfile.NamedTemporaryFile(mode="r", delete=False)
        storage.copy(
            os.path.join(config["process"]["directory"], f"todo.{split}.list"),
            f"file://{todo_list_obj.name}",
        )

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location: {e}")

    last_done_slab = None
    have_to_work = True
    last_done_fo = os.path.join(config["process"]["directory"], f"slab.{split}.last")

    try:
        if storage.exists(last_done_fo):
            last_done_slab = storage.get_data_str(last_done_fo)
            logging.info(
                f"The last done slab file exists, last slab to have been copied is {last_done_slab}"
            )
            have_to_work = False

        # On ouvre à nouveau en lecture le fichier pour avoir le contenu après la copie
        todo_list_obj = open(todo_list_obj.name)

        for line in todo_list_obj:
            line = line.rstrip()
            parts = line.split(" ")

            if (len(parts) != 3 and len(parts) != 4) or parts[0] != "cp":
                raise Exception(
                    f"Invalid todo list line: we need a cp command and 3 or 4 more elements (source and destination): {line}"
                )

            if not have_to_work:
                if parts[2] == last_done_slab:
                    # On est retombé sur la dernière dalles traitées, on passe à la suivante mais on arrête de passer
                    logging.info(f"Last copied slab reached, copies can start again")
                    have_to_work = True

                continue

            slab_md5 = None
            if len(parts) == 4:
                slab_md5 = parts[3]

            storage.copy(parts[1], parts[2], slab_md5)
            last_done_slab = parts[2]

        # On nettoie les fichiers locaux et comme tout s'est bien passé, on peut supprimer aussi le fichier local du travail fait
        todo_list_obj.close()
        storage.remove(f"file://{todo_list_obj.name}")
        storage.remove(last_done_fo)

    except Exception as e:
        if last_done_slab is not None:
            storage.put_data_str(last_done_slab, last_done_fo)
        raise Exception(f"Cannot process the todo list: {e}")
