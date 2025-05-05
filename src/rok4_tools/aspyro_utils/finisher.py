import logging
import os
import subprocess
import tempfile
from typing import Dict

from rok4 import storage
from rok4.enums import SlabType, StorageType
from rok4.pyramid import Pyramid


def work(config: Dict) -> None:
    """Agent steps : make slabs' copute

    Expects the configuration, all todo lists and the optionnal last done slab name : if exists, work
    does not start from the beginning, but after the last copied slab. This file contains only the
    destination path of the last processed slab.

    Args:
        config (Dict): ASPYRO configuration

    Raises:
        Exception: Cannot get todo list
        Exception: Invalid todo list line
        StorageError: Slab compute issue
        MissingEnvironmentError: Missing object storage informations
    """

    # On récupère la todo list sous forme de fichier temporaire
    try:
        todo_list_obj = tempfile.NamedTemporaryFile(mode="r", delete=False)
        storage.copy(
            os.path.join(config["process"]["directory"], "todo.finisher.list"),
            f"file://{todo_list_obj.name}",
        )

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location: {e}")

    last_done_slab = None
    have_to_work = True
    last_done_fo = os.path.join(config["process"]["directory"], "slab.finisher.last")

    # On récupéère l'éventuelle dernière dalle traitée, pour faire de la reprise sur erreur
    try:
        if storage.exists(last_done_fo):
            last_done_slab = storage.get_data_str(last_done_fo)
            # Format de la dalle : level_column_row
            logging.info(
                f"The last done slab file exists, last slab to have been copied is {last_done_slab}"
            )
            have_to_work = False

    except Exception as e:
        raise Exception(f"Cannot get last slab done: {e}")

    try:
        # On ouvre à nouveau en lecture le fichier pour avoir le contenu après la copie

        todo_list_obj = open(todo_list_obj.name)
        cut_level = None
        width_getmap_count = None
        height_getmap_count = None
        download_extension = None
        getmap_extension = None
        output_pyramid = None

        for line in todo_list_obj:
            line = line.rstrip()
            parts = line.split(" ")

            cmd = parts.pop(0)
            if cmd == "levels":
                parts.pop(0)
                cut_level = parts.pop(0)
                parts.pop(0)

            elif cmd == "getmap_infos":
                width_getmap_count = int(parts.pop(0))
                height_getmap_count = int(parts.pop(0))
                parts.pop(0)
                download_extension = parts.pop(0)
                samplesperpixel = parts.pop(0)
                sampleformat = parts.pop(0)

                # L'extension finale d'une dalle moissonnée est celle de téléchargement si on la télécharge en une fois
                # tif sinon
                if width_getmap_count * height_getmap_count > 1:
                    getmap_extension = "tif"
                else:
                    getmap_extension = download_extension

                config["pyramid"]["pixel"] = {
                    "samplesperpixel": int(samplesperpixel),
                    "sampleformat": sampleformat,
                }

                # Chargement de la pyramide à écrire
                try:
                    output_pyramid = Pyramid.from_parameters(config["pyramid"])
                    output_pyramid.load_list()
                    output_pyramid_root = f"{output_pyramid.storage_root}/{output_pyramid.name}"
                except Exception as e:
                    raise Exception(
                        f"Cannot create the output pyramid descriptor from the parameters and load its list: {e}"
                    )

            elif cmd == "m4t":
                level = parts.pop(0)
                col = int(parts.pop(0))
                row = int(parts.pop(0))

                if not have_to_work:
                    # On n'a toujours pas repris le travail, on regarde si on n'est justement pas sur la dernière dalle traitée
                    if f"{level}_{col}_{row}" == last_done_slab:
                        # On est retombé sur la dernière dalles traitées, on passe à la suivante mais on arrête de passer
                        logging.info("Last copied slab reached, work can start again")
                        have_to_work = True

                    continue

                below_cmd = parts.pop(0)
                below_level = parts.pop(0)
                slab_path = output_pyramid.get_slab_path_from_infos(
                    SlabType.DATA, level, col, row, False
                )
                full_slab_path = f"{output_pyramid_root}/{slab_path}"

                output_pyramid.upsert_slab(
                    SlabType.DATA, level, col, row, output_pyramid_root, slab_path
                )

                m4t_cmd = f"merge4tiff -n {output_pyramid.nodata} -io /tmp/{level}_{col}_{row}.tif"
                to_remove = []
                while len(parts) > 0:
                    extension = "tif"
                    # Si le merge4tiff a en entrée des dalles moissonnées, celles ci peuvent avoir une extension différente
                    if below_cmd == "getmap":
                        extension = getmap_extension

                    below_col = int(parts.pop(0))
                    below_row = int(parts.pop(0))
                    output_pyramid.get_slab_path_from_infos(
                        SlabType.DATA, below_level, below_col, below_row
                    )

                    if below_level == cut_level:
                        # Les dalles en entrée du merge4tiff appartiennent au niveau de coupure
                        # C'est à dire qu'elle ont été générée par les agents, elles sont donc sur l'espace partagé
                        # Il faut commencer par les récupérer
                        shared_slab = os.path.join(
                            config["process"]["directory"],
                            f"{below_level}_{below_col}_{below_row}.{extension}",
                        )
                        storage.copy(
                            shared_slab,
                            f"file:///tmp/{below_level}_{below_col}_{below_row}.{extension}",
                        )
                        to_remove.append(shared_slab)

                    ind = below_col % 2 + 2 * (below_row % 2) + 1
                    m4t_cmd += f" -i{ind} /tmp/{below_level}_{below_col}_{below_row}.{extension}"
                    to_remove.append(
                        f"file:///tmp/{below_level}_{below_col}_{below_row}.{extension}"
                    )

                try:
                    subprocess.check_output(m4t_cmd, shell=True, text=True)
                except subprocess.CalledProcessError as e:
                    raise Exception(f"merge4tiff raises an error : {e.output}")

                if output_pyramid.storage_type == StorageType.FILE:
                    # Il faut créer le dossier cible dans lequel la dalle doit aller
                    os.makedirs(os.path.dirname(full_slab_path), exist_ok=True)

                try:
                    subprocess.check_output(
                        f"work2cache /tmp/{level}_{col}_{row}.tif {output_pyramid.storage_type.value}{full_slab_path} -c {output_pyramid.compression.name.lower()} -t {output_pyramid.tms.get_level(level).tile_width} {output_pyramid.tms.get_level(level).tile_height}",
                        shell=True,
                        text=True,
                    )
                except subprocess.CalledProcessError as e:
                    raise Exception(f"work2cache raises an error : {e.output}")

                # Tout s'est bien passé, on nettoie les images de travail
                for work in to_remove:
                    storage.remove(work)

                last_done_slab = f"{level}_{col}_{row}"

            else:
                raise Exception(f"Cannot process the line (command {cmd}): {line}")

    except Exception as e:
        if last_done_slab is not None:
            storage.put_data_str(last_done_slab, last_done_fo)
        raise Exception(f"Cannot process the todo list: {e}")

    storage.remove(last_done_fo)

    # On va faire une passe sur les todo listes des agents pour calculer la liste complète de la pyramide
    try:
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

                cmd = parts.pop(0)
                if cmd == "getmap" or cmd == "m4t":
                    level = parts.pop(0)
                    col = int(parts.pop(0))
                    row = int(parts.pop(0))
                    slab_path = output_pyramid.get_slab_path_from_infos(
                        SlabType.DATA, level, col, row, False
                    )

                    output_pyramid.upsert_slab(
                        SlabType.DATA, level, col, row, output_pyramid_root, slab_path
                    )

            todo_list_obj.close()
            storage.remove(f"file://{todo_list_obj.name}")
            storage.remove(os.path.join(config["process"]["directory"], f"todo.{i+1}.list"))

    except Exception as e:
        raise Exception(f"Cannot compile the agents todo list: {e}")

    try:
        output_pyramid.write_list()
    except Exception as e:
        raise Exception(f"Cannot write the output pyramid's list: {e}")

    storage.remove(os.path.join(config["process"]["directory"], "todo.finisher.list"))
