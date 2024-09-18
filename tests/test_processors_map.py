import os
import sys
from unittest import mock
from unittest.mock import *

import pytest

from rok4_tools.tmsizer_utils.processors.map import *
from rok4_tools.tmsizer_utils.processors.processor import *

@mock.patch.dict(os.environ, {"ROK4_TMS_DIRECTORY": "tests/fixtures/processors"}, clear=True)
def test_gettile2tileindexprocessor():

    tms = TileMatrixSet("PM")
    Processor.set_tms(tms)  

    processor_instance = MagicMock()
    processor_instance.format = "GETTILE_PARAMS"
    processor_instance.process.return_value = iter([
        "/wmts?layer=layer&style=normal&tilematrixset=PM_5_16&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=20&TileCol=549681&TileRow=390037",
        "/private/wmts?layer=layer&style=normal&tilematrixset=PM&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=9&TileCol=262&TileRow=187",
        "/wmts?layer=layer&style=normal&tilematrixset=LAMB93&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=18&TileCol=130803&TileRow=89692",
        "/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=layer&STYLE=normal&FORMAT=image%2Fjpeg&TILEMATRIXSET=PM&TILEMATRIX=20&TILEROW=748016&TILECOL=1076958",
        "/wms-v/ows?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&transparent=true&version=1.1.1&format=image%2Fpng&LAYERS=layer&WIDTH=256&HEIGHT=256&CRS=EPSG%3A3857&STYLES=&BBOX=137892.39902645722%2C5507287.887946948%2C137968.8360547424%2C5507364.3249752335"
    ])

    try:
        processor = Gettile2tileindexProcessor(processor_instance, levels="20")

    except Exception as exc:
        assert False, f"Gettile2tileindexProcessor usage raises an exception: {exc}"
    
    assert list(processor.process()) == [("20", 549681, 390037), ("20", 1076958, 748016)]


@mock.patch.dict(os.environ, {"ROK4_TMS_DIRECTORY": "tests/fixtures/processors"}, clear=True)
def test_tileindex2gettileprocessor():

    tms = TileMatrixSet("PM")
    Processor.set_tms(tms)  

    processor_instance = MagicMock()
    processor_instance.format = "TILE_INDEX"
    processor_instance.process.return_value = iter([("20", 654165, 3541), ("12", 6541, 98)])

    try:
        processor = Tileindex2gettileProcessor(processor_instance)

    except Exception as exc:
        assert False, f"Gettile2tileindexProcessor usage raises an exception: {exc}"
    
    assert list(processor.process()) == [
        "TILEMATRIXSET=PM&TILEMATRIX=20&TILECOL=654165&TILEROW=3541",
        "TILEMATRIXSET=PM&TILEMATRIX=12&TILECOL=6541&TILEROW=98"
    ]


@mock.patch.dict(os.environ, {"ROK4_TMS_DIRECTORY": "tests/fixtures/processors"}, clear=True)
def test_tileindex2pointprocessor():

    tms = TileMatrixSet("PM")
    Processor.set_tms(tms)  

    processor_instance = MagicMock()
    processor_instance.format = "TILE_INDEX"
    processor_instance.process.return_value = iter([("20", 654165, 3541), ("12", 15, 98)])

    try:
        processor = Tileindex2pointProcessor(processor_instance)

    except Exception as exc:
        assert False, f"Gettile2tileindexProcessor usage raises an exception: {exc}"
    
    assert list(processor.process()) == [
        (4963725.070554057, 19902157.474953223),
        (-19885857.27867141, 19073790.290169697)
    ]



@mock.patch.dict(os.environ, {"ROK4_TMS_DIRECTORY": "tests/fixtures/processors"}, clear=True)
def test_geometry2tileindexprocessor():

    tms = TileMatrixSet("PM")
    Processor.set_tms(tms)  

    processor_instance = MagicMock()
    processor_instance.format = "GEOMETRY"
    processor_instance.process.return_value = iter(["POLYGON((0 0,10 0,10 10,10 0,0 0))"])

    try:
        processor = Geometry2tileindexProcessor(processor_instance, level="12", format="WKT")

    except Exception as exc:
        assert False, f"Gettile2tileindexProcessor usage raises an exception: {exc}"
    
    assert list(processor.process()) == [
        ('12', 2047, 2047),
        ('12', 2048, 2047)
    ]