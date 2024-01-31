import os
from unittest import mock
from unittest.mock import *

import pytest
from rok4.enums import PyramidType

from rok4_tools.global_utils.source import *


def test_init_source():
    try:
        datasources = Source("16", "9")
        assert datasources.bottom == "16"
        assert datasources.top == "9"
    except Exception as exc:
        assert False, f"Source creation raises an exception: {exc}"


@mock.patch("rok4.layer.Pyramid.from_descriptor")
def test_init_sourcepyramids(mocked_pyramid_class):
    tms_instance = MagicMock()
    tms_instance.srs = "EPSG:3857"
    tms_instance.name = "TMS"

    level_instance = MagicMock()
    level_instance.id = "10"
    level_instance.resolution = 1
    level_instance.tile_limits = {"min_row": 10, "max_row": 20, "min_col": 5, "max_col": 10}
    level_instance.slab_width = 16
    level_instance.slab_height = 16

    pyramid_instance = MagicMock()
    pyramid_instance.raster_specifications = {
        "channels": 3,
        "nodata": "255,255,255",
        "photometric": "rgb",
        "interpolation": "bicubic",
    }
    pyramid_instance.format = "TIFF_JPG_UINT8"
    pyramid_instance.tms = tms_instance
    pyramid_instance.descriptor = "s3://pyramids/SCAN1000.json"
    pyramid_instance.get_level.return_value = level_instance
    pyramid_instance.storage_s3_cluster = None
    pyramid_instance.type = PyramidType.RASTER
    pyramid_instance.channels = 3

    tms_instance2 = MagicMock()
    tms_instance2.srs = "EPSG:3857"
    tms_instance2.name = "TMS"

    level_instance2 = MagicMock()
    level_instance2.id = "10"
    level_instance2.resolution = 1
    level_instance2.tile_limits = {"min_row": 2, "max_row": 12, "min_col": 8, "max_col": 20}
    level_instance2.slab_width = 16
    level_instance2.slab_height = 16

    pyramid_instance2 = MagicMock()
    pyramid_instance2.raster_specifications = {
        "channels": 3,
        "nodata": "255,255,255",
        "photometric": "rgb",
        "interpolation": "bicubic",
    }
    pyramid_instance2.format = "TIFF_JPG_UINT8"
    pyramid_instance2.tms = tms_instance2
    pyramid_instance2.descriptor = "s3://pyramids/SCAN1000.json"
    pyramid_instance2.get_level.return_value = level_instance2
    pyramid_instance2.storage_s3_cluster = None
    pyramid_instance2.type = PyramidType.RASTER
    pyramid_instance2.channels = 3
    mocked_pyramid_class.side_effect = [pyramid_instance, pyramid_instance2]

    try:
        datasources = SourcePyramids(
            "10", "10", ["s3://pyramids/SCAN1000.json", "s3://pyramids/SCAN2000.json"]
        )
        assert datasources.format == "TIFF_JPG_UINT8"
        assert datasources.info_level("10") == (
            16,
            16,
            {"min_row": 2, "max_row": 20, "min_col": 5, "max_col": 20},
        )
        mocked_pyramid_class.assert_has_calls(
            [call("s3://pyramids/SCAN1000.json"), call("s3://pyramids/SCAN2000.json")]
        )
    except Exception as exc:
        assert False, f"Source pyramids creation raises an exception: {exc}"
