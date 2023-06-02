import tempfile
import os

from rok4 import Storage
from rok4.Pyramid import Pyramid, Level

def work(config: dict, split: int):
    """Agent steps : make joincache

    Inputs:
    - Configuration
    - Todo list
    - The last done slab name : if exists, work does not start from the beginning, but after the last copied slab. This file contains only the destination path of the last processed slab

    Steps:
    - Write the output pyramid's descriptor to the final location
    - Write the output pyramid's list to the final location (from the todo lists)
    - Remove the todo lists

    Args:
        config (dict): Joincache configuration
        split (int): Split number
    """

    # On récupère la todo list sous forme de fichier temporaire
    try:
        todo_list_obj = tempfile.NamedTemporaryFile(mode='r', delete=False)
        Storage.copy(os.path.join(config["process"]["directory"], f"todo.{split}.list"), f"file://{todo_list_obj.name}")

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location: {e}")
    
    try :
        pyramid = Pyramid.from_descriptor(config["datasources"][0]["source"]["descriptors"][0])
    except Exception as e:
        raise Exception(f"Cannot load source pyramid descriptor : {config['datasources'][0]['source']['descriptors'][0]} : {e}")

    try:
        raster_specifications = pyramid.raster_specifications
        format = pyramid.format
        compression = format.split("_")[1].lower()
        if "UINT" in format :
            format_canal = "uint"
        elif "FLOAT" in format :
            format_canal = "float"
        if "8" in format :
            bits_canal = "8"
        elif "32" in format :
            bits_canal = "32"

        multiple_slabs = False
        for line in todo_list_obj:
            line = line.rstrip()
            parts = line.split(" ")

            if parts[0] == "link" :
                to_tray = Storage.get_infos_from_path(parts[1])[2]
                if to_tray != "":
                    os.makedirs(to_tray, exist_ok=True)

                if Storage.exists(parts[1]) :
                    Storage.remove(parts[1])
                Storage.link(parts[2], parts[1])

            if parts[0] == "c2w" :
                if not multiple_slabs :
                    i=0
                    image = tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".tif")
                    os.system(f"cache2work -c zip {parts[1]} {image.name}")
                    data = [image]
                    mask = [""]
                    multiple_slabs = True
                else :
                    if parts[2] == "MASK" :
                        mask_file = tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".tif")
                        os.system(f"cache2work -c zip {parts[1]} {mask_file.name}")
                        mask[i] = mask_file
                    else :
                        i+=1
                        image = tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".tif")
                        os.system(f"cache2work -c zip {parts[1]} {image.name}")
                        data += [image]
                        mask += [""]

            if parts[0] == "oNt" :
                resultat = tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".tif")
                fichierNtiff = f"{resultat.name}"
                if config["pyramid"]["mask"] :
                    resultat_mask = tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".tif")
                    fichierNtiff += f" {resultat_mask.name}\n"
                else :
                    fichierNtiff += "\n"
                for i in range (len(data)-1,-1,-1) :
                    fichierNtiff += f"{data[i].name}"
                    if mask[i] != "" :
                        if i == 0 :
                            fichierNtiff += f" {mask[i].name}"
                        else :
                            fichierNtiff += f" {mask[i].name}\n"
                    else :
                        if i != 0 :
                            fichierNtiff += "\n"
                fichier = tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".txt")
                with open(fichier.name, 'w') as f :
                    f.write(fichierNtiff)
                os.system(f"overlayNtiff -f {fichier.name} -m TOP -b {raster_specifications['nodata']} -c zip -s {raster_specifications['channels']} -p {raster_specifications['photometric']}")
                Storage.remove(f"file://{fichier.name}")
                for i in range (len(data)) :
                    Storage.remove(f"file://{data[i].name}")
                    pass
                for i in range (len(mask)) :
                    if mask[i] != "" :
                        pass
                        Storage.remove(f"file://{mask[i].name}")
                multiple_slabs = False

            if parts[0] == "w2c" :
                to_tray = Storage.get_infos_from_path(parts[1])[2]
                if to_tray != "":
                    os.makedirs(to_tray, exist_ok=True)

                if parts[2] == "DATA" :
                    level = pyramid.get_infos_from_slab_path(parts[1])[1]
                    tile_width = pyramid.tms.get_level(level).tile_width
                    tile_heigth = pyramid.tms.get_level(level).tile_heigth
                    os.system(f"work2cache -c {compression} -t {tile_width} {tile_heigth} -a {format_canal} -b {bits_canal} -s {raster_specifications['channels']} {resultat.name} {parts[1]}")
                    Storage.remove(f"file://{resultat.name}")
                elif parts[2] == "MASK" :
                    level = pyramid.get_infos_from_slab_path(parts[1])[1]
                    tile_width = pyramid.tms.get_level(level).tile_width
                    tile_heigth = pyramid.tms.get_level(level).tile_heigth
                    os.system(f"work2cache -c zip -t {tile_width} {tile_heigth} -a {format_canal} -b {bits_canal} -s {raster_specifications['channels']} {resultat_mask.name} {parts[1]}")
                    Storage.remove(f"file://{resultat_mask.name}")


        # On nettoie les fichiers locaux et comme tout s'est bien passé, on peut supprimer aussi le fichier local du travail fait
        todo_list_obj.close()
        Storage.remove(f"file://{todo_list_obj.name}")

    except Exception as e:
        raise Exception(f"Cannot process the todo list: {e}")