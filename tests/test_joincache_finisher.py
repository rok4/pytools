import os
import shutil
from unittest import mock
from unittest.mock import *

from rok4.enums import PyramidType, SlabType, StorageType

from rok4_tools.joincache_utils.finisher import *


@mock.patch("rok4_tools.joincache_utils.finisher.SourcePyramids")
@mock.patch("rok4_tools.joincache_utils.finisher.Pyramid.from_other")
@mock.patch("rok4_tools.joincache_utils.finisher.storage.copy")
def test_ok(mocked_copy, mocked_from_other, mocked_source):
    files = [f for f in os.listdir("tests/fixtures/list_agent")]
    for file in files:
        print(file)
        shutil.copy2(
            os.path.join("tests/fixtures/list_agent", file), os.path.join("tests/fixtures/list_finisher", file)
        )
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
            "directory": "tests/fixtures/list_finisher",
        },
    }
    storage_pyramid = {"type": StorageType.S3, "root": "bucket"}

    work(config)
    mocked_source.assert_has_calls([call("6", "10", ["path"]), call("11", "16", ["path2"])])
    mocked_from_other.assert_called_once_with(
        source1.pyramids[0], "joincache.png", storage_pyramid, mask=True
    )
