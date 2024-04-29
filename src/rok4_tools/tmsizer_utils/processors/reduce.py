"""Provide processor combining data. Input data is transformed and accumulated and the result is yielded juste once, at the end.

The module contains the following classes:

- `CountProcessor` - Count the number of item read from the input processor
- `HeatmapProcessor` - Generate an heat map with all point coordinate read from the input processor
"""
import sys
import numpy as np
from typing import Dict, List, Tuple, Union, Iterator
from math import floor

import rasterio
from rasterio.transform import from_origin
from rasterio.io import MemoryFile
from rasterio import logging
logging.getLogger().setLevel(logging.ERROR)

from rok4_tools.tmsizer_utils.processors.processor import Processor

class CountProcessor(Processor):
    """Processor counting the number of item read from the input processor

    All input formats are allowed and output format is "COUNT"

    Attributes:
        __input (Processor): Processor from which data is read
    """

    def __init__(self, input: Processor):
        """Constructor method

        Args:
            input (Processor): Processor from which data is read
        """  

        super().__init__("COUNT")

        self.__input = input

    def process(self) -> Iterator[int]:
        """Count number of input item

        Yield count only once at the end

        Examples:

            Get input items count

                from rok4_tools.tmsizer_utils.processors.reduce import CountProcessor

                try:
                    # Creation of Processor source_processor
                    processor = CountProcessor(source_processor, level="15", format="GeoJSON" )
                    count = processor.process().__next__()
                    print(f"{count} items in source_processor")

                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[int]: the count of input items
        """  

        for item in self.__input.process():
            self._processed += 1

        yield self._processed

    def __str__(self) -> str:
        return f"CountProcessor : {self._processed} {self.__input.format} items counted"


class HeatmapProcessor(Processor):
    """Processor counting the number of item read from the input processor

    Accepted input format is "POINT" and output format is "FILELIKE". Output file-like object is an in-memory GeoTIFF

    Attributes:
        __input (Processor): Processor from which data is read
        __bbox (Tuple[float, float, float, float]): Bounding box of the heat map (xmin,ymin,xmax,ymax)
        __dimensions (Tuple[int, int]): Pixel dimensions of the heat map (width, height)
        __resolutions (Tuple[float, float]): Pixel resolution (x resolution, y resolution)
    """

    input_formats_allowed = ["POINT"]

    def __init__(self, input: Processor, **options):
        """Constructor method

        Args:
            input (Processor): Processor from which data is read
            **bbox (str): Bounding box of the heat map. Format "<xmin>,<ymin>,<xmax>,<ymax>". Coordinates system have to be the pivot TMS' one
            **dimensions (str): Pixel dimensions of the heat map.Format "<width>x<height>"

        Raises:
            ValueError: Input format is not allowed
            KeyError: A mandatory option is missing
            ValueError: A mandatory option is not valid
            ValueError: Provided level is not in the pivot TMS
        """  

        if input.format not in self.input_formats_allowed:
            raise Exception(f"Input format {input.format} is not handled for HeatmapProcessor : allowed formats are {self.input_formats_allowed}")

        super().__init__("FILELIKE")

        self.__input = input

        try:
            try:
                self.__bbox = [float(c) for c in options["bbox"].split(",")]
                self.__bbox = tuple(self.__bbox)
            except ValueError as e:
                raise ValueError(f"Option 'bbox' contains non float values : {e}")

            if len(self.__bbox) != 4 or self.__bbox[0] >= self.__bbox[2] or self.__bbox[1] >= self.__bbox[3]:
                raise ValueError(f"Option 'bbox' have to be provided with format <xmin>,<ymin>,<xmax>,<ymax> (floats, min < max)")

            try:
                self.__dimensions = [int(d) for d in options["dimensions"].split("x")]
                self.__dimensions = tuple(self.__dimensions)
            except ValueError as e:
                raise ValueError(f"Option 'dimensions' contains non integer values : {e}")

            if len(self.__dimensions) != 2 or self.__dimensions[0] <= 0 or self.__dimensions[1] <= 0:
                raise ValueError(f"Option 'dimensions' have to be provided with format <width>x<height> (positive integers)")

            self.__resolutions = (
                (self.__bbox[2] - self.__bbox[0]) / self.__dimensions[0],
                (self.__bbox[3] - self.__bbox[1]) / self.__dimensions[1]
            )

        except KeyError as e:
            raise KeyError(f"Option {e} is required for a heatmap processing")

    def process(self) -> Iterator[MemoryFile]:
        """Read point coordinates from the input processor and accumule them as a heat map

        Points outsides the provided bounding box are ignored.

        Examples:

            Get intersecting tiles' indices

                from rok4_tools.tmsizer_utils.processors.reduce import HeatmapProcessor

                try:
                    # Creation of Processor source_processor with format POINT
                    
                    processor = HeatmapProcessor(source_processor, bbox="65000,6100000,665000,6500000", dimensions="600x400" )
                    f = processor.process().__next__()

                    with open("hello.txt", "w") as my_file:
                        my_file.write(f.read())
                    
                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[rasterio.io.MemoryFile]: In-memory GeoTIFF
        """  

        data = np.zeros((self.__dimensions[1], self.__dimensions[0]), dtype=np.uint32)

        if self.__input.format == "POINT":

            for item in self.__input.process():
                self._processed += 1

                (x_center, y_center) = item

                if x_center > self.__bbox[2] or y_center > self.__bbox[3] or x_center < self.__bbox[0] or y_center < self.__bbox[1]:
                    continue

                pcol = floor((x_center - self.__bbox[0]) / self.__resolutions[0])
                prow = floor((self.__bbox[3] - y_center) / self.__resolutions[1])

                data[prow][pcol] += 1

        memfile = MemoryFile()
        with memfile.open(
            driver='GTiff',
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs=rasterio.CRS.from_string(self.tms.srs),
            nodata=0,
            transform=from_origin(self.__bbox[0], self.__bbox[3], self.__resolutions[0], self.__resolutions[1]),
        ) as dataset:
            dataset.write(data, indexes=1)

        yield memfile

    def __str__(self) -> str:
        return f"HeatmapProcessor : {self._processed} hits on image with dimensions {self.__dimensions} and bbox {self.__bbox}"
