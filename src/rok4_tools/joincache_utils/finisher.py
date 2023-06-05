import tempfile
import os

from rok4.Pyramid import Pyramid
from rok4 import Storage
from rok4_tools.global_utils.source import SourceRasterPyramids

def work(config: dict):
    """Finisher steps : finalize the pyramid's transfer

    Inputs:
    - Configuration
    - Todo lists

    Steps:
    - Write the output pyramid's descriptor to the final location
    - Write the output pyramid's list to the final location (from the todo lists)
    - Remove the todo lists

    Args:
        config (dict): joincache configuration
    """

    datasources = []
    for i in range (len(config["datasources"])) :
        sources = SourceRasterPyramids(config["datasources"][i]["bottom"], config["datasources"][i]["top"], config["datasources"][i]["source"]["descriptors"])
        datasources += [sources]

    # Chargement de la pyramide à écrire
    storage = {
    "type" : datasources[0].pyramids[0].storage_type,
    "root" : config["pyramid"]["root"]
    }
    try:
        to_pyramid = Pyramid.from_other(datasources[0].pyramids[0], config["pyramid"]["name"], storage, mask=config["pyramid"]["mask"])
    except Exception as e:
        raise Exception(f"Cannot create the destination pyramid descriptor from the source one: {e}")
    
    for sources in datasources :
        for k in range (int(sources.top), int(sources.bottom) + 1) :
            try :
                to_pyramid.delete_level(str(k))
            except :
                pass
            info = sources.info_level(str(k))
            to_pyramid.add_level(str(k),info[0],info[1],info[2])
    
    try:
        to_pyramid.write_descriptor()
    except Exception as e:
        raise Exception(f"Cannot write output pyramid's descriptor to final location: {e}")
    
    try:

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as list_file_obj:

            list_file_tmp = list_file_obj.name

            # Écriture de l'en-tête du fichier liste : une seule racine, celle de la pyramide en sortie
            to_root = os.path.join(to_pyramid.storage_root, to_pyramid.name)
            list_file_obj.write(f"0={to_root}\n#\n")

            if to_pyramid.storage_s3_cluster is not None:
                # Les chemins de destination contiendront l'hôte du cluster S3 utilisé,
                # Il faut donc l'inclure dans la racine à supprimer des chemins vers les dalles
                to_root = os.path.join(f"{to_pyramid.storage_root}@{to_pyramid.storage_s3_cluster}", to_pyramid.name)

            for i in range(0, config["process"]["parallelization"]):

                todo_list_obj = tempfile.NamedTemporaryFile(mode='r', delete=False)
                Storage.copy(os.path.join(config["process"]["directory"], f"todo.{i+1}.list"), f"file://{todo_list_obj.name}")

                for line in todo_list_obj:
                    line = line.rstrip()
                    parts = line.split(" ")

                    if parts[0] == "link" or parts[0] == "w2c" :

                        storage_type, path, tray, base_name = Storage.get_infos_from_path(parts[1])
                        path = path.replace(to_root, "0")
                        list_file_obj.write(f"{path}\n")
                
                todo_list_obj.close()
                Storage.remove(f"file://{todo_list_obj.name}")
                Storage.remove(os.path.join(config["process"]["directory"], f"todo.{i+1}.list"))

        Storage.copy(f"file://{list_file_tmp}", to_pyramid.list)
        Storage.remove(f"file://{list_file_tmp}")
    
    except Exception as e:
        raise Exception(f"Cannot concatenate splits' done lists and write the final output pyramid's list to the final location: {e}")