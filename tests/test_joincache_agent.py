import os
import subprocess
from unittest import mock
from unittest.mock import *

import pytest

from rok4_tools.joincache_utils.agent import *


@mock.patch("rok4_tools.joincache_utils.agent.Pyramid.from_descriptor")
@mock.patch("rok4_tools.joincache_utils.agent.storage.link")
@mock.patch("rok4_tools.joincache_utils.agent.os.system")
def test_ok(mocked_os_system, mocked_link, mocked_from_descriptor):
    pyramid = MagicMock()
    pyramid.raster_specifications = {
        "channels": 3,
        "nodata": "255,255,255",
        "photometric": "rgb",
        "interpolation": "bicubic",
    }
    pyramid.format = "TIFF_ZIP_FLOAT32"

    mocked_from_descriptor.return_value = pyramid
    mocked_os_system.return_value = 0

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
            "directory": "tests/fixtures/list_agent",
        },
    }
    resultat = work(config, 1)
    mocked_from_descriptor.assert_called_once_with("path")
