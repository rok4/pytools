import tempfile
import itertools
import os

from rok4.Pyramid import Pyramid, SlabType
from rok4 import Storage
from rok4_tools.global_utils.source import SourceRasterPyramids

def work(config):
    """Master steps : prepare and split copies to do

    Inputs:
    - Configuration

    Outputs:
    - Todo lists

    Steps:
    - Load input pyramids form the descriptor
    - Verification of the pyramids
    - Write the todo lists, splitting the copies to do
    """

    datasources = []
    tms_reference = False
    format_reference = False
    channels_reference = False
    for i in range (len(config["datasources"])) :
        sources = SourceRasterPyramids(config["datasources"][i]["bottom"], config["datasources"][i]["top"], config["datasources"][i]["source"]["descriptors"])
        # Vérification de l'unicité du TMS
        if not tms_reference :
            tms_reference = sources.tms
        elif tms_reference != sources.tms :
            raise Exception(f"Sources pyramids cannot have two different TMS : {tms_reference} and {sources.tms}")

        # Vérification de l'unicité du format
        if not format_reference :
            format_reference = sources.format
        elif format_reference != sources.format :
            raise Exception(f"Sources pyramids cannot have two different format : {format_reference} and {sources.format}")

        # Vérification de l'unicité du nombre de canaux
        if not channels_reference :
            channels_reference = sources.channels
        elif channels_reference != sources.channels :
            raise Exception(f"Sources pyramids cannot have two different numbers of channels : {channels_reference} and {sources.channels}")

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

    # Ouverture des flux vers les listes de recopies à faire
    file_objects = []
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
            file_objects.append(tmp)

    except Exception as e:
        raise Exception(f"Cannot open stream to write todo lists: {e}")

    round_robin = itertools.cycle(file_objects)

    slab_finish = []
    level_finish = []
    for sources in datasources :
        for k in range (int(sources.top), int(sources.bottom) + 1) :
            if str(k) not in level_finish :
                try :
                    to_pyramid.delete_level(str(k))
                except :
                    pass
                info = sources.info_level(str(k))
                to_pyramid.add_level(str(k),info[0],info[1],info[2])
                level_finish += [str(k)]
            else :
                raise Exception(f"Different datasources cannot define the same level : {str(k)}")
            from_pyramids = sources.pyramids

            for i in range (len(from_pyramids)) :
                slabs = from_pyramids[i].list_generator_level(str(k))
                slabs_mask = from_pyramids[i].list_generator_level(str(k))
                for slab in slabs :
                    if slab[0] in slab_finish :
                        continue
                    if slab[0][0].name == "MASK":
                        continue
                    from_slab_path = Storage.get_path_from_infos(from_pyramids[i].storage_type, slab[1]["root"], slab[1]["slab"])
                    process = [from_slab_path]
                    slab_finish += [slab[0]]

                    if config["process"]["mask"]:
                        slab_mask = ((SlabType["MASK"], slab[0][1], slab[0][2], slab[0][3]), slab[1])
                        slab_mask[1]["slab"] = from_pyramids[i].get_slab_path_from_infos(SlabType["MASK"], slab[0][1], slab[0][2], slab[0][3], False)
                        if slab_mask in slabs_mask :
                            mask = [Storage.get_path_from_infos(from_pyramids[i].storage_type, slab_mask[1]["root"], slab_mask[1]["slab"])]
                        else :
                            mask = [""]

                    if not config["process"]["only_links"] :
                        for j in range (i+1,len(from_pyramids)) :
                            slabs_other = from_pyramids[j].list_generator_level(str(k))
                            slabs_other_mask = from_pyramids[j].list_generator_level(str(k))
                            for slab_other in slabs_other :
                                if slab_other[0] == slab[0] :
                                    from_slab_path_other = Storage.get_path_from_infos(from_pyramids[j].storage_type, slab_other[1]["root"], slab_other[1]["slab"])
                                    process += [from_slab_path_other]
                                    if config["process"]["mask"]:
                                        slab_mask_other = ((SlabType["MASK"], slab_other[0][1], slab_other[0][2], slab_other[0][3]), slab_other[1])
                                        slab_mask_other[1]["slab"] = from_pyramids[j].get_slab_path_from_infos(SlabType["MASK"], slab_other[0][1], slab_other[0][2], slab_other[0][3], False)
                                        if slab_mask_other in slabs_other_mask :
                                            mask += [Storage.get_path_from_infos(from_pyramids[i].storage_type, slab_mask_other[1]["root"], slab_mask_other[1]["slab"])]
                                        else :
                                            mask += [""]
                                    continue

                    to_slab_path = to_pyramid.get_slab_path_from_infos(slab[0][0], slab[0][1], slab[0][2], slab[0][3])
                    if config["pyramid"]["mask"]:
                        to_slab_path_mask = to_pyramid.get_slab_path_from_infos(SlabType["MASK"], slab[0][1], slab[0][2], slab[0][3])

                    if len(process) == 1 :
                        next(round_robin).write(f"link {to_slab_path} {from_slab_path}\n")
                        if config["pyramid"]["mask"]:
                            if mask[0] != "" :
                                next(round_robin).write(f"link {to_slab_path_mask} {mask[0]}\n")
                    else :
                        command = ""
                        for j in range (len(process)) :
                            command += f"c2w {process[j]} DATA\n"
                            if config["process"]["mask"]:
                                if mask[j] != "" :
                                    command += f"c2w {mask[j]} MASK\n"
                        command += "oNt\n"
                        command += f"w2c {to_slab_path} DATA\n"
                        if config["pyramid"]["mask"]:
                            command += f"w2c {to_slab_path_mask} MASK\n"
                        next(round_robin).write(command)

    # Copie des listes de recopies à l'emplacement partagé (peut être du stockage objet)
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = file_objects[i]
            tmp.close()
            Storage.copy(f"file://{tmp.name}", os.path.join(config["process"]["directory"], f"todo.{i+1}.list"))
            Storage.remove(f"file://{tmp.name}")

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location and clean: {e}")
