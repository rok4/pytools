import logging
import os
import tempfile
from typing import Dict, List, Tuple, Union

from rok4 import storage
from rok4.pyramid import Pyramid


def work(config: Dict) -> None:
    """Finisher steps : finalize the pyramid's transfer

    Expects the configuration and all todo lists. Write the output pyramid's descriptor to the final location,
    write the output pyramid's list to the final location (from the todo lists) and remove the todo lists

    Args:
        config (Dict): PYR2PYR configuration

    Raises:
        Exception: Cannot load the input or the output pyramid
        Exception: Cannot write output pyramid's descriptor
        Exception: Cannot concatenate todo lists to write the output pyramid's list
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

    try:
        to_pyramid.write_descriptor()
    except Exception as e:
        raise Exception(f"Cannot write output pyramid's descriptor to final location: {e}")

    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as list_file_obj:
            list_file_tmp = list_file_obj.name

            # Écriture de l'en-tête du fichier liste : une seule racine, celle de la pyramide en sortie
            to_root = os.path.join(to_pyramid.storage_root, to_pyramid.name)
            list_file_obj.write(f"0={to_root}\n#\n")

            if to_pyramid.storage_s3_cluster is not None:
                # Les chemins de destination contiendront l'hôte du cluster S3 utilisé,
                # Il faut donc l'inclure dans la racine à supprimer des chemins vers les dalles
                to_root = os.path.join(
                    f"{to_pyramid.storage_root}@{to_pyramid.storage_s3_cluster}", to_pyramid.name
                )

            for i in range(0, config["process"]["parallelization"]):
                todo_list_obj = tempfile.NamedTemporaryFile(mode="r", delete=False)
                storage.copy(
                    os.path.join(config["process"]["directory"], f"todo.{i+1}.list"),
                    f"file://{todo_list_obj.name}",
                )

                # On ouvre à nouveau en lecture le fichier pour avoir le contenu après la copie
                todo_list_obj = open(todo_list_obj.name)
                for line in todo_list_obj:
                    line = line.rstrip()
                    parts = line.split(" ")

                    if (len(parts) != 3 and len(parts) != 4) or parts[0] != "cp":
                        raise Exception(
                            f"Invalid todo list line: we need a cp command and 3 or 4 more elements (source and destination): {line}"
                        )

                    storage_type, path, tray, base_name = storage.get_infos_from_path(parts[2])
                    path = path.replace(to_root, "0")
                    list_file_obj.write(f"{path}\n")

                todo_list_obj.close()
                storage.remove(f"file://{todo_list_obj.name}")
                storage.remove(os.path.join(config["process"]["directory"], f"todo.{i+1}.list"))

        storage.copy(f"file://{list_file_tmp}", to_pyramid.list)
        storage.remove(f"file://{list_file_tmp}")

    except Exception as e:
        raise Exception(
            f"Cannot concatenate splits' done lists and write the final output pyramid's list to the final location: {e}"
        )
