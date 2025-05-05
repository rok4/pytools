import itertools
import logging
import os
import pprint
import tempfile
from typing import Dict

from rok4 import storage
from rok4.pyramid import Pyramid
from rok4.tile_matrix_set import TileMatrixSet

from rok4_tools.global_utils.source import SourceWMS

"""Todo list instructions

* levels <bottom level ID> <cut level ID> <top level ID> - Define the levels for source to compute
* getmap_infos <widthwise getmap count> <heightwise getmap count> <getmap static part> <extension> <bands count> <band format> - Define global informations for getmap requests
* getmap <slab level> <slab column> <slab row> <bbox>[ <bbox>] - Download a slab through WMS GetMap(s), never in the finisher todo list
* m4t <slab level> <slab column> <slab row> <source slab(s) command> <source slab(s) level> <source slab col> <source slab row>[ <source slab col> <source slab row>] - Compute a slab with 4 (or less) below slabs

"""


def work(config: Dict, dry: bool = False) -> None:
    """Master steps : prepare and split getmap requests and pyramid copies to do

    Load the WMS sources and the output pyramid and write the todo lists, splitting the work to do and write the output pyramid descriptor

    Args:
        config (Dict): ASPYRO configuration
        dry (bool, optional): Only test configuration content and print the harvested slabs count. Defaults to False.

    Raises:
        Exception: Cannot load the output pyramid
        Exception: Cannot load WMS sources
        Exception: Cannot write temporary todo lists
        MissingEnvironmentError: Missing object storage informations
    """

    # Chargement du TMS cible
    try:
        tms = TileMatrixSet(config["pyramid"]["tms"])
    except Exception as e:
        raise Exception(f"Cannot load the output pyramid tile matrix set: {e}")

    datasources = []
    level_ids = []
    samplesperpixel = None
    sampleformat = None
    for datasource in config["datasources"]:
        # On contrôle la cohérence des niveaux limites avec le TMS de la pyramide à écrire
        # et on charge les sources en tant qu'objet de la classe SourceWMS
        levels = tms.get_levels(datasource["bottom"], datasource["top"])

        for l in levels:
            if l.id in level_ids:
                raise Exception(f"The level '{l.id}' is defined twice in datasources")
            level_ids.append(l.id)

        source = SourceWMS(datasource["bottom"], datasource["top"], datasource["source"])

        infos = source.test(tms)

        if sampleformat is None:
            sampleformat = infos["format"].name
            samplesperpixel = infos["bands"]
        elif sampleformat != infos["format"].name or samplesperpixel != infos["bands"]:
            raise Exception(
                "All WMS source have to give image with same bands count and sample format"
            )

        datasources.append(source)

    # Chargement de la pyramide à écrire

    # On enrichit la configuration avec le format d'image issu du moissonnage
    config["pyramid"]["pixel"] = {"samplesperpixel": samplesperpixel, "sampleformat": sampleformat}

    try:
        output_pyramid = Pyramid.from_parameters(config["pyramid"])
        if output_pyramid.exists:
            # La pyramide de sortie existe déjà, on va donc la charger depuis son descripteur
            descriptor_path = output_pyramid.descriptor
            output_pyramid = Pyramid.from_descriptor(descriptor_path)
            pprint.pp(output_pyramid.serializable)
            return
    except Exception as e:
        raise Exception(f"Cannot create the output pyramid descriptor from the parameters: {e}")

    if dry:
        logging.info(f"Raster data with {samplesperpixel} {sampleformat} band(s)")
    else:
        # Ouverture des flux vers les listes de recopies à faire
        split_file_objects = []
        finisher_file_object = None
        try:
            for i in range(0, config["process"]["parallelization"]):
                tmp = tempfile.NamedTemporaryFile(mode="w", delete=False)
                split_file_objects.append(tmp)

            finisher_file_object = tempfile.NamedTemporaryFile(mode="w", delete=False)

        except Exception as e:
            raise Exception(f"Cannot open stream to write todo lists: {e}")

        round_robin = itertools.cycle(split_file_objects)

    for source in datasources:
        levels = output_pyramid.tms.get_levels(source.bottom, source.top)

        # On identifie les dalles à générer à partir de cette source
        (width_getmap_count, height_getmap_count, url, extension) = source.compute_slabs_indices(
            output_pyramid.tms,
            (config["pyramid"]["slab_size"][0], config["pyramid"]["slab_size"][1]),
        )

        # On ajoute chaque niveau de cette source dans la pyramide de sortie, avec les tuiles limites
        for level in levels:
            (col_min, row_min, col_max, row_max) = source.get_tile_limits(level.id)

            output_pyramid.add_level(
                level.id,
                config["pyramid"]["slab_size"][0],
                config["pyramid"]["slab_size"][1],
                {"min_col": col_min, "max_col": col_max, "min_row": row_min, "max_row": row_max},
            )

        # On détermine le niveau jusqu'auquel les todo listes en parallèle vont travailler
        # et à partir duquel la todo liste du finisher va travailler
        cut_level = source.get_cut_level(output_pyramid.tms, config["process"]["parallelization"])

        if dry:
            logging.info(f"WMS source from {source.bottom} to {source.top}")
            logging.info(f"    cut level {cut_level}")
            logging.info(f"    {source.bottom_slab_count} slab(s) to harvest")
            continue

        # On précise les niveaux (bas, coupure et haut) dans tous les scripts
        # Ainsi que les informations globales de moissonnage
        for split_file_object in split_file_objects:
            split_file_object.write(f"levels {source.bottom} {cut_level} {source.top}\n")
            split_file_object.write(
                f"getmap_infos {width_getmap_count} {height_getmap_count} {url} {extension} {samplesperpixel} {sampleformat}\n"
            )

        finisher_file_object.write(f"levels {source.bottom} {cut_level} {source.top}\n")
        finisher_file_object.write(
            f"getmap_infos {width_getmap_count} {height_getmap_count} {url} {extension} {samplesperpixel} {sampleformat}\n"
        )

        # On demande le calcul parallélisable des dalles du niveau de coupure et en dessous
        for slab in source.slab_generator(cut_level):
            source.compute_slab(slab, next(round_robin), None)

        # On demande le calcul non parallélisable des dalles du niveau du haut jusqu'au niveau de coupure
        for slab in source.slab_generator(source.top):
            source.compute_slab(slab, finisher_file_object, cut_level)

    if not dry:
        # Copie des listes de recopies à l'emplacement partagé (peut être du stockage objet)
        try:
            for i in range(0, config["process"]["parallelization"]):
                tmp = split_file_objects[i]
                tmp.close()
                storage.copy(
                    f"file://{tmp.name}",
                    os.path.join(config["process"]["directory"], f"todo.{i+1}.list"),
                )
                storage.remove(f"file://{tmp.name}")

            finisher_file_object.close()
            storage.copy(
                f"file://{finisher_file_object.name}",
                os.path.join(config["process"]["directory"], "todo.finisher.list"),
            )
            storage.remove(f"file://{finisher_file_object.name}")

        except Exception as e:
            raise Exception(f"Cannot copy todo lists to final location and clean: {e}")

        try:
            output_pyramid.write_descriptor()
        except Exception as e:
            raise Exception(f"Cannot write output pyramid's descriptor to final location: {e}")
