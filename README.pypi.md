# ROK4 Python tools

![ROK4 Logo](https://rok4.github.io/assets/images/rok4.png)

The `rok4-tools` package help to use [ROK4 project](https://rok4.github.io/) concepts, like Tile Matrix Sets, data pyramids or layers.

## Installation

Required system packages :
* debian : `apt install python3-rados python3-gdal`

The `rok4` package is available on :
* [PyPI](https://pypi.org/project/rok4/) : `pip install rok4`
* [GitHub](https://github.com/rok4/core-python/releases/) : `pip install https://github.com/rok4/core-python/releases/download/<version>/rok4-<version>-py3-none-any.whl`

## Tools

### PYR2PYR

PYR2PYR allow to copy a pyramid from a storage to another one. It is possible to ignore slab under a provided size. Copy is parallelized. If MD5 hash are in the pyramid's list file, they are used to check integrity after copy.

To obtain an example of JSON configuration, call `pyr2pyr --role example`. To check a JSON configuration, call `pyr2pyr --role check --conf conf.json`. JSON configuratio can be a file or a S3 object(use a path's prefix, for example : `s3://bucket/configuration.json`)

#### Usage

A full copy requires the tool call with the three modes (all need the JSON configuration), in this order :

1. `master` role
    * Actions : write N TODO lists, in a file or s3 directory.
    * Call : `pyr2pyr --role master --conf conf.json`
2. `agent` role :
    * Actions : read the TODO list from the work directory and copy slabs
    * Call (one by TODO list) : `pyr2pyr --role agent --conf conf.json --split X`
3. `finisher` role:
    * Actions : read all TODO lists and write the output pyramid's list file and its descriptor
    * Call : `pyr2pyr --role finisher --conf conf.json`

![PYR2PYR workflow](https://rok4.github.io/pytools/versions/latest/docs/images/pyr2pyr.png)

#### Configuration

JSON configuration content (generated from the JSON schema with `jsonschema2md bin/pyr2pyr.schema.json /dev/stdout`)

- **`logger`** *(object)*: Logger configuration.
    - **`layout`** *(string)*: Log format, according to logging python library. Default: `%(asctime)s %(levelname)s: %(message)s`.
    - **`file`** *(string)*: Path to log file. Standard output is used if not provided.
    - **`level`** *(string)*: Log level. Must be one of: `['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'NOTSET']`. Default: `WARNING`.
- **`from`** *(object)*: Pyramid to copy.
    - **`descriptor`** *(string)*: Path to pyramid's descriptor to copy.
- **`to`** *(object)*: Pyramid to write.
    - **`name`** *(string)*: Output pyramid's name.
    - **`storage`** *(object)*
        - **`type`** *(string)*: Storage type. Must be one of: `['FILE', 'S3', 'CEPH']`.
        - **`root`** *(string)*: Storage root : a directory for FILE storage, pool name for CEPH storage, bucket name for S3 storage.
        - **`depth`** *(integer)*: Tree depth, only for FILE storage. Minimum: `1`. Default: `2`.
- **`process`** *(object)*: Processing parameters.
    - **`directory`** *(string)*: Directory to write copies to process, FILE directory or S3/CEPH prefix.
    - **`parallelization`** *(integer)*: Parallelization level, number of todo lists and agents working at the same time. Minimum: `1`. Default: `1`.
    - **`follow_links`** *(boolean)*: Do we follow links (data slabs in others pyramids than the 'from' one). Default: `False`.
    - **`slab_limit`** *(integer)*: Minimum slab size (if under, we do not copy). Minimum: `0`. Default: `0`.


### MAKE-LAYER

MAKE-LAYER generate a layer's descriptor, [ROK4 server](https://github.com/rok4/server/) compliant, from pyramids' descriptors

#### Usage

`make-layer [-h] --pyramids storage://path/to/pyr.json[>BOTTOM>TOP] [storage://path/to/pyr.json[>BOTTOM>TOP] ...] --name my data [--styles normal [normal ...]] [--title my data]`
