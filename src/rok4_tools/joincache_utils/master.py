import itertools
import os
import tempfile
from typing import Dict, List, Tuple, Union

from rok4 import storage
from rok4.enums import PyramidType, SlabType
from rok4.pyramid import Pyramid

from rok4_tools.global_utils.source import SourcePyramids

"""Todo list instructions

* c2w <source slab> - Convert a source pyramid slab (MASK ro DATA) to work format
* oNt - Overlay  previous converted data slabs (considering possible masks)
* w2c <destination slab> - Convert the output of last overlayNtiff to slab format, into the output pyramid
* link <destination slab> <source slab> <source index> - Make a symbolic slab to source slab. Source index will be used to generate the pyramid's list

"""


def work(config: Dict) -> None:
    """Master steps : prepare and split copies and merge to do

    Load and check input pyramids from the descriptors and write the todo lists, splitting the copies or merge to do

    Args:
        config (Dict): JOINCACHE configuration

    Raises:
        Exception: Cannot load the input or the output pyramid
        Exception: S3 cluster host have not to be provided into bucket names (output or inputs)
        Exception: Sources pyramid have different features
        Exception: Cannot open stream to write todo lists
        Exception: Cannot copy todo lists
    """

    datasources = []
    tms_reference = None
    format_reference = None
    channels_reference = None
    for datasource in config["datasources"]:
        sources = SourcePyramids(
            datasource["bottom"],
            datasource["top"],
            datasource["source"]["descriptors"],
        )
        # Vérification de l'unicité du TMS
        if not tms_reference:
            tms_reference = sources.tms
        elif tms_reference.name != sources.tms.name:
            raise Exception(
                f"Sources pyramids cannot have two different TMS : {tms_reference} and {sources.tms}"
            )

        # Vérification de l'unicité du format
        if not format_reference:
            format_reference = sources.format
        elif format_reference != sources.format:
            raise Exception(
                f"Sources pyramids cannot have two different format : {format_reference} and {sources.format}"
            )

        # Vérification de l'unicité du nombre de canaux
        if not channels_reference:
            channels_reference = sources.channels
        elif channels_reference != sources.channels:
            raise Exception(
                f"Sources pyramids cannot have two different numbers of channels : {channels_reference} and {sources.channels}"
            )

        # Vérification du type des pyramides
        if sources.type != PyramidType.RASTER:
            raise Exception(f"Some sources pyramids are not a raster")

        datasources += [sources]

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

    if to_pyramid.storage_s3_cluster is not None:
        # On ne travaille que sur un unique cluster S3, il ne faut pas préciser lequel dans les chemins
        raise Exception(
            f"Do not set S3 cluster host into output bucket name ({config['pyramid']['root']}) : only one cluster can be used with JOINCACHE"
        )

    # Ouverture des flux vers les listes de travail à faire
    temp_agent_todos = []
    temp_finisher_todo = None
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False)
            temp_agent_todos.append(tmp)

        temp_finisher_todo = tempfile.NamedTemporaryFile(mode="w", delete=False)

    except Exception as e:
        raise Exception(f"Cannot open stream to write todo lists: {e}")

    round_robin = itertools.cycle(temp_agent_todos)

    slab_finish = []
    level_finish = []
    used_pyramids_roots = {}
    used_pyramids_count = 0

    for sources in datasources:
        from_pyramids = sources.pyramids
        levels = from_pyramids[0].get_levels(sources.bottom, sources.top)
        for level in levels:
            # Vérification que plusieurs datasources ne définissent pas un même niveau
            if level.id not in level_finish:
                try:
                    to_pyramid.delete_level(level.id)
                except:
                    pass
                info = sources.info_level(level.id)
                to_pyramid.add_level(level.id, info[0], info[1], info[2])
                level_finish += [level.id]
            else:
                raise Exception(f"Different datasources cannot define the same level : {level.id}")

            for i in range(len(from_pyramids)):
                # Récupération des dalles de la pyramide
                slabs = from_pyramids[i].list_generator(level.id)
                slabs_mask = from_pyramids[i].list_generator(level.id)
                # Vérification si la dalle à déjà été traitée
                for slab in slabs:
                    if slab[0] in slab_finish:
                        continue
                    if slab[0][0].name == "MASK":
                        continue
                    from_slab_path = storage.get_path_from_infos(
                        from_pyramids[i].storage_type, slab[1]["root"], slab[1]["slab"]
                    )
                    process = [from_slab_path]
                    slab_finish += [slab[0]]

                    # Recherche du masque correspondant à la dalle
                    if config["process"]["mask"]:
                        slab_mask = (
                            (SlabType["MASK"], slab[0][1], slab[0][2], slab[0][3]),
                            slab[1],
                        )
                        slab_mask[1]["slab"] = from_pyramids[i].get_slab_path_from_infos(
                            SlabType["MASK"], slab[0][1], slab[0][2], slab[0][3], False
                        )
                        if slab_mask in slabs_mask:
                            mask = [
                                storage.get_path_from_infos(
                                    from_pyramids[i].storage_type,
                                    slab_mask[1]["root"],
                                    slab_mask[1]["slab"],
                                )
                            ]
                        else:
                            mask = [""]

                    # Recherche de la dalle dans d'autres pyramides sources
                    if not config["process"]["only_links"]:
                        for j in range(i + 1, len(from_pyramids)):
                            slabs_other = from_pyramids[j].list_generator(level.id)
                            slabs_other_mask = from_pyramids[j].list_generator(level.id)
                            for slab_other in slabs_other:
                                if slab_other[0] == slab[0]:
                                    from_slab_path_other = storage.get_path_from_infos(
                                        from_pyramids[j].storage_type,
                                        slab_other[1]["root"],
                                        slab_other[1]["slab"],
                                    )
                                    process += [from_slab_path_other]
                                    if config["process"]["mask"]:
                                        slab_mask_other = (
                                            (
                                                SlabType["MASK"],
                                                slab_other[0][1],
                                                slab_other[0][2],
                                                slab_other[0][3],
                                            ),
                                            slab_other[1],
                                        )
                                        slab_mask_other[1]["slab"] = from_pyramids[
                                            j
                                        ].get_slab_path_from_infos(
                                            SlabType["MASK"],
                                            slab_other[0][1],
                                            slab_other[0][2],
                                            slab_other[0][3],
                                            False,
                                        )
                                        if slab_mask_other in slabs_other_mask:
                                            mask += [
                                                storage.get_path_from_infos(
                                                    from_pyramids[i].storage_type,
                                                    slab_mask_other[1]["root"],
                                                    slab_mask_other[1]["slab"],
                                                )
                                            ]
                                        else:
                                            mask += [""]
                                    continue

                    to_slab_path = to_pyramid.get_slab_path_from_infos(
                        slab[0][0], slab[0][1], slab[0][2], slab[0][3]
                    )
                    if config["pyramid"]["mask"]:
                        to_slab_path_mask = to_pyramid.get_slab_path_from_infos(
                            SlabType["MASK"], slab[0][1], slab[0][2], slab[0][3]
                        )

                    # Ecriture des commandes dans les todo-lists
                    if len(process) == 1:
                        if slab[1]["root"] in used_pyramids_roots:
                            root_index = used_pyramids_roots[slab[1]["root"]]
                        else:
                            used_pyramids_count += 1
                            root_index = used_pyramids_count
                            used_pyramids_roots[slab[1]["root"]] = used_pyramids_count

                        next(round_robin).write(
                            f"link {to_slab_path} {from_slab_path} {root_index}\n"
                        )
                        if config["pyramid"]["mask"]:
                            if mask[0] != "":
                                next(round_robin).write(
                                    f"link {to_slab_path_mask} {mask[0]} {root_index}\n"
                                )
                    else:
                        command = ""
                        for j in range(len(process)):
                            command += f"c2w {process[j]}\n"
                            if config["process"]["mask"]:
                                if mask[j] != "":
                                    command += f"c2w {mask[j]}\n"
                        command += "oNt\n"
                        command += f"w2c {to_slab_path}\n"
                        if config["pyramid"]["mask"]:
                            command += f"w2c {to_slab_path_mask}\n"
                        next(round_robin).write(command)

    for root in used_pyramids_roots:
        temp_finisher_todo.write(f"{used_pyramids_roots[root]}={root}\n")

    # Copie des listes de recopies à l'emplacement partagé (peut être du stockage objet)
    try:
        for i in range(0, config["process"]["parallelization"]):
            tmp = temp_agent_todos[i]
            tmp.close()
            storage.copy(
                f"file://{tmp.name}",
                os.path.join(config["process"]["directory"], f"todo.{i+1}.list"),
            )
            storage.remove(f"file://{tmp.name}")

        temp_finisher_todo.close()
        storage.copy(
            f"file://{temp_finisher_todo.name}",
            os.path.join(config["process"]["directory"], f"todo.finisher.list"),
        )
        storage.remove(f"file://{temp_finisher_todo.name}")

    except Exception as e:
        raise Exception(f"Cannot copy todo lists to final location and clean: {e}")
