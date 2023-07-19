"""Provide classes to load sources of data.

The module contains the following classes:

- `Source` - Source objects
- `SourcePyramids` - Load pyramids
- `SourceRasterPyramids` - Load raster pyramids
"""

from typing import Dict, List, Tuple, Union

from rok4.pyramid import Pyramid
from rok4.enums import PyramidType


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
    """

    def __init__(self, bottom: str, top: str, descriptors: List[str]) -> None:
        Source.__init__(self, bottom, top)

        self.__tms = None
        self.__format = None
        self.__pyramids = []

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

            # Vérification de l'unicité du des caractéristiques des pyramides
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

            # Vérification de la présence des niveaux
            try:
                level = pyramid.get_levels(bottom, top)
            except Exception as e:
                raise Exception(f"All levels between {bottom} -> {top} are not in {pyramid.name}")

    @property
    def tms(self) -> str:
        return self.__tms

    @property
    def format(self) -> str:
        return self.__format

    @property
    def pyramids(self) -> List[Pyramid]:
        return self.__pyramids

    def info_level(self, id_level: str) -> Tuple[int, int, Dict[str, int]]:
        slab_width = None
        slab_height = None
        tile_limits = None

        for pyramid in self.__pyramids:
            level = pyramid.get_level(id_level)
            tile_limits_level = level.tile_limits
            if slab_width != None:
                if level.slab_width != slab_width or level.slab_height != slab_height:
                    raise Exception(
                        f"The number of tiles by slab is different between {pyramid.name} and {pyramids[0].name} at level {id_level}"
                    )
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


class SourceRasterPyramids(SourcePyramids):
    """Raster pyramid sources to load to create a new pyramid

    Attributes:
        __channels (int): Number of channels of the sources
    """

    def __init__(self, bottom: str, top: str, descriptors: List[str]) -> None:
        SourcePyramids.__init__(self, bottom, top, descriptors)
        pyramids = self.pyramids
        for i in range(len(pyramids)):
            # Vérification que les pyramides soient bien des rasters
            if pyramids[i].type != PyramidType.RASTER:
                raise Exception(f"Source pyramid {pyramids[i].name} is not a raster")

            # Vérification de l'unicité du nombre de canaux
            if i == 0:
                self.__channels = pyramids[i].channels
            else:
                if self.__channels != pyramids[i].channels:
                    raise Exception(
                        f"Sources pyramids cannot have two different numbers of channels : {self.__channels} and {pyramids.channels}"
                    )

    @property
    def channels(self) -> int:
        return self.__channels
