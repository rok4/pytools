import os
import tempfile
from typing import Dict, List, Tuple, Union

from rok4 import storage
from rok4.enums import SlabType
from rok4.pyramid import Level, Pyramid


def work(config: Dict, split: int) -> None:
    """Agent steps : make links or merge images

    Expects the configuration, the todo list and the optionnal last done slab name : if exists, work
    does not start from the beginning, but after the last copied slab. This file contains only the
    destination path of the last processed slab.

    A line in the todo list is either a slab's copy from pyramid format to work format, or a merge of
    stacking slabs or a slab's copy from work format to pyramid format.

    Args:
        config (Dict): JOINCACHE configuration
        split (int): Split number

    Raises:
        Exception: Cannot get todo list
        Exception: Cannot load the input or output pyramid
        Exception: Cannot process todo lists
        Exception: System command raises an error
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

    try:
        pyramid = Pyramid.from_descriptor(config["datasources"][0]["source"]["descriptors"][0])
    except Exception as e:
        raise Exception(
            f"Cannot load source pyramid descriptor : {config['datasources'][0]['source']['descriptors'][0]} : {e}"
        )

    last_done_slab = None
    last_done_fo = os.path.join(config["process"]["directory"], f"slab.{split}.last")
    have_to_work = True

    try:
        if storage.exists(last_done_fo):
            last_done_slab = storage.get_data_str(last_done_fo)
            logging.info(
                f"The last done slab file exists, last slab to have been copied is {last_done_slab}"
            )
            have_to_work = False

        raster_specifications = pyramid.raster_specifications
        format = pyramid.format
        compression = format.split("_")[1].lower()
        if "UINT" in format:
            format_channel = "uint"
        elif "FLOAT" in format:
            format_channel = "float"
        if "8" in format:
            bits_channel = "8"
        elif "32" in format:
            bits_channel = "32"

        multiple_slabs = False
        with open(todo_list_obj.name) as file:
            for line in file:
                line = line.rstrip()
                parts = line.split(" ")

                if parts[0] == "link":
                    if not have_to_work:
                        if parts[1] == last_done_slab:
                            # On est retombé sur la dernière dalles traitées, on passe à la suivante mais on arrête de passer
                            logging.info(f"Last copied slab reached, copies can start again")
                            have_to_work = True

                        continue

                    storage.link(parts[2], parts[1])

                if parts[0] == "c2w":
                    if not have_to_work:
                        continue

                    if not multiple_slabs:
                        i = 0
                        data_file = tempfile.NamedTemporaryFile(
                            mode="r", delete=False, suffix=".tif"
                        )
                        result_value = os.system(f"cache2work -c zip {parts[1]} {data_file.name}")
                        if result_value != 0:
                            raise Exception(f"cache2work raises an error")
                        data = [data_file]
                        mask = [""]
                        multiple_slabs = True
                    else:
                        slab_type = pyramid.get_infos_from_slab_path(parts[1])[0]
                        if slab_type == SlabType.MASK:
                            mask_file = tempfile.NamedTemporaryFile(
                                mode="r", delete=False, suffix=".tif"
                            )
                            result_value = os.system(
                                f"cache2work -c zip {parts[1]} {mask_file.name}"
                            )
                            if result_value != 0:
                                raise Exception(f"cache2work raises an error")
                            mask[i] = mask_file
                        else:
                            i += 1
                            data_file = tempfile.NamedTemporaryFile(
                                mode="r", delete=False, suffix=".tif"
                            )
                            result_value = os.system(
                                f"cache2work -c zip {parts[1]} {data_file.name}"
                            )
                            if result_value != 0:
                                raise Exception(f"cache2work raises an error")
                            data += [data_file]
                            mask += [""]

                if parts[0] == "oNt":
                    if not have_to_work:
                        continue

                    result = tempfile.NamedTemporaryFile(mode="r", delete=False, suffix=".tif")
                    file_tiff = f"{result.name}"
                    if config["pyramid"]["mask"]:
                        result_mask = tempfile.NamedTemporaryFile(
                            mode="r", delete=False, suffix=".tif"
                        )
                        file_tiff += f" {result_mask.name}\n"
                    else:
                        file_tiff += "\n"
                    for i in range(len(data) - 1, -1, -1):
                        file_tiff += f"{data[i].name}"
                        if mask[i] != "":
                            if i == 0:
                                file_tiff += f" {mask[i].name}"
                            else:
                                file_tiff += f" {mask[i].name}\n"
                        else:
                            if i != 0:
                                file_tiff += "\n"
                    fichier = tempfile.NamedTemporaryFile(mode="r", delete=False, suffix=".txt")
                    with open(fichier.name, "w") as f:
                        f.write(file_tiff)
                    result_value = os.system(
                        f"overlayNtiff -f {fichier.name} -m TOP -b {raster_specifications['nodata']} -c zip -s {raster_specifications['channels']} -p {raster_specifications['photometric']}"
                    )
                    if result_value != 0:
                        raise Exception(f"overlayNtiff raises an error")
                    storage.remove(f"file://{fichier.name}")
                    for i in range(len(data)):
                        storage.remove(f"file://{data[i].name}")
                        pass
                    for i in range(len(mask)):
                        if mask[i] != "":
                            pass
                            storage.remove(f"file://{mask[i].name}")
                    multiple_slabs = False

                if parts[0] == "w2c":
                    if not have_to_work:
                        if parts[1] == last_done_slab:
                            # On est retombé sur la dernière dalles traitées, on passe à la suivante mais on arrête de passer
                            logging.info(f"Last copied slab reached, copies can start again")
                            have_to_work = True

                        continue

                    to_tray = storage.get_infos_from_path(parts[1])[2]
                    if to_tray != "":
                        os.makedirs(to_tray, exist_ok=True)

                    slab_type = pyramid.get_infos_from_slab_path(parts[1])[0]
                    if slab_type == SlabType.DATA:
                        level = pyramid.get_infos_from_slab_path(parts[1])[1]
                        tile_width = pyramid.tms.get_level(level).tile_width
                        tile_heigth = pyramid.tms.get_level(level).tile_heigth
                        result_value = os.system(
                            f"work2cache -c {compression} -t {tile_width} {tile_heigth} -a {format_channel} -b {bits_channel} -s {raster_specifications['channels']} {result.name} {parts[1]}"
                        )
                        if result_value != 0:
                            raise Exception(f"work2cache raises an error")
                        storage.remove(f"file://{result.name}")
                    elif slab_type == SlabType.MASK:
                        level = pyramid.get_infos_from_slab_path(parts[1])[1]
                        tile_width = pyramid.tms.get_level(level).tile_width
                        tile_heigth = pyramid.tms.get_level(level).tile_heigth
                        result_value = os.system(
                            f"work2cache -c zip -t {tile_width} {tile_heigth} -a {format_channel} -b {bits_channel} -s {raster_specifications['channels']} {result_mask.name} {parts[1]}"
                        )
                        if result_value != 0:
                            raise Exception(f"work2cache raises an error")
                        storage.remove(f"file://{result_mask.name}")

        # On nettoie les fichiers locaux et comme tout s'est bien passé, on peut supprimer aussi le fichier local du travail fait
        todo_list_obj.close()
        storage.remove(f"file://{todo_list_obj.name}")
        storage.remove(last_done_fo)

    except Exception as e:
        if last_done_slab is not None:
            storage.put_data_str(last_done_slab, last_done_fo)
        raise Exception(f"Cannot process the todo list: {e}")
