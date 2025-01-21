from unittest import mock
from unittest.mock import *

from rok4.enums import PyramidType

from rok4_tools.global_utils.enums import SourceType
from rok4_tools.global_utils.source import *


def test_init_source():
    try:
        datasource = Source("16", "9")
        assert datasource.bottom == "16"
        assert datasource.top == "9"
    except Exception as exc:
        assert False, f"Source creation raises an exception: {exc}"


@mock.patch("rok4.layer.Pyramid.from_descriptor")
def test_sourcepyramids_ok(mocked_pyramid_class):
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
        datasource = SourcePyramids(
            "10",
            "10",
            {"descriptors": ["s3://pyramids/SCAN1000.json", "s3://pyramids/SCAN2000.json"]},
        )
        assert datasource.type == SourceType.PYRAMIDS
        assert datasource.format == "TIFF_JPG_UINT8"
        assert datasource.info_level("10") == (
            16,
            16,
            {"min_row": 2, "max_row": 20, "min_col": 5, "max_col": 20},
        )
        mocked_pyramid_class.assert_has_calls(
            [call("s3://pyramids/SCAN1000.json"), call("s3://pyramids/SCAN2000.json")]
        )
    except Exception as exc:
        assert False, f"Pyramids source creation raises an exception: {exc}"


def test_sourcewms_ok():
    try:
        datasource = SourceWMS(
            "10",
            "10",
            {
                "type": "WMS",
                "endpoint": "https://services.geo/wms",
                "layers": ["layer1", "layer2"],
                "extra_params": {"titi": "toto"},
            },
        )
    except Exception as exc:
        assert False, f"WMS source creation raises an exception: {exc}"

    assert datasource.type == SourceType.WMS
    assert datasource.format == "image/jpeg"
    assert datasource.endpoint == "https://services.geo/wms"
    assert (
        datasource.get_getmap_request("EPSG:2154", (200, 280), (0, 10, 100, 150))
        == "https://services.geo/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=layer1,layer2&STYLES=,&SRS=EPSG:2154&BBOX=0,10,100,150&WIDTH=200&HEIGHT=280&FORMAT=image/jpeg&titi=toto"
    )
    assert (
        datasource.get_getcapabilities_request()
        == "https://services.geo/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities&titi=toto"
    )
