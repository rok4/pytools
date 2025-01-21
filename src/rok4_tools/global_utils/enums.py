#! python3  # noqa: E265

# standard lib
from enum import Enum


class SourceType(Enum):
    """Source's type"""

    PYRAMIDS = "PYRAMIDS"
    WMS = "WMS"
