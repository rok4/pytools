import subprocess
from unittest import mock
from unittest.mock import *

import pytest

from rok4_tools.joincache import *


def test_bad_role():
    with pytest.raises(Exception, match="bad_role"):
        result = subprocess.run(
            ["joincache", "--role", "null", "--conf", "path/to/conf.json"], stderr=subprocess.PIPE
        )
        if b"joincache: error: argument --role: invalid choice:" in result.stderr:
            raise Exception("bad_role")


def test_no_split():
    with pytest.raises(Exception, match="no_split"):
        result = subprocess.run(
            ["joincache", "--role", "agent", "--conf", "path/to/conf.json"], stdout=subprocess.PIPE
        )
        print(result.stdout)
        if (
            result.stdout
            == b"joincache: error: argument --split is required for the agent role and have to be a positive integer\n"
        ):
            raise Exception("no_split")


def test_no_conf():
    with pytest.raises(Exception, match="no_conf"):
        result = subprocess.run(["joincache", "--role", "master"], stdout=subprocess.PIPE)
        print(result.stdout)
        if (
            result.stdout
            == b"joincache: error: argument --conf is required for all roles except 'example'\n"
        ):
            raise Exception("no_conf")


@mock.patch("rok4_tools.joincache.get_data_str", return_value="{}")
@mock.patch("rok4_tools.joincache.args")
def test_bad_json(mocked_args, mocked_get_data_str):
    mocked_args.configuration = "path/to/conf.json"
    with pytest.raises(Exception) as exc:
        configuration()
    assert "Failed validating" in str(exc.value)
    mocked_get_data_str.assert_called_once_with("path/to/conf.json")


@mock.patch(
    "rok4_tools.joincache.get_data_str",
    return_value='{"datasources":[{"bottom":"6","top":"16","source":{"type":"PYRAMIDS","descriptors":["path"]}}],"pyramid":{"name":"joincache","root":"root"},"process":{"directory":"tmp","parallelization":3}}',
)
@mock.patch("rok4_tools.joincache.args")
def test_wrong_number_parallelization(mocked_args, mocked_get_data_str):
    mocked_args.configuration = "path/to/conf.json"
    mocked_args.role = "agent"
    mocked_args.split = 5
    with pytest.raises(Exception) as exc:
        configuration()
    assert (
        str(exc.value) == "Split number have to be consistent with the parallelization level: 5 > 3"
    )
    mocked_get_data_str.assert_called_once_with("path/to/conf.json")


@mock.patch(
    "rok4_tools.joincache.get_data_str",
    return_value='{"datasources":[{"bottom":"6","top":"16","source":{"type":"PYRAMIDS","descriptors":["path"]}}],"pyramid":{"name":"joincache","root":"root","mask":true},"process":{"directory":"tmp","parallelization":3,"mask":false}}',
)
@mock.patch("rok4_tools.joincache.args")
def test_impossible_mask(mocked_args, mocked_get_data_str):
    mocked_args.configuration = "path/to/conf.json"
    mocked_args.role = "master"
    with pytest.raises(Exception) as exc:
        configuration()
    assert (
        str(exc.value)
        == "The new pyramid cannot have mask if masks are not used during the process"
    )
    mocked_get_data_str.assert_called_once_with("path/to/conf.json")


@mock.patch(
    "rok4_tools.joincache.get_data_str",
    return_value='{"datasources":[{"bottom":"6","top":"16","source":{"type":"PYRAMIDS","descriptors":["path"]}}],"pyramid":{"name":"joincache","root":"root"},"process":{"directory":"tmp"}}',
)
@mock.patch("rok4_tools.joincache.args")
def test_default_value(mocked_args, mocked_get_data_str):
    mocked_args.configuration = "path/to/conf.json"
    mocked_args.role = "master"
    try:
        configuration()
    except Exception as e:
        assert False, f"There is an error with the default values: {e}"
    mocked_get_data_str.assert_called_once_with("path/to/conf.json")


@mock.patch(
    "rok4_tools.joincache.get_data_str",
    return_value='{"datasources":[{"bottom":"6","top":"16","source":{"type":"PYRAMIDS","descriptors":["path"]}}],"pyramid":{"name":"joincache","root":"root"},"process":{"directory":"tmp"},"logger":{"level":"WARNING"}}',
)
@mock.patch("rok4_tools.joincache.args")
def test_logger(mocked_args, mocked_get_data_str):
    mocked_args.configuration = "path/to/conf.json"
    mocked_args.role = "master"
    try:
        configuration()
    except Exception as e:
        assert False, f"There is an error with the logger: {e}"
    mocked_get_data_str.assert_called_once_with("path/to/conf.json")
