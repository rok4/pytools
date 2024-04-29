import os
import sys
from io import StringIO
from unittest import mock
from unittest.mock import *

import pytest

from rok4.exceptions import StorageError

from rok4_tools.tmsizer_utils.processors.io import *

def test_stdinprocessor():
    sys.stdin = StringIO("data1\ndata2\n")

    try:
        processor = StdinProcessor("TOTO")
    except Exception as exc:
        assert False, f"StdinProcessor usage raises an exception: {exc}"
        
    assert processor.format == "TOTO"
    assert list(processor.process()) == ['data1', 'data2']


def test_pathinprocessor_ok():

    try:
        processor = PathinProcessor("TOTO", "tests/fixtures/processors/data.txt")
    except Exception as exc:
        assert False, f"PathinProcessor usage raises an exception: {exc}"
        
    assert processor.format == "TOTO"
    assert list(processor.process()) == ['data1', 'data2']


def test_pathinprocessor_nok():

    with pytest.raises(StorageError):
        processor = PathinProcessor("TOTO", "wrong/path.txt")
        processor.process().__next__()

def test_stdoutprocessor_nok():

    processor_instance = MagicMock()
    processor_instance.format = "FILELIKE"

    with pytest.raises(ValueError):
        processor = StdoutProcessor(processor_instance)

@patch('sys.stdout', new_callable = StringIO)
def test_stdoutprocessor_ok(mocked_stdout):

    processor_instance = MagicMock()
    processor_instance.format = "TOTO"
    processor_instance.process.return_value = iter(["data1", "data2"])

    try:
        processor = StdoutProcessor(processor_instance)
        assert processor.process().__next__() == True

    except Exception as exc:
        assert False, f"StdoutProcessor usage raises an exception: {exc}"
    
    assert processor.format == "NONE"
    assert mocked_stdout.getvalue() == 'data1\ndata2\n'

@mock.patch(
    "rok4_tools.tmsizer_utils.processors.io.copy",
    side_effect=StorageError("FILE", "Cannot copy file")
)
def test_pathoutprocessor_nok(mocked_copy):

    processor_instance = MagicMock()
    processor_instance.format = "TOTO"
    processor_instance.process.return_value = iter(["data1", "data2"])

    with pytest.raises(StorageError):
        processor = PathoutProcessor(processor_instance, "/path/to/file.txt")
        processor.process().__next__()

    mocked_copy.assert_called_once_with(ANY, "/path/to/file.txt")

def test_pathoutprocessor_ok():

    processor_instance = MagicMock()
    processor_instance.format = "TOTO"
    processor_instance.process.return_value = iter(["data1", "data2"])

    try:
        processor = PathoutProcessor(processor_instance, "tests/fixtures/processors/output.txt")
        assert processor.process().__next__() == True

    except Exception as exc:
        assert False, f"StdoutProcessor usage raises an exception: {exc}"
    
    with open("tests/fixtures/processors/output.txt") as f:
        lignes = f.read()

    assert lignes == "data1\ndata2\n"

    os.remove("tests/fixtures/processors/output.txt")
