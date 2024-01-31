"""Provide classes to load sources of data.

The module contains the following classes:

- `Source` - Source objects
- `SourcePyramids` - Load pyramids
"""

from typing import Dict, List, Tuple, Union

from rok4.enums import PyramidType
from rok4.pyramid import Pyramid


class Source:
    """Sources to load to create a new pyramid

    Attributes:
        __bottom (str): Level of the new pyramid's TMS for which the source is used
        __top (str): Level of the new pyramid's TMS until which the source is used
    """

    def __init__(self, bottom: str, top: str) -> None:
        self.__bottom = bottom
        self.__top = top

    @property
    def bottom(self) -> str:
        return self.__bottom

    @property
    def top(self) -> str:
        return self.__top


class SourcePyramids(Source):
    """Pyramid sources to load to create a new pyramid

    Attributes:
        __tms (TileMatrxSet): Tile Matrix Set of the sources
        __format (str): Format of the sources
        __pyramids (List[Pyramid]): List of the loaded pyramid sources
        __type (PyramidType) : Type of the sources
        __channels (int) : If raster pyramid, number of channels of the sources
    """

    def __init__(self, bottom: str, top: str, descriptors: List[str]) -> None:
        Source.__init__(self, bottom, top)

        self.__tms = None
        self.__format = None
        self.__pyramids = []
        self.__type = None

        width_slabs = {}
        height_slabs = {}

        for d in descriptors:
            # Chargement de la pyramide source
            try:
                pyramid = Pyramid.from_descriptor(d)
                self.__pyramids.append(pyramid)

                if pyramid.storage_s3_cluster is not None:
                    # On ne travaille que sur un unique cluster S3, il ne faut pas préciser lequel dans les chemins
                    raise Exception(
                        f"Do not set S3 cluster host into bucket name ({d}) : only one cluster can be used for sources"
                    )

            except Exception as e:
                raise Exception(f"Cannot load source pyramid descriptor : {d} : {e}")

            # Vérification de l'unicité des caractéristiques des pyramides
            if self.__format is None:
                self.__tms = pyramid.tms
                self.__format = pyramid.format
            else:
                if self.__tms.name != pyramid.tms.name:
                    raise Exception(
                        f"Sources pyramids cannot have two different TMS : {self.__tms.name} and {pyramid.tms.name}"
                    )

                if self.__format != pyramid.format:
                    raise Exception(
                        f"Sources pyramids cannot have two different format : {self.__format} and {pyramid.format}"
                    )

            # Vérification de l'unicité du type des pyramides sources
            if self.__type is None:
                self.__type = pyramid.type
                if pyramid.type == PyramidType.RASTER:
                    self.__channels = pyramid.channels
            else:
                if self.__type != pyramid.type:
                    raise Exception(
                        f"Sources pyramids cannot be of two types different : {self.__type} and {self.__type}"
                    )
                if pyramid.type == PyramidType.RASTER:
                    if self.__channels != pyramid.channels:
                        raise Exception(
                            f"Sources pyramids cannot have two different numbers of channels : {self.__channels} and {pyramid.channels}"
                        )

            # Vérification de la présence des niveaux
            try:
                levels = pyramid.get_levels(bottom, top)
            except Exception as e:
                raise Exception(f"All levels between {bottom} -> {top} are not in {pyramid.name}")

            # Vérification de l'unicité de la taille des dalles par niveau
            for level in levels:
                if level.id in width_slabs:
                    if (
                        width_slabs[level.id] != level.slab_width
                        or height_slabs[level.id] != level.slab_height
                    ):
                        raise Exception(
                            f"The number of tiles by slab is different between {pyramid.name} and {self.__pyramids[0].name} at level {level.id}"
                        )
                else:
                    width_slabs[level.id] = level.slab_width
                    height_slabs[level.id] = level.slab_height

    @property
    def tms(self) -> str:
        return self.__tms

    @property
    def format(self) -> str:
        return self.__format

    @property
    def pyramids(self) -> List[Pyramid]:
        return self.__pyramids

    @property
    def type(self) -> PyramidType:
        return self.__type

    @property
    def channels(self) -> int:
        """Get the number of channels for RASTER sources

        Returns:
            int: Number of channels, None if VECTOR sources
        """
        return self.__channels

    def info_level(self, id_level: str) -> Tuple[int, int, Dict[str, int]]:
        """Calculate informations from a level from the level's informations of each pyramid of the datasource

        Args:
            id_level (str) : name of the level

        Returns:
            Tuple[int, int, Dict[str, int]] : slab's width of the level, slab's height of the level and terrain extent in TMS coordinates system
        """
        slab_width = None
        slab_height = None
        tile_limits = None

        for pyramid in self.__pyramids:
            level = pyramid.get_level(id_level)
            tile_limits_level = level.tile_limits
            if slab_width != None:
                if tile_limits_level["min_row"] < tile_limits["min_row"]:
                    tile_limits["min_row"] = tile_limits_level["min_row"]
                if tile_limits_level["min_col"] < tile_limits["min_col"]:
                    tile_limits["min_col"] = tile_limits_level["min_col"]
                if tile_limits_level["max_row"] > tile_limits["max_row"]:
                    tile_limits["max_row"] = tile_limits_level["max_row"]
                if tile_limits_level["max_col"] > tile_limits["max_col"]:
                    tile_limits["max_col"] = tile_limits_level["max_col"]
            else:
                slab_width = level.slab_width
                slab_height = level.slab_height
                tile_limits = tile_limits_level

        return (slab_width, slab_height, tile_limits)
