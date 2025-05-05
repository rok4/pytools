import logging
import os
import shutil
import subprocess
import tempfile
from typing import Dict

from rok4 import storage
from rok4.enums import SlabType, StorageType
from rok4.pyramid import Pyramid


def work(config: Dict, split: int) -> None:
    """Agent steps : make slabs' copute

    Expects the configuration, the todo list and the optionnal last done slab name : if exists, work
    does not start from the beginning, but after the last copied slab. This file contains only the
    destination path of the last processed slab.

    Args:
        config (Dict): ASPYRO configuration
        split (int): Split number

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
            os.path.join(config["process"]["directory"], f"todo.{split}.list"),
            f"file://{todo_list_obj.name}",
        )

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location: {e}")

    last_done_slab = None
    have_to_work = True
    last_done_fo = os.path.join(config["process"]["directory"], f"slab.{split}.last")

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
        url = None
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
                url = parts.pop(0)
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
                except Exception as e:
                    raise Exception(
                        f"Cannot create the output pyramid descriptor from the parameters: {e}"
                    )

            elif cmd == "getmap":
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

                slab_path = output_pyramid.get_slab_path_from_infos(SlabType.DATA, level, col, row)

                # Tous les éléments qui restent sont des bboxes
                bboxes = parts
                if len(bboxes) != width_getmap_count * height_getmap_count:
                    raise Exception(
                        f"bboxes count is not equal to count of getmap to do to compute the slab : {len(bboxes)} bboxes != {width_getmap_count}x{height_getmap_count} getmaps"
                    )

                working_slab_path = f"/tmp/{level}_{col}_{row}.{getmap_extension}"
                if width_getmap_count * height_getmap_count > 1:
                    os.mkdir(f"/tmp/{level}_{col}_{row}")
                    i = 1
                    for bb in bboxes:
                        storage.copy(
                            f"{url}&BBOX={bb}",
                            f"file:///tmp/{level}_{col}_{row}/{i}.{download_extension}",
                        )
                        i += 1

                    try:
                        subprocess.check_output(
                            f"composeNtiff -s /tmp/{level}_{col}_{row}/ -g {width_getmap_count} {height_getmap_count} {working_slab_path}",
                            shell=True,
                            text=True,
                        )
                    except subprocess.CalledProcessError as e:
                        shutil.rmtree(f"/tmp/{level}_{col}_{row}")
                        raise Exception(f"composeNtiff raises an error: {e.output}")

                    shutil.rmtree(f"/tmp/{level}_{col}_{row}")
                else:
                    storage.copy(f"{url}&BBOX={bboxes[0]}", f"file://{working_slab_path}")

                if output_pyramid.storage_type == StorageType.FILE:
                    # Il faut créer le dossier cible dans lequel la dalle doit aller
                    # slab_path contient le prefixe file:// qu'il faut supprimer pour que makedirs fonctionne
                    os.makedirs(os.path.dirname(slab_path[7:]), exist_ok=True)

                try:
                    subprocess.check_output(
                        f"work2cache {working_slab_path} {slab_path} -c {output_pyramid.compression.name.lower()} -t {output_pyramid.tms.get_level(level).tile_width} {output_pyramid.tms.get_level(level).tile_height}",
                        shell=True,
                        text=True,
                    )
                except subprocess.CalledProcessError as e:
                    raise Exception(f"work2cache raises an error : {e.output}")

                if level == cut_level:
                    shared_slab = os.path.join(
                        config["process"]["directory"], f"{level}_{col}_{row}.{getmap_extension}"
                    )
                    storage.copy(f"file://{working_slab_path}", shared_slab)
                    storage.remove(f"file://{working_slab_path}")

                last_done_slab = f"{level}_{col}_{row}"

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
                slab_path = output_pyramid.get_slab_path_from_infos(SlabType.DATA, level, col, row)

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
                    # slab_path contient le prefixe file:// qu'il faut supprimer pour que makedirs fonctionne
                    os.makedirs(os.path.dirname(slab_path[7:]), exist_ok=True)

                try:
                    subprocess.check_output(
                        f"work2cache /tmp/{level}_{col}_{row}.tif {slab_path} -c {output_pyramid.compression.name.lower()} -t {output_pyramid.tms.get_level(level).tile_width} {output_pyramid.tms.get_level(level).tile_height}",
                        shell=True,
                        text=True,
                    )
                except subprocess.CalledProcessError as e:
                    raise Exception(f"work2cache raises an error : {e.output}")

                if level == cut_level:
                    shared_slab = os.path.join(
                        config["process"]["directory"], f"{level}_{col}_{row}.tif"
                    )
                    storage.copy(f"file:///tmp/{level}_{col}_{row}.tif", shared_slab)
                    storage.remove(f"file:///tmp/{level}_{col}_{row}.tif")

                # Tout s'est bien passé, on nettoie les images de travail
                for work in to_remove:
                    storage.remove(work)

                last_done_slab = f"{level}_{col}_{row}"

            else:
                raise Exception(f"Cannot process the line (command {cmd}): {line}")

        # On nettoie les fichiers locaux et comme tout s'est bien passé, on peut supprimer aussi le fichier local du travail fait
        todo_list_obj.close()
        storage.remove(f"file://{todo_list_obj.name}")
        storage.remove(last_done_fo)

    except Exception as e:
        if last_done_slab is not None:
            storage.put_data_str(last_done_slab, last_done_fo)
        raise Exception(f"Cannot process the todo list: {e}")
