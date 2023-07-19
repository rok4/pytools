from typing import Dict, List, Tuple, Union
import tempfile
import logging
import os

from rok4.pyramid import Pyramid
from rok4 import Storage


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
        StorageError: Slab copy issue
        MissingEnvironmentError: Missing object storage informations
    """

    # On récupère la todo list sous forme de fichier temporaire
    try:
        todo_list_obj = tempfile.NamedTemporaryFile(mode="r", delete=False)
        Storage.copy(
            os.path.join(config["process"]["directory"], f"todo.{split}.list"),
            f"file://{todo_list_obj.name}",
        )

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location: {e}")

    last_done_slab = None
    last_done_fo = os.path.join(config["process"]["directory"], f"slab.{split}.last")

    try:
        if Storage.exists(last_done_fo):
            last_done_slab = Storage.get_data_str(last_done_fo)
            logging.debug(
                f"The last done slab file exists, last slab to have been copied is {last_done_slab}"
            )

        for line in todo_list_obj:
            line = line.rstrip()
            parts = line.split(" ")

            if (len(parts) != 3 and len(parts) != 4) or parts[0] != "cp":
                raise Exception(
                    f"Invalid todo list line: we need a cp command and 3 or 4 more elements (source and destination): {line}"
                )

            if last_done_slab is not None:
                if parts[2] == last_done_slab:
                    # On est retombé sur la dernière dalles traitées, on passe à la suivante mais on arrête de passer
                    logging.debug(f"Last copied slab reached, copies can start again")
                    last_done_slab = None

                next

            slab_md5 = None
            if len(parts) == 4:
                slab_md5 = parts[3]

            Storage.copy(parts[1], parts[2], slab_md5)
            last_done_slab = parts[2]

        # On nettoie les fichiers locaux et comme tout s'est bien passé, on peut supprimer aussi le fichier local du travail fait
        todo_list_obj.close()
        Storage.remove(f"file://{todo_list_obj.name}")
        Storage.remove(last_done_fo)

    except Exception as e:
        if last_done_slab is not None:
            Storage.put_data_str(last_done_slab, last_done_fo)
        raise Exception(f"Cannot process the todo list: {e}")
