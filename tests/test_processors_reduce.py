import os
import sys
from unittest import mock
from unittest.mock import *

import pytest

from rok4_tools.tmsizer_utils.processors.reduce import *
from rok4_tools.tmsizer_utils.processors.processor import *

def test_countprocessor():

    processor_instance = MagicMock()
    processor_instance.format = "TOTO"
    processor_instance.process.return_value = iter(["data1", "data2", "data3", "data4"])

    try:
        processor = CountProcessor(processor_instance)
        assert processor.process().__next__() == 4

    except Exception as exc:
        assert False, f"CountProcessor usage raises an exception: {exc}"
    
    assert processor.format == "COUNT"

@mock.patch.dict(os.environ, {"ROK4_TMS_DIRECTORY": "tests/fixtures/processors"}, clear=True)
def test_heatmapprocessor_ok():

    tms = TileMatrixSet("PM")
    Processor.set_tms(tms)  

    processor_instance = MagicMock()
    processor_instance.format = "POINT"
    processor_instance.process.return_value = iter([(1,1), (1,2), (25,15), (11,19)])

    try:
        processor = HeatmapProcessor(processor_instance, bbox="0,0,30,20", dimensions="3x2")
        fo = processor.process().__next__()

    except Exception as exc:
        assert False, f"HeatmapProcessor usage raises an exception: {exc}"
    
    assert processor.format == "FILELIKE"
    assert isinstance(fo, rasterio.io.MemoryFile)

    with fo.open() as dataset:
        data_array = dataset.read()
        assert data_array[0][0][0] == 0
        assert data_array[0][0][1] == 1
        assert data_array[0][0][2] == 1
        assert data_array[0][1][0] == 2
        assert data_array[0][1][1] == 0
        assert data_array[0][1][2] == 0
