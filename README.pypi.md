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

To obtain an example of JSON configuration, call `pyr2pyr --role example`. To check a JSON configuration, call `pyr2pyr --role check --conf conf.json`. JSON configuration can be a file or a S3 object(use a path's prefix, for example : `s3://bucket/configuration.json`)

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

![PYR2PYR workflow](https://rok4.github.io/pytools/latest/images/pyr2pyr.png)

#### Configuration

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

### JOINCACHE

JOINCACHE build a raster pyramid from consistent pyramids (same TMS, same slab size, same bands format). Source pyramids are provided per levels.

To obtain an example of JSON configuration, call `joincache --role example`. To check a JSON configuration, call `joincache --role check --conf conf.json`. JSON configuration can be a file or a S3 object(use a path's prefix, for example : `s3://bucket/configuration.json`)

#### Usage

A full build requires the tool call with the three modes (all need the JSON configuration), in this order :

1. `master` role
    * Actions : write N TODO lists, in a file or s3 directory.
    * Call : `joincache --role master --conf conf.json`
2. `agent` role :
    * Actions : read the TODO list from the work directory and build or link slabs
    * Call (one by TODO list) : `joincache --role agent --conf conf.json --split X`
3. `finisher` role:
    * Actions : read all TODO lists and write the output pyramid's list file and its descriptor
    * Call : `joincache --role finisher --conf conf.json`

#### Configuration

- **`logger`** *(object)*: Paramètres du logger. Cannot contain additional properties.
  - **`layout`** *(string)*: Log format, according to logging python library. Default: `"%(asctime)s %(levelname)s: %(message)s"`.
  - **`file`** *(string)*: Path to log file. Standard output is used if not provided.
  - **`level`** *(string)*: Log level. Must be one of: `["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"]`. Default: `"WARNING"`.
- **`datasources`** *(array)*: Source pyramids.
  - **Items** *(object)*: Cannot contain additional properties.
    - **`bottom`** *(string, required)*: Bottom level's usage for source pyramids.
    - **`top`** *(string, required)*: Top level's usage for source pyramids.
    - **`source`** *(object, required)*: Pyramids as data source. Cannot contain additional properties.
      - **`type`** *(string, required)*: Source type. Must be one of: `["PYRAMIDS"]`.
      - **`descriptors`** *(array, required)*: Paths to pyramids' descriptors (all with the same characteritics : TMS, formats...). Length must be at least 1.
        - **Items** *(string)*
- **`pyramid`** *(object)*: Output pyramid's storage informations. Cannot contain additional properties.
  - **`name`** *(string, required)*: Output pyramid's name.
  - **`root`** *(string, required)*: Storage root : a directory for FILE storage, pool name for CEPH storage, bucket name for S3 storage.
  - **`mask`** *(boolean)*: Mask export ? If true, masks are used for processing. Default: `false`.
- **`process`** *(object)*: Processing parameters. Cannot contain additional properties.
  - **`directory`** *(string, required)*: Directory to write copies to process, FILE directory or S3/CEPH prefix.
  - **`parallelization`** *(integer)*: Parallelization level, number of todo lists and agents working at the same time. Minimum: `1`. Default: `1`.
  - **`mask`** *(boolean)*: Source masks used for processing ? Default: `false`.
  - **`only_links`** *(boolean)*: Only links are made ? If true, only top slab will be considered and linked. Default: `false`.

### MAKE-LAYER

MAKE-LAYER generate a layer's descriptor, [ROK4 server](https://github.com/rok4/server/) compliant, from pyramids' descriptors

#### Usage

`make-layer [-h] --pyramids storage://path/to/pyr.json[>BOTTOM>TOP] [storage://path/to/pyr.json[>BOTTOM>TOP] ...] --name my data [--styles normal [normal ...]] [--title my data]`


### PYROLYSE

PYROLYSE analyse a pyramid, to get slab/tile size and count, for hte entire pyramide and per level. Slab and tile sizes are not all processed : a ratio limits the number of measures. This ratio is assumed for a level (to avoid to have mainly data for the best level). If tile statistics is enabled, access time are compiled.

For size and access time, it's possible to get deciles and not all values.

#### Usage

`pyrolyse [-h] [--version] --pyramid storage://path/to/pyr.json [--json storage://path/to/conf.json] [--tiles] [--deciles] [--ratio N]`