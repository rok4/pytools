"""Provide abstract class to define a unit processing data for tmsizer tool.

The module contains the following classes:

- `Processor` - Abstract class for all kinds of processor
"""

from typing import Dict, List, Tuple, Union, Iterator

from rok4.tile_matrix_set import TileMatrixSet

class Processor:
    """Abstract class for a processor

    A processor is a unit which treat data, item by item, and generate other items. An item could be a string, a tuple... 
    
    The output format define what the processor generate.

    Attributes:
        _processed (int): Count of input item processed
        _format (str): Processor's output items' format
    """

    tms = None
    """tms (TileMatrixSet): Pivot TMS for all processors"""

    def __init__(self, format: str = "UNKNOWN") -> None:
        """Constructor method

        Set the output format and the processed count to 0.

        Args:
            format (str, optional): Processor's output items' format. Defaults to "UNKNOWN".
        """
        self._processed = 0
        self._format = format

    def process(self) -> Iterator:
        """Abstract method for the processor's treatment function, as stream

        Raises:
            NotImplementedError: Subclasses have to implement this function
        """
        raise NotImplementedError("Subclasses have to implement this function")

    @classmethod
    def set_tms(cls, tms: TileMatrixSet):
        """Set the pivot TMS for all processors

        Args:
            tms (TileMatrixSet): Pivot TMS for processings
        """        
        cls.tms = tms

    @property
    def format(self) -> str:
        """Get the output format

        Returns:
            str: Processor's output items' format
        """        
        return self._format

    def __str__(self) -> str:
        return f"Processor : abstract class, only instance of subclasses can be used to treat data"
