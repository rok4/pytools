"""Provide classes to load sources of data.

The module contains the following classes:

- `Source` - Source objects
- `SourcePyramids` - Load pyramids source
- `SourceWMS` - Load WMS source
"""

from typing import Dict, Iterator, List, TextIO, Tuple

from rok4.enums import PyramidType
from rok4.pyramid import Pyramid
from rok4.storage import copy, get_data_str
from rok4.tile_matrix_set import TileMatrixSet
from rok4.utils import (
    bbox_to_geometry,
    get_geometry_parts,
    get_raster_infos,
    intersects,
    path_to_geometry,
    reproject_geometry,
    wkt_to_geometry,
)

from rok4_tools.global_utils.enums import SourceType


class Source:
    """Sources to load to create a new pyramid

    Attributes:
        bottom (str): Level of the new pyramid's TMS for which the source is used
        top (str): Level of the new pyramid's TMS until which the source is used
    """

    def __init__(self, bottom: str, top: str) -> None:
        self.bottom = bottom
        self.top = top


class SourcePyramids(Source):
    """Pyramid sources to load to create a new pyramid

    Attributes:
        __pyramids (List[Pyramid]): List of the loaded pyramid sources
    """

    def __init__(self, bottom: str, top: str, params: Dict) -> None:
        Source.__init__(self, bottom, top)

        self.__pyramids = []

        pyramids_tms = None
        pyramids_format = None
        pyramids_type = None
        pyramids_channels = None

        width_slabs = {}
        height_slabs = {}

        if "descriptors" not in params:
            raise Exception("Missing descriptors list in source parameters")

        for d in params["descriptors"]:
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
            if pyramids_format is None:
                # On est sur la première pyramide source, qui servira de référence
                pyramids_tms = pyramid.tms
                pyramids_format = pyramid.format
                pyramids_type = pyramid.type
                pyramids_channels = pyramid.channels
            else:
                if pyramids_tms.name != pyramid.tms.name:
                    raise Exception(
                        f"Source pyramids cannot have two different TMS : {pyramid.name} and {self.__pyramids[0].name}"
                    )

                if pyramids_format != pyramid.format:
                    raise Exception(
                        f"Source pyramids cannot have two different format : {pyramid.name} and {self.__pyramids[0].name}"
                    )

                if pyramids_type != pyramid.type:
                    raise Exception(
                        f"Source pyramids cannot be of two types different : {pyramid.name} and {self.__pyramids[0].name}"
                    )

                if pyramids_channels != pyramid.channels:
                    raise Exception(
                        f"Source pyramids cannot have two different numbers of channels : {pyramid.name} and {self.__pyramids[0].name}"
                    )

            # Vérification de la présence des niveaux
            try:
                levels = pyramid.get_levels(bottom, top)
            except Exception:
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

        if len(self.__pyramids) == 0:
            raise Exception("A PYRAMIDS source have to contains minimum one pyramid")

    @property
    def type(self) -> SourceType:
        return SourceType.PYRAMIDS

    @property
    def tms(self) -> str:
        return self.__pyramids[0].tms

    @property
    def format(self) -> str:
        return self.__pyramids[0].format

    @property
    def pyramids(self) -> List[Pyramid]:
        return self.__pyramids

    @property
    def pyramids_type(self) -> PyramidType:
        return self.__pyramids[0].type

    @property
    def channels(self) -> int:
        """Get the number of channels for RASTER sources

        Returns:
            int: Number of channels, None if VECTOR sources
        """
        return self.__pyramids[0].channels

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
            if slab_width is not None:
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


class SourceWMS(Source):
    """WMS service source to request (version 1.3.0)

    Attributes:
        __endpoint (str): WMS service URL
        __format (str): Format to use to request raster data
        __extension (str): Extension for downloaded images
        __extra_params (Dict[str, str]): Additionnal query parameters, to add to each WMS request
        __extra_params_serialized (str]): Additionnal query parameters, as string, to add to each WMS request
        __layers (List[str]) : Layers to request
        __styles (str) : Styles to apply to requested layers
        __geometry (osgeo.ogr.Geometry): Area to harvest as geometry
        __srs (str): Coordinates system of the geometry
        __slabs (Dict[str, Dict[str, Dict]]): Slab indices from bottom to top
        __max_size (List[int]): Maximum pixel width and height of image to download.
        __tile_limits (Dict[str, Tuple[int,int,int,int]]]): Tile limits (col_min, row_min, col_max, row_max), from bottom to top
    """

    def __init__(self, bottom: str, top: str, params: Dict) -> None:
        Source.__init__(self, bottom, top)

        self.__slabs = {}
        self.__tile_limits = {}
        self.__extension = "tif"

        try:
            self.__endpoint = params["endpoint"]

            self.__format = params.get("format", "image/jpeg")
            if self.__format == "image/jpeg":
                self.__extension = "jpg"
            elif self.__format == "image/png":
                self.__extension = "png"

            self.__max_size = params.get("max_size", None)

            self.__layers = params["layers"]
            styles = params.get("styles", [])

            if len(styles) != 0 and len(styles) != len(self.__layers):
                raise Exception(
                    "Layers' list and styles' list (if not empty) lengths have to be the same"
                )

            self.__styles = ",".join(str(v) for v in styles)

            self.__extra_params = params.get("extra_params", {})
            self.__extra_params_serialized = ""
            for key in self.__extra_params:
                self.__extra_params_serialized += f"&{key}={self.__extra_params[key]}"

            if "bbox" in params["area"]:
                self.__srs = params["area"]["srs"]
                self.__geometry = bbox_to_geometry(params["area"]["bbox"], 10)
            elif "geometry" in params["area"]:
                self.__srs = params["area"]["srs"]
                self.__geometry = wkt_to_geometry(params["area"]["geometry"])
            elif "path" in params["area"]:
                self.__srs = params["area"]["srs"]
                self.__geometry = path_to_geometry(params["area"]["path"])
            else:
                raise Exception("No handled area provided for the WMS source")

        except KeyError as e:
            raise Exception(f"Missing '{e}' key in WMS source parameters")

        except RuntimeError as e:
            raise Exception(f"OGR cannot load the geometry used to define area : {e}")

    def test(self, tms: TileMatrixSet) -> Dict:
        """Download a tile of the bottom level, to check if layer(s) are available and format is valid

        Args:
            tms (TileMatrixSet): Target tile matrix set

        Raises:
            RuntimeError: raised by OGR/GDAL if anything goes wrong
            Exception: Issue downloading the tile

        Returns:
            Dict: Informations about downloaded image : bbox (Tuple[float]), bands (int), format (ColorFormat) and dimensions (Tuple[int])
        """
        bottom_level = tms.get_level(self.bottom)
        url = f"{self.get_static_getmap_request(tms.srs, (bottom_level.tile_width, bottom_level.tile_height))}&BBOX={','.join(map(str, bottom_level.tile_to_bbox(0,0)))}"

        try:
            copy(url, f"file:///tmp/test_getmap.{self.__extension}")
            infos = get_raster_infos(f"file:///tmp/test_getmap.{self.__extension}")
            return infos
        except Exception as e:
            err = get_data_str(f"file:///tmp/test_getmap.{self.__extension}")
            raise Exception(f"Cannot test a getmap to WMS source: {e}\n{err}")

    def compute_slabs_indices(
        self, tms: TileMatrixSet, slab_size: Tuple[int, int]
    ) -> Tuple[int, int, str, str]:
        """Determine slabs indices from bottom to top levels of source

        Args:
            tms (TileMatrixSet): Tile matrix set used for slabs
            slab_size (Tuple[int, int]): Tiles per width and tiles per height

        Returns:
            Tuple[int, int, str, str]: Harevst informations: widthwise and heightwise getmaps count for a slab, the static part for getmap requests and the downloaded image extension
        """

        # On va travailler à partir de la géométrie reprojetée dans le système du TMS cible
        geometry = reproject_geometry(self.__geometry, self.__srs, tms.srs)

        parts = get_geometry_parts(geometry)
        levels = tms.get_levels(self.bottom, self.top)

        # Les dalles du niveau du bas sont définies par la géométrie fournie
        bottom_level = levels.pop(0)
        self.__slabs[bottom_level.id] = {}

        # On contrôle la cohérence de la taille maximale à moissonner et la taille des dalles
        slab_pixel_width = bottom_level.tile_width * slab_size[0]
        slab_pixel_height = bottom_level.tile_height * slab_size[1]

        width_getmap_count = 1
        getmap_ground_width = slab_pixel_width * bottom_level.resolution
        height_getmap_count = 1
        getmap_ground_height = slab_pixel_height * bottom_level.resolution
        getmap_dimensions = (slab_pixel_width, slab_pixel_height)

        if self.__max_size is not None:
            if (
                slab_pixel_width % self.__max_size[0] != 0
                or slab_pixel_height % self.__max_size[1] != 0
            ):
                raise Exception(
                    "Maximum size for requested image have to be a divisor of final slab size"
                )

            width_getmap_count = slab_pixel_width // self.__max_size[0]
            getmap_ground_width = getmap_ground_width / width_getmap_count
            height_getmap_count = slab_pixel_height // self.__max_size[1]
            getmap_ground_height = getmap_ground_height / height_getmap_count

            getmap_dimensions = (self.__max_size[0], self.__max_size[1])

        url = self.get_static_getmap_request(tms.srs, getmap_dimensions)

        for part in parts:
            (col_min, row_min, col_max, row_max) = bottom_level.bbox_to_tiles(part[1])
            self.__tile_limits[bottom_level.id] = (col_min, row_min, col_max, row_max)

            # On a des indices de tuiles, on va passer sur des indices de dalle
            col_min = col_min // slab_size[0]
            col_max = col_max // slab_size[0]
            row_min = row_min // slab_size[1]
            row_max = row_max // slab_size[1]

            for col in range(col_min, col_max + 1):
                for row in range(row_min, row_max + 1):
                    bbox = bottom_level.slab_to_bbox(col, row, slab_size)
                    slab_geom = bbox_to_geometry(bbox)
                    if intersects(slab_geom, part[0]):
                        bboxes = []

                        for h in range(height_getmap_count):
                            for w in range(width_getmap_count):
                                bboxes.append(
                                    (
                                        bbox[0] + w * getmap_ground_width,
                                        bbox[3] - (h + 1) * getmap_ground_height,
                                        bbox[0] + (w + 1) * getmap_ground_width,
                                        bbox[3] - h * getmap_ground_height,
                                    )
                                )

                        self.__slabs[bottom_level.id][f"{col}_{row}"] = {
                            "indices": (col, row),
                            "level": bottom_level.id,
                            "bboxes": bboxes,
                        }

        # Les niveaux supérieurs sont définis par le niveau du dessous
        below_level = bottom_level
        if tms.qtree:
            for level in levels:
                self.__slabs[level.id] = {}

                self.__tile_limits[level.id] = (
                    self.__tile_limits[below_level.id][0] // 2,
                    self.__tile_limits[below_level.id][1] // 2,
                    self.__tile_limits[below_level.id][2] // 2,
                    self.__tile_limits[below_level.id][3] // 2,
                )

                for slab in self.__slabs[below_level.id]:
                    (below_col, below_row) = self.__slabs[below_level.id][slab]["indices"]

                    col = below_col // 2
                    row = below_row // 2

                    # Une dalle de ce niveau est généré à partir des 4 dalles potentielles du dessous
                    # On calcule la place de la dalle du dessous
                    #  -------+-------
                    # |   0   |   1   |
                    #  -------+-------
                    # |   2   |   3   |
                    #  -------+-------

                    ind = below_col % 2 + 2 * (below_row % 2)

                    if f"{col}_{row}" in self.__slabs[level.id]:
                        # La dalle de ce niveau existe déjà, on va compléter les dalles du dessous à partir desquelles elle est calculée
                        self.__slabs[level.id][f"{col}_{row}"]["slabs"][
                            ind
                        ] = f"{below_col}_{below_row}"
                    else:
                        # C'est une nouvelle dalle pour ce niveau
                        source_slabs = [None] * 4
                        source_slabs[ind] = f"{below_col}_{below_row}"
                        self.__slabs[level.id][f"{col}_{row}"] = {
                            "indices": (col, row),
                            "level": level.id,
                            "below_level": below_level.id,
                            "slabs": source_slabs,
                        }

                below_level = level

            return (width_getmap_count, height_getmap_count, url, self.__extension)
        else:
            raise Exception("Cannot compute slabs for non quad tree tile matrix set")

    @property
    def type(self) -> SourceType:
        return SourceType.WMS

    def get_cut_level(self, tms: TileMatrixSet, parallelization: int) -> str:
        if tms.qtree:
            levels = tms.get_levels(self.bottom, self.top)

            for level in reversed(levels):
                if len(self.__slabs[level.id]) >= 5 * parallelization:
                    return level.id

            # Même le niveau du bas ne contient pas 5 fois plus de dalles qu'il n'y aura de script en parallèle, on le choisit tout de même
            return self.bottom
        else:
            raise Exception("Cannot get cut level for non quad tree tile matrix set")

    @property
    def endpoint(self) -> str:
        return self.__endpoint

    def slab_generator(self, level_id: str) -> Iterator[Dict]:
        """Get slabs for provided levels

        Args :
            level_id (str) : id of the level to get slabs

        Yields:
            Iterator[Dict]: Slab indices and compute informations

            URL value example:

                {
                    'indices': (4223, 2962),
                    'level': '16',
                    'bboxes': [
                        (621280.1659019776, 5545047.779919768, 623726.1508071033, 5547493.764824893),
                        (623726.1508071033, 5545047.779919768, 626172.1357122288, 5547493.764824893),
                        (621280.1659019776, 5542601.795014642, 623726.1508071033, 5545047.779919768),
                        (623726.1508071033, 5542601.795014642, 626172.1357122288, 5545047.779919768)
                    ]
                }

            MERGE4TIFF value example:

                {
                    'indices': (1055, 740),
                    'level': '14',
                    'below_level': '15',
                    'slabs': ['2110_1481', '2111_1481', None, None]
                }
        """
        yield from self.__slabs[level_id].values()

    def compute_slab(self, slab: Dict, file: TextIO, stop_level_id: str = None) -> str:
        """Compute a slab from an URL (WMS GetMap) or source slabs (merge4tiff)

        It's a recursive function: if source slabs are present, we call this function for each, until a slab with URL or a cut level slab

        Args:
            slab (Dict): Slab to compute
            file (TextIO): File to write commands
            stop_level_id (str, optional): Level to stop recursive calls. Defaults to None.

        Raises:
            Exception: Invalid slab, neither URL nor SLABS to compute it

        Returns:
            str: command used to compute the slab (m4t or getmap)
        """
        if stop_level_id is not None and slab["level"] == stop_level_id:
            # On nous a fourni un niveau d'arrêt et on a ici une de ses dalles, on arrête le parcours
            # on retourne tout de même la commande qui a généré cette dalle

            if "bboxes" in slab:
                return "getmap"
            elif "slabs" in slab:
                return "m4t"
            else:
                raise Exception(
                    f"Cannot compute slab {slab}: neither with a getmap nor a merge4tiff"
                )

        if "bboxes" in slab:
            # On a une URL, il suffit de moissonner la dalle
            file.write(f"getmap {slab['level']} {slab['indices'][0]} {slab['indices'][1]}")
            for bb in slab["bboxes"]:
                file.write(f" {','.join(str(v) for v in bb)}")
            file.write("\n")
            return "getmap"
        elif "slabs" in slab:
            # On a des dalles sources, on en demande le calcul puis on réalise un merge4tiff pour avoir notre dalle
            m4t_inputs = [slab["below_level"]]

            source_cmd = ""
            for source_slab_key in slab["slabs"]:
                if source_slab_key is not None:
                    source_slab = self.__slabs[slab["below_level"]][source_slab_key]
                    m4t_inputs.append(f"{source_slab['indices'][0]} {source_slab['indices'][1]}")
                    source_cmd = self.compute_slab(source_slab, file, stop_level_id)

            file.write(
                f"m4t {slab['level']} {slab['indices'][0]} {slab['indices'][1]} {source_cmd} {' '.join(m4t_inputs)}\n"
            )
            return "m4t"
        else:
            raise Exception(f"Cannot compute slab {slab}: neither with a getmap nor a merge4tiff")

    def get_tile_limits(self, level: str) -> Tuple[int, int, int, int]:
        return self.__tile_limits.get(level, None)

    def get_slab_count(self, level: str) -> int:
        return self.__tile_limits.get(level, None)

    def get_static_getmap_request(self, crs: str, dimensions: Tuple[int, int]) -> str:
        return f"{self.__endpoint}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={','.join(str(v) for v in self.__layers)}&STYLES={self.__styles}&FORMAT={self.__format}&CRS={crs}&width={dimensions[0]}&height={dimensions[1]}{self.__extra_params_serialized}"

    def get_getcapabilities_request(self) -> str:
        return f"{self.__endpoint}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities{self.__extra_params_serialized}"
