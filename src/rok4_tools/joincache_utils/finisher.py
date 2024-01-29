import logging
import os
import tempfile
from typing import Dict, List, Tuple, Union

from rok4 import storage
from rok4.pyramid import Pyramid

from rok4_tools.global_utils.source import SourcePyramids


def work(config: Dict) -> None:
    """Finisher steps : finalize the pyramid's processing

    Expects the configuration and all todo lists. Write the output pyramid's descriptor to the final location,
    write the output pyramid's list to the final location (from the todo lists) and remove the todo lists

    Args:
        config (Dict): JOINCACHE configuration

    Raises:
        Exception: Cannot load the input or output pyramid
        Exception: Cannot write output pyramid's descriptor
        Exception: Cannot concatenate splits' done lists and write the final output pyramid's list to the final location
    """

    datasources = []
    for i in range(len(config["datasources"])):
        sources = SourcePyramids(
            config["datasources"][i]["bottom"],
            config["datasources"][i]["top"],
            config["datasources"][i]["source"]["descriptors"],
        )
        datasources.append(sources)

    # Chargement de la pyramide à écrire
    storage_pyramid = {
        "type": datasources[0].pyramids[0].storage_type,
        "root": config["pyramid"]["root"],
    }
    try:
        to_pyramid = Pyramid.from_other(
            datasources[0].pyramids[0],
            config["pyramid"]["name"],
            storage_pyramid,
            mask=config["pyramid"]["mask"],
        )
    except Exception as e:
        raise Exception(
            f"Cannot create the destination pyramid descriptor from the source one: {e}"
        )

    for sources in datasources:
        from_pyramids = sources.pyramids
        levels = from_pyramids[0].get_levels(sources.bottom, sources.top)
        for level in levels:
            try:
                to_pyramid.delete_level(level.id)
            except:
                pass
            info = sources.info_level(level.id)
            to_pyramid.add_level(level.id, info[0], info[1], info[2])

    try:
        to_pyramid.write_descriptor()
    except Exception as e:
        raise Exception(f"Cannot write output pyramid's descriptor to final location: {e}")

    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as list_file_obj:
            list_file_tmp = list_file_obj.name

            # Écriture de l'en-tête du fichier liste, avec toutes les racines des pyramides utilisées
            to_root = os.path.join(to_pyramid.storage_root, to_pyramid.name)
            list_file_obj.write(f"0={to_root}\n")

            todo_list_obj = tempfile.NamedTemporaryFile(mode="r", delete=False)
            storage.copy(
                os.path.join(config["process"]["directory"], f"todo.finisher.list"),
                f"file://{todo_list_obj.name}",
            )

            used_pyramids_roots = {}

            # On ouvre à nouveau en lecture le fichier pour avoir le contenu après la copie
            todo_list_obj = open(todo_list_obj.name)
            for line in todo_list_obj:
                line = line.rstrip()
                list_file_obj.write(f"{line}\n")
                index, root = line.split("=")
                used_pyramids_roots[index] = root

            todo_list_obj.close()
            storage.remove(f"file://{todo_list_obj.name}")
            storage.remove(os.path.join(config["process"]["directory"], f"todo.finisher.list"))

            list_file_obj.write("#\n")

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

                    if parts[0] == "w2c":
                        storage_type, path, tray, base_name = storage.get_infos_from_path(parts[1])
                        # La dalle a été recalculée, elle appartient donc à la pyramide de sortie
                        path = path.replace(to_root, "0")
                        list_file_obj.write(f"{path}\n")

                    elif parts[0] == "link":
                        storage_type, path, tray, base_name = storage.get_infos_from_path(parts[2])
                        # On a fait un lien, on met donc dans la liste la racine de la pyramide source
                        path = path.replace(used_pyramids_roots[parts[3]], parts[3])
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
