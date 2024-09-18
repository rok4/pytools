"""Provide processor tranforming data. Output data is emitted as the input processor reading progresses

The module contains the following classes:

- `Gettile2tileindexProcessor` - Extract tile index from a WMTS GetTile URL
- `Tileindex2gettileProcessor` - Generate WMTS GetTile query parameters from tile index
- `Tileindex2pointProcessor` - Generate the tile's center coordinates from tile index
- `Geometry2tileindexProcessor` - Generate all tiles' indices intersecting the input geometry
"""

import sys
from typing import Dict, List, Tuple, Union, Iterator
from math import floor
from urllib.parse import urlparse, parse_qs

from osgeo import gdal, ogr, osr
ogr.UseExceptions()
osr.UseExceptions()
gdal.UseExceptions()

from rok4.tile_matrix_set import TileMatrixSet
from rok4.utils import bbox_to_geometry

from rok4_tools.tmsizer_utils.processors.processor import Processor

class Gettile2tileindexProcessor(Processor):
    """Processor extracting tile index from a WMTS GetTile URL

    Accepted input format is "GETTILE_PARAMS" and output format is "TILE_INDEX"

    Attributes:
        __input (Processor): Processor from which data is read
        __levels (List[str], optional): Tile matrix identifier(s) to filter data
        __layers (List[str], optional): Layer(s) to filter data
    """

    input_formats_allowed = ["GETTILE_PARAMS"]

    def __init__(self, input: Processor, **options):
        """Constructor method

        Args:
            input (Processor): Processor from which data is read
            **levels (str, optional): Tile matrix identifier(s) to filter data
            **layers (str, optional): Layer(s) to filter data

        Raises:
            ValueError: Input format is not allowed
            ValueError: Provided level is not in the pivot TMS
        """        

        if input.format not in self.input_formats_allowed:
            raise ValueError(f"Input format {input.format} is not handled for Gettile2tileindexProcessor : allowed formats are {self.input_formats_allowed}")

        super().__init__("TILE_INDEX")

        self.__input = input
        if "levels" in options.keys():
            self.__levels = options["levels"].split(",")
            for l in self.__levels:
                if self.tms.get_level(l) is None:
                    raise ValueError(f"The provided level '{l}' is not in the TMS")
        else:
            self.__levels = None

        self.__input = input
        if "layers" in options.keys():
            self.__layers = options["layers"].split(",")
        else:
            self.__layers = None

    def process(self) -> Iterator[Tuple[str, int, int]]:
        """Read an item from the input processor and extract tile index

        Used query parameters are TILEMATRIXSET, TILEMATRIX, TILECOL and TILEROW. If one is missing, item is passed. 
        TILEMATRISET have to be the pivot TMS's name (or just preffixed by its name). TILEMATRIX have to be present in the pivot TMS. 
        If filtering levels are provided, unmatched TILEMATRIX are passed. If filtering layers are provided, unmatched LAYER are passed.

        Examples:

            Get tile index

                from rok4_tools.tmsizer_utils.processors.map import Gettile2tileindexProcessor

                try:
                    # Creation of Processor source_processor with format GETTILE_PARAMS
                    processor = Gettile2tileindexProcessor(source_processor, level="19" )
                    for item in processor.process():
                        (level, col, row) = item

                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[Tuple[str, int, int]]: Tile index (level, col, row)
        """  

        if self.__input.format == "GETTILE_PARAMS":
            for item in self.__input.process():
                self._processed += 1

                qs = parse_qs(urlparse(item.upper()).query)
                try:

                    # On se limite à un niveau et ce n'est pas celui de la requête
                    if self.__levels is not None and qs["TILEMATRIX"][0] not in self.__levels:
                        continue

                    # On se limite à une couche et ce n'est pas celle de la requête
                    if self.__layers is not None and qs["LAYER"][0] not in self.__layers:
                        continue

                    # La requête n'utilise pas le TMS en entrée
                    if qs["TILEMATRIXSET"][0] != self.tms.name and not qs["TILEMATRIXSET"][0].startswith(f"{self.tms.name}_"):
                        continue

                    # La requête demande un niveau que le TMS ne possède pas
                    if self.tms.get_level(qs["TILEMATRIX"][0]) is None:
                        continue

                    yield (str(qs["TILEMATRIX"][0]),int(qs["TILECOL"][0]),int(qs["TILEROW"][0]))
                except Exception as e:
                    # La requête n'est pas un gettile ou n'est pas valide, il manque un paramètre, ou il a un mauvais format
                    # on la passe simplement
                    pass

    def __str__(self) -> str:
        return f"Gettile2tileindexProcessor : {self._processed} {self.__input.format} items processed, extracting tile's indices"


class Tileindex2gettileProcessor(Processor):
    """Processor generating WMTS GetTile query parameters from tile index

    Accepted input format is "TILE_INDEX" and output format is "GETTILE_PARAMS"

    Attributes:
        __input (Processor): Processor from which data is read
    """

    input_formats_allowed = ["TILE_INDEX"]

    def __init__(self, input: Processor):
        """Constructor method

        Args:
            input (Processor): Processor from which data is read

        Raises:
            ValueError: Input format is not allowed
        """  

        if input.format not in self.input_formats_allowed:
            raise ValueError(f"Input format {input.format} is not handled for Tileindex2gettileProcessor : allowed formats are {self.input_formats_allowed}")

        super().__init__("GETTILE_PARAMS")

        self.__input = input

    def process(self) -> Iterator[str]:
        """Read a tile index from the input processor and generate WMTS GetTile query parameters

        Examples:

            Get GetTile query parameters

                from rok4_tools.tmsizer_utils.processors.map import Tileindex2gettileProcessor

                try:
                    # Creation of Processor source_processor with format TILE_INDEX
                    processor = Tileindex2gettileProcessor(source_processor)
                    for item in processor.process():
                        query_parameters = item

                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[str]: GetTile query parameters TILEMATRIXSET=<tms>&TILEMATRIX=<level>&TILECOL=<col>&TILEROW=<row>
        """  

        if self.__input.format == "TILE_INDEX":
            for item in self.__input.process():
                self._processed += 1

                (level, col, row) = item

                yield f"TILEMATRIXSET={self.tms.name}&TILEMATRIX={level}&TILECOL={col}&TILEROW={row}"

    def __str__(self) -> str:
        return f"Tileindex2gettileProcessor : {self._processed} {self.__input.format} items processed, generating GetTile's query parameters"

class Tileindex2pointProcessor(Processor):
    """Processor generating the tile's center coordinates from tile index

    Accepted input format is "TILE_INDEX" and output format is "POINT"

    Attributes:
        __input (Processor): Processor from which data is read
    """

    input_formats_allowed = ["TILE_INDEX"]

    def __init__(self, input: Processor):
        """Constructor method

        Args:
            input (Processor): Processor from which data is read

        Raises:
            ValueError: Input format is not allowed
        """  

        if input.format not in self.input_formats_allowed:
            raise ValueError(f"Input format {input.format} is not handled for Tileindex2pointProcessor : allowed formats are {self.input_formats_allowed}")

        super().__init__("POINT")

        self.__input = input

    def process(self) -> Iterator[Tuple[float, float]]:
        """Read a tile index from the input processor and generate the tile's center coordinates

        Examples:

            Get tile's center coordinates

                from rok4_tools.tmsizer_utils.processors.map import Tileindex2pointProcessor

                try:
                    # Creation of Processor source_processor with format TILE_INDEX
                    processor = Tileindex2pointProcessor(source_processor)
                    for item in processor.process():
                        (x, y) = item

                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[Tuple[float, float]]: point coordinates (x,y)
        """  

        if self.__input.format == "TILE_INDEX":
            for item in self.__input.process():
                self._processed += 1

                (level, col, row) = item
                try:
                    bb = self.tms.get_level(level).tile_to_bbox(col, row)

                    x_center = bb[0] + (bb[2] - bb[0]) / 2;
                    y_center = bb[1] + (bb[3] - bb[1]) / 2;

                    yield (x_center, y_center)
                except Exception as e:
                    # Le niveau n'est pas valide, on passe simplement
                    pass

    def __str__(self) -> str:
        return f"Tileindex2pointProcessor : {self._processed} {self.__input.format} items processed, extracting tile's center coordinates"


class Geometry2tileindexProcessor(Processor):
    """Processor generating the tile's center coordinates from tile index

    Accepted input format is "GEOMETRY" and output format is "TILE_INDEX"

    Attributes:
        __input (Processor): Processor from which data is read
        __geometry_format (str): Format of input string geometries. "WKT", "WKB" or "GeoJSON"
        __level (str): Tile matrix identifier to define intersecting tiles
    """

    input_formats_allowed = ["GEOMETRY"]
    geometry_formats_allowed = ["WKT", "WKB", "GeoJSON"]

    def __init__(self, input: Processor, **options):
        """Constructor method

        Args:
            input (Processor): Processor from which data is read
            **format (str): Format of input string geometries. "WKT", "WKB" or "GeoJSON"
            **level (str): Tile matrix identifier to define intersecting tiles

        Raises:
            ValueError: Input format is not allowed
            KeyError: A mandatory option is missing
            ValueError: A mandatory option is not valid
            ValueError: Provided level is not in the pivot TMS
        """  

        if input.format not in self.input_formats_allowed:
            raise ValueError(f"Input format {input.format} is not handled for Geometry2tileindexProcessor : allowed formats are {self.input_formats_allowed}")

        super().__init__("TILE_INDEX")

        self.__input = input

        try:

            if options["format"] not in self.geometry_formats_allowed:
                raise ValueError(f"Option 'format' for an input geometry is not handled ({options['format']}) : allowed formats are {self.geometry_formats_allowed}")

            self.__geometry_format = options["format"]

            if self.tms.get_level(options["level"]) is None:
                raise ValueError(f"Provided level is not in the TMS")

            self.__level = options["level"]

        except KeyError as e:
            raise KeyError(f"Option {e} is required to generate tile indices from geometries")

    def process(self) -> Iterator[Tuple[str, int, int]]:
        """Read a geometry from the input processor and extract tile index

        Geometry is parsed according to provided format. To determine intersecting tiles, geometry have to be a Polygon or a MultiPolygon. 
        For an input geometry, all intersecting tiles for the provided level are yielded

        Examples:

            Get intersecting tiles' indices

                from rok4_tools.tmsizer_utils.processors.map import Geometry2tileindexProcessor

                try:
                    # Creation of Processor source_processor with format GEOMETRY
                    processor = Geometry2tileindexProcessor(source_processor, level="15", format="GeoJSON" )
                    for item in processor.process():
                        (level, col, row) = item

                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[Tuple[str, int, int]]: Tile index (level, col, row)
        """  

        tile_matrix = self.tms.get_level(self.__level)

        if self.__input.format == "GEOMETRY":

            for item in self.__input.process():
                self._processed += 1

                try:
                    geom = None
                    if self.__geometry_format == "WKT":
                        geom = ogr.ForceToMultiPolygon(ogr.CreateGeometryFromWkt(item))
                    elif self.__geometry_format == "GeoJSON":
                        geom = ogr.ForceToMultiPolygon(ogr.CreateGeometryFromJson(item))
                    elif self.__geometry_format == "WKB":
                        geom = ogr.ForceToMultiPolygon(ogr.CreateGeometryFromWkb(item))
                
                    for i in range(0, geom.GetGeometryCount()):
                        g = geom.GetGeometryRef(i)
                        xmin, xmax, ymin, ymax = g.GetEnvelope()
                        col_min, row_min, col_max, row_max = tile_matrix.bbox_to_tiles((xmin, ymin, xmax, ymax))

                        for col in range(col_min, col_max + 1):
                            for row in range(row_min, row_max + 1):
                                tg = bbox_to_geometry(tile_matrix.tile_to_bbox(col, row))
                                if g.Intersects(tg):
                                    yield (self.__level, col, row)

                except Exception as e:
                    # La géométrie n'est pas valide, on la passe simplement
                    print(e)
                    continue

    def __str__(self) -> str:
        return f"Geometry2tileindexProcessor : {self._processed} {self.__input.format} items processed (format {self.__geometry_format}), extracting intersecting tile's indices"
