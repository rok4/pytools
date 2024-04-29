"""
A processor is defined by its process function, the output format and optionnaly by the input allowed formats.

The output format informs of type of item yielded by the process function

Used formats are :

* `NONE`: Yielded item is a boolean, just once, at the end
* `FILELIKE`: Yielded item is a file-like object, just once, at the end
* `TILE_INDEX`: Yielded item is a tuple (level, col, row)
* `GETTILE_PARAMS`: Yielded item is a string, with WMTS GetTile query parameters (at least TILEMATRIXSET, TILEMATRIX, TILECOL and TILEROW)
* `GEOMETRY`: Yielded item is a string, a geometry with format WKT, WKB or GeoJSON
* `POINT`: Yielded item is a tuple (x, y)
* `COUNT`: Yielded item is an integer, just once, at the end
"""