import os
import subprocess
from unittest import mock
from unittest.mock import *

import pytest
from rok4.enums import PyramidType, SlabType, StorageType

from rok4_tools.joincache_utils.master import *


@mock.patch("rok4_tools.joincache_utils.master.SourcePyramids")
def test_different_tms(mocked_source):
    source1 = MagicMock()
    source1.tms.name = "PM"
    source1.format = "TIFF_PNG_UINT8"
    source1.channels = 3
    source1.type = PyramidType.RASTER

    source2 = MagicMock()
    source2.tms.name = "WLD"
    source2.format = "TIFF_PNG_UINT8"
    source2.channels = 3
    source2.type = PyramidType.RASTER

    mocked_source.side_effect = [source1, source2]
    config = {
        "datasources": [
            {"bottom": "6", "top": "10", "source": {"descriptors": ["path"]}},
            {"bottom": "11", "top": "16", "source": {"descriptors": ["path2"]}},
        ]
    }
    with pytest.raises(Exception) as exc:
        resultat = work(config)
    assert "Sources pyramids cannot have two different TMS" in str(exc.value)

    mocked_source.assert_has_calls([call("6", "10", ["path"]), call("11", "16", ["path2"])])


@mock.patch("rok4_tools.joincache_utils.master.SourcePyramids")
def test_different_format(mocked_source):
    source1 = MagicMock()
    source1.tms.name = "PM"
    source1.format = "TIFF_PNG_UINT8"
    source1.channels = 3
    source1.type = PyramidType.RASTER

    source2 = MagicMock()
    source2.tms.name = "PM"
    source2.format = "TIFF_PNG_UINT16"
    source2.channels = 3
    source2.type = PyramidType.RASTER

    mocked_source.side_effect = [source1, source2]
    config = {
        "datasources": [
            {"bottom": "6", "top": "10", "source": {"descriptors": ["path"]}},
            {"bottom": "11", "top": "16", "source": {"descriptors": ["path2"]}},
        ]
    }
    with pytest.raises(Exception) as exc:
        resultat = work(config)
    assert "Sources pyramids cannot have two different format" in str(exc.value)

    mocked_source.assert_has_calls([call("6", "10", ["path"]), call("11", "16", ["path2"])])


@mock.patch("rok4_tools.joincache_utils.master.SourcePyramids")
def test_different_channels(mocked_source):
    source1 = MagicMock()
    source1.tms.name = "PM"
    source1.format = "TIFF_PNG_UINT8"
    source1.channels = 3
    source1.type = PyramidType.RASTER

    source2 = MagicMock()
    source2.tms.name = "PM"
    source2.format = "TIFF_PNG_UINT8"
    source2.channels = 1
    source2.type = PyramidType.RASTER

    mocked_source.side_effect = [source1, source2]
    config = {
        "datasources": [
            {"bottom": "6", "top": "10", "source": {"descriptors": ["path"]}},
            {"bottom": "11", "top": "16", "source": {"descriptors": ["path2"]}},
        ]
    }
    with pytest.raises(Exception) as exc:
        resultat = work(config)
    assert "Sources pyramids cannot have two different numbers of channels" in str(exc.value)

    mocked_source.assert_has_calls([call("6", "10", ["path"]), call("11", "16", ["path2"])])


@mock.patch("rok4_tools.joincache_utils.master.SourcePyramids")
def test_not_raster(mocked_source):
    source1 = MagicMock()
    source1.tms.name = "PM"
    source1.format = "TIFF_PNG_UINT8"
    source1.channels = 3
    source1.type = PyramidType.RASTER

    source2 = MagicMock()
    source2.tms.name = "PM"
    source2.format = "TIFF_PNG_UINT8"
    source2.channels = 3
    source2.type = PyramidType.VECTOR

    mocked_source.side_effect = [source1, source2]
    config = {
        "datasources": [
            {"bottom": "6", "top": "10", "source": {"descriptors": ["path"]}},
            {"bottom": "11", "top": "16", "source": {"descriptors": ["path2"]}},
        ]
    }
    with pytest.raises(Exception) as exc:
        resultat = work(config)
    assert "Some sources pyramids are not a raster" in str(exc.value)

    mocked_source.assert_has_calls([call("6", "10", ["path"]), call("11", "16", ["path2"])])


@mock.patch("rok4_tools.joincache_utils.master.SourcePyramids")
@mock.patch("rok4_tools.joincache_utils.master.Pyramid.from_other")
def test_false_name_S3(mocked_from_other, mocked_source):
    pyramid1 = MagicMock()
    pyramid1.storage_type = StorageType.S3
    source1 = MagicMock()
    source1.tms.name = "PM"
    source1.format = "TIFF_PNG_UINT8"
    source1.channels = 3
    source1.type = PyramidType.RASTER
    source1.pyramids = [pyramid1]

    pyramid2 = MagicMock()
    pyramid2.storage_type = StorageType.S3
    source2 = MagicMock()
    source2.tms.name = "PM"
    source2.format = "TIFF_PNG_UINT8"
    source2.channels = 3
    source2.type = PyramidType.RASTER
    source2.type = PyramidType.RASTER
    source2.pyramids = [pyramid2]

    mocked_source.side_effect = [source1, source2]

    source3 = MagicMock()
    source3.storage_s3_cluster = "blabla"
    mocked_from_other.return_value = source3

    storage_pyramid = {"type": StorageType.S3, "root": "bucket"}

    config = {
        "datasources": [
            {"bottom": "6", "top": "10", "source": {"descriptors": ["path"]}},
            {"bottom": "11", "top": "16", "source": {"descriptors": ["path2"]}},
        ],
        "pyramid": {"name": "blabla/joincache.png", "root": "bucket", "mask": "true"},
        "process": {"parallelization": 3},
    }
    with pytest.raises(Exception) as exc:
        resultat = work(config)
    assert "Do not set S3 cluster host into output bucket name" in str(exc.value)

    mocked_source.assert_has_calls([call("6", "10", ["path"]), call("11", "16", ["path2"])])
    mocked_from_other.assert_called_once_with(
        source1.pyramids[0], "blabla/joincache.png", storage_pyramid, mask="true"
    )


@mock.patch("rok4_tools.joincache_utils.master.SourcePyramids")
@mock.patch("rok4_tools.joincache_utils.master.Pyramid.from_other")
def test_datasources_with_same_level(mocked_from_other, mocked_source):
    level6 = MagicMock()
    level6.id = "6"
    pyramid1 = MagicMock()
    pyramid1.storage_type = StorageType.S3
    pyramid1.get_levels.return_value = [level6]
    source1 = MagicMock()
    source1.tms.name = "PM"
    source1.format = "TIFF_PNG_UINT8"
    source1.channels = 3
    source1.type = PyramidType.RASTER
    source1.pyramids = [pyramid1]

    pyramid2 = MagicMock()
    pyramid2.storage_type = StorageType.S3
    pyramid2.get_levels.return_value = [level6]
    source2 = MagicMock()
    source2.tms.name = "PM"
    source2.format = "TIFF_PNG_UINT8"
    source2.channels = 3
    source2.type = PyramidType.RASTER
    source2.type = PyramidType.RASTER
    source2.pyramids = [pyramid2]

    mocked_source.side_effect = [source1, source2]

    source3 = MagicMock()
    source3.storage_s3_cluster = None
    mocked_from_other.return_value = source3

    storage_pyramid = {"type": StorageType.S3, "root": "bucket"}

    config = {
        "datasources": [
            {"bottom": "6", "top": "10", "source": {"descriptors": ["path"]}},
            {"bottom": "6", "top": "16", "source": {"descriptors": ["path2"]}},
        ],
        "pyramid": {"name": "joincache.png", "root": "bucket", "mask": "true"},
        "process": {"parallelization": 3},
    }
    with pytest.raises(Exception) as exc:
        resultat = work(config)
    assert "Different datasources cannot define the same level" in str(exc.value)

    mocked_source.assert_has_calls([call("6", "10", ["path"]), call("6", "16", ["path2"])])
    mocked_from_other.assert_called_once_with(
        source1.pyramids[0], "joincache.png", storage_pyramid, mask="true"
    )


@mock.patch("rok4_tools.joincache_utils.master.SourcePyramids")
@mock.patch("rok4_tools.joincache_utils.master.Pyramid.from_other")
def test_ok(mocked_from_other, mocked_source):
    files = [f for f in os.listdir("tests/fixtures/list_master")]
    for file in files:
        os.remove(os.path.join("tests/fixtures/list_master", file))
    level6 = MagicMock()
    level6.id = "6"
    pyramid1 = MagicMock()
    pyramid1.storage_type = StorageType.S3
    pyramid1.get_levels.return_value = [level6]
    pyramid1.list_generator.return_value = [
        (
            (SlabType.DATA, "6", 1, 1),
            {"link": False, "md5": None, "root": "path", "slab": "DATA_6_1_1"},
        ),
        (
            (SlabType.MASK, "6", 1, 1),
            {"link": False, "md5": None, "root": "path", "slab": "MASK_6_1_1"},
        ),
        (
            (SlabType.DATA, "6", 2, 1),
            {"link": False, "md5": None, "root": "path", "slab": "DATA_6_2_1"},
        ),
        (
            (SlabType.MASK, "6", 2, 1),
            {"link": False, "md5": None, "root": "path", "slab": "MASK_6_2_1"},
        ),
    ]
    pyramid1.get_slab_path_from_infos.side_effect = ["MASK_6_1_1", "MASK_6_2_1"]
    pyramid3 = MagicMock()
    pyramid3.storage_type = StorageType.S3
    pyramid3.get_levels.return_value = [level6]
    pyramid3.list_generator.return_value = [
        (
            (SlabType.DATA, "6", 1, 1),
            {"link": False, "md5": None, "root": "path3", "slab": "DATA_6_1_1"},
        ),
        (
            (SlabType.MASK, "6", 1, 1),
            {"link": False, "md5": None, "root": "path3", "slab": "MASK_6_1_1"},
        ),
    ]
    pyramid3.get_slab_path_from_infos.return_value = "MASK_6_1_1"
    source1 = MagicMock()
    source1.tms.name = "PM"
    source1.format = "TIFF_PNG_UINT8"
    source1.channels = 3
    source1.type = PyramidType.RASTER
    source1.pyramids = [pyramid1, pyramid3]

    level11 = MagicMock()
    level11.id = "11"
    pyramid2 = MagicMock()
    pyramid2.storage_type = StorageType.S3
    pyramid2.get_levels.return_value = [level11]
    pyramid2.list_generator.return_value = [
        (
            (SlabType.DATA, "11", 1, 1),
            {"link": False, "md5": None, "root": "path2", "slab": "DATA_11_1_1"},
        ),
        (
            (SlabType.MASK, "11", 1, 1),
            {"link": False, "md5": None, "root": "path2", "slab": "MASK_11_1_1"},
        ),
    ]
    pyramid2.get_slab_path_from_infos.return_value = "MASK_11_1_1"
    source2 = MagicMock()
    source2.tms.name = "PM"
    source2.format = "TIFF_PNG_UINT8"
    source2.channels = 3
    source2.type = PyramidType.RASTER
    source2.type = PyramidType.RASTER
    source2.pyramids = [pyramid2]

    mocked_source.side_effect = [source1, source2]

    source3 = MagicMock()
    source3.storage_s3_cluster = None
    source3.get_slab_path_from_infos.side_effect = [
        "s3://path_final/DATA_6_1_1",
        "s3://path_final/MASK_6_1_1",
        "s3://path_final/DATA_6_2_1",
        "s3://path_final/MASK_6_2_1",
        "s3://path_final/DATA_11_1_1",
        "s3://path_final/MASK_11_1_1",
    ]
    mocked_from_other.return_value = source3

    storage_pyramid = {"type": StorageType.S3, "root": "bucket"}

    config = {
        "datasources": [
            {"bottom": "6", "top": "10", "source": {"descriptors": ["path"]}},
            {"bottom": "11", "top": "16", "source": {"descriptors": ["path2"]}},
        ],
        "pyramid": {"name": "joincache.png", "root": "bucket", "mask": True},
        "process": {
            "parallelization": 3,
            "mask": True,
            "only_links": False,
            "directory": "tests/fixtures/list_master",
        },
    }

    resultat = work(config)
    with open("tests/fixtures/list_master/todo.1.list") as f:
        lignes = f.read()

    assert (
        lignes
        == "c2w s3://path/DATA_6_1_1\nc2w s3://path/MASK_6_1_1\nc2w s3://path3/DATA_6_1_1\nc2w s3://path3/MASK_6_1_1\noNt\nw2c s3://path_final/DATA_6_1_1\nw2c s3://path_final/MASK_6_1_1\nlink s3://path_final/DATA_11_1_1 s3://path2/DATA_11_1_1 2\n"
    )

    mocked_source.assert_has_calls([call("6", "10", ["path"]), call("11", "16", ["path2"])])
    mocked_from_other.assert_called_once_with(
        source1.pyramids[0], "joincache.png", storage_pyramid, mask=True
    )
