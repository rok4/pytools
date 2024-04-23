"""Provide processor to read or write data.

The module contains the following classes:

- `StdinProcessor` - Read data from standard input
- `PathinProcessor` - Read data from a file/object
- `StdoutProcessor` - Write data to standard output
- `PathoutProcessor` - Write data to file/object
"""

import os
import sys
from typing import Dict, List, Tuple, Union, Iterator
import tempfile
from tqdm import tqdm

from rok4.storage import put_data_str, copy

from rok4_tools.tmsizer_utils.processors.processor import Processor

class StdinProcessor(Processor):
    """Processor to read from standard input

    Data is read line by line. Data's format cannot be detected and have to be provided by user.

    Attributes:
        __pbar (tqdm): Progress bar, to print read progression to standard output
    """

    def __init__(self, format: str, pbar: bool = False):
        """Constructor method

        Args:
            format (str): Format of read and processor's output data
            pbar (bool, optional): Print a read progress bar ? Defaults to False.
        """        

        super().__init__(format)
        self.__pbar = None
        if pbar:
            self.__pbar = tqdm()

    def process(self) -> Iterator[str]:
        """Read from standard input line by line and yield it

        Examples:

            Read from standard input (GetTile urls), line by line, and print it

                from rok4_tools.tmsizer_utils.processors.io import StdinProcessor

                try:
                    reader_processor = StdinProcessor("GETTILE_PARAMS")
                    for line in reader_processor.process():
                        print(line)

                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[str]: line from the standard input
        """        

        for line in sys.stdin:
            self._processed += 1
            if self.__pbar is not None:
                self.__pbar.update(1)
            yield line.rstrip()

    def __str__(self) -> str:
        return f"StdinProcessor : {self._processed} lines read (format {self._format}) from standard input"



class PathinProcessor(Processor):
    """Processor to read from file or object

    Data is read line by line. Data's format cannot be detected and have to be provided by user.

    Attributes:
        __path (str): Path to file or object to read
        __pbar (tqdm): Progress bar, to print read progression to standard output
    """

    def __init__(self, format: str, path: str, pbar: bool = False):
        """Constructor method

        Args:
            format (str): Format of read and processor's output data
            path (str): Path to file or object to read
            pbar (bool, optional): Print a read progress bar ? Defaults to False.
        """        

        super().__init__(format)
        self.__path = path
        self.__pbar = None
        if pbar:
            self.__pbar = tqdm()

    def process(self) -> Iterator[str]:
        """Read from the file or object line by line and yield it

        The input file or object is copied in a temporary file to be read line by line.

        Examples:

            Read from an S3 object (geometries), line by line, and print it

                from rok4_tools.tmsizer_utils.processors.io import PathinProcessor

                try:
                    reader_processor = PathinProcessor("GEOMETRY", "s3://bucket/data.txt")
                    for line in reader_processor.process():
                        print(line)

                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[str]: line from the file or object
        """     
        
        tmp = tempfile.NamedTemporaryFile(mode="r", delete=False)
        copy(self.__path, tmp.name)
        with open(tmp.name) as f:
            for line in f:
                self._processed += 1
                if self.__pbar is not None:
                    self.__pbar.update(1)
                yield line.rstrip()
        tmp.close()
        os.remove(tmp.name)
        

    def __str__(self) -> str:
        return f"PathinProcessor : {self._processed} lines read (format {self._format}) from {self.__path}"


class StdoutProcessor(Processor):
    """Processor to write to standard output

    Data is read from the input processor and write as string, item by item. Output format is "NONE"

    Attributes:
        __input (Processor): Processor from which data is read
    """

    def __init__(self, input: Processor):
        """Constructor method

        All input format are accepted except "FILELIKE".

        Args:
            input (Processor): Processor from which data is read

        Raises:
            ValueError: Input format is not allowed
        """        

        if input.format == "FILELIKE":
            raise ValueError(f"Input format {input.format} is not handled for StdoutProcessor")

        super().__init__("NONE")
        self.__input = input

    def process(self) -> Iterator[bool]:
        """Read items one by one from the input processor and write it to the standard output

        Yield True only once at the end

        Examples:

            Write results into standard output

                from rok4_tools.tmsizer_utils.processors.io import StdoutProcessor

                try:
                    # Creation of Processor source_processor
                    writer_processor = StdoutProcessor(source_processor)
                    status = writer_processor.process().__next__()
                    print("Results successfully written to S3 object")

                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[bool]: True when work is done
        """   

        for item in self.__input.process():
            self._processed += 1
            print(str(item))
        
        yield True

    def __str__(self) -> str:
        return f"StdoutProcessor : {self._processed} {self._format} items write to standard output"


class PathoutProcessor(Processor):
    """Processor to write to file or object

    Data is read from the input processor and write as string, item by item. Output format is "NONE"

    Attributes:
        __input (Processor): Processor from which data is read
        __path (str): Path to file or object to write
    """

    def __init__(self, input: Processor, path: str):
        """Constructor method

        All input format are accepted.

        Args:
            input (Processor): Processor from which data is read
            path (str): Path to file or object to write 
        """        
        super().__init__("NONE")
        self.__input = input
        self.__path = path

    def process(self) -> Iterator[bool]:
        """Read items one by one from the input processor and write it to the standard output

        Items are write into a temporary file, then copied to final location (file or object). Yield True only once at the end

        Examples:

            Write results into a S3 object

                from rok4_tools.tmsizer_utils.processors.io import PathoutProcessor

                try:
                    # Creation of Processor source_processor
                    writer_processor = PathoutProcessor(source_processor, "s3://bucket/results.txt")
                    status = writer_processor.process().__next__()
                    print(f"Results successfully written to S3 object")

                except Exception as e:
                    print("{e}")

        Yields:
            Iterator[bool]: True when work is done
        """ 

        if self.__input.format == "FILELIKE":
            tmp = tempfile.NamedTemporaryFile(mode="wb", delete=False)
            f = self.__input.process().__next__()
            self._processed += 1
            tmp.write(f.read())
            tmp.close()
            copy(tmp.name, self.__path)
            os.remove(tmp.name)

        else:
            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False)
            for item in self.__input.process():
                self._processed += 1
                tmp.write(f"{str(item)}\n")
            tmp.close()
            copy(tmp.name, self.__path)
            os.remove(tmp.name)

        yield True

    def __str__(self) -> str:
        return f"PathoutProcessor : {self._processed} {self._format} items write to {self.__path}"
