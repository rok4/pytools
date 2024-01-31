# Outils ROK4 Python

![ROK4 Logo](https://rok4.github.io/assets/images/rok4.png)

Ce projet contient des outils de gestion des pyramides de données, écrits en Python.

## Installer les outils

Installations système requises :

* debian : `apt install python3-rados python3-gdal`

Depuis [PyPI](https://pypi.org/project/rok4-tools/) : `pip install rok4-tools`

Depuis [GitHub](https://github.com/rok4/pytools/releases/) : `pip install https://github.com/rok4/pytools/releases/download/x.y.z/rok4_tools-x.y.z-py3-none-any.whl`

L'environnement d'exécution doit avoir accès aux librairies système. Dans le cas d'une utilisation au sein d'un environnement python, précisez bien à la création `python3 -m venv --system-site-packages .venv`.


## Utiliser les outils

### PYR2PYR

PYR2PYR est un outil de copie d'une pyramide d'un stockage à un autre. Il est possible de filtrer les dalles transférée en précisant une taille limite sous laquelle les données ne sont pas recopiées. La copie des dalles est parallélisable. Si des signatures MD5 sont présente dans le fichier liste, elles sont contrôlées après recopie.

Un exemple de configuration est affichable avec la commande `pyr2pyr --role example` et l'appel `pyr2pyr --role check --conf conf.json` permet de valider un fichier de configuration. Le fichier de configuration peut être un objet, auquel cas le chemin doit être préfixé par le type de stockage (exemple : `s3://bucket/configuration.json`)

#### Fonctionnement

Une copie complète d'une pyramide implique l'utilisation de l'outil avec les 3 modes suivants, dans cet ordre (tous les modes utilisent le fichier de configuration) :

1. Rôle `master`
    * Actions : génération des N TODO lists, déposé dans un dossier précisé dans la configuration (peut être un stockage objet).
    * Appel : `pyr2pyr --role master --conf conf.json`
2. Rôle `agent` :
    * Actions : lecture de la TODO list depuis le dossier de traitement et recopie des dalles
    * Appel (un appel par TODO list) : `pyr2pyr --role agent --conf conf.json --split X`
3. Rôle `finisher` :
    * Actions : lecture des TODO lists pour écrire le fichier liste final et écriture du descripteur de la pyramide en sortie.
    * Appel : `pyr2pyr --role finisher --conf conf.json`

![Enchaînement PYR2PYR](./docs/images/pyr2pyr.png)

#### Configuration

Possibilités de contenu du fichier JSON (généré à partir du schéma JSON avec `jsonschema2md bin/pyr2pyr.schema.json /dev/stdout`)

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

MAKE-LAYER est un outil générant un descripteur de couche compatible avec le serveur à partir des pyramides de données à utiliser

Utilisation : `make-layer [-h] --pyramids storage://path/to/pyr.json[>BOTTOM>TOP] [storage://path/to/pyr.json[>BOTTOM>TOP] ...] --name my data [--styles normal [normal ...]] [--title my data]`

### JOINCACHE

L'outil JOINCACHE génèrent une pyramide raster à partir d'autres pyramide raster compatibles (même TMS, dalles de même dimensions, canaux au même format). La composition se fait verticalement (choix des pyramides sources par niveau) et horizontalement (choix des pyramides source par zone au sein d'un niveau).

Un exemple de configuration est affichable avec la commande `joincache --role example` et l'appel `joincache --role check --conf conf.json` permet de valider un fichier de configuration. Le fichier de configuration peut être un objet, auquel cas le chemin doit être préfixé par le type de stockage (exemple : `s3://bucket/configuration.json`)

#### Fonctionnement

Une copie complète d'une pyramide implique l'utilisation de l'outil avec les 3 modes suivants, dans cet ordre (tous les modes utilisent le fichier de configuration) :

1. Rôle `master`
    * Actions : contrôle du fichier de configuration et des pyramides, identification du travail, génération des N TODO lists, déposé dans un dossier précisé dans la configuration (peut être un stockage objet).
    * Appel : `joincache --role master --conf conf.json`
2. Rôle `agent` :
    * Actions : lecture de la TODO list depuis le dossier de traitement et traitement de chaque ligne
    * Appel (un appel par TODO list) : `joincache --role agent --conf conf.json --split X`
3. Rôle `finisher` :
    * Actions : lecture des TODO lists pour écrire le fichier liste final et écriture du descripteur de la pyramide en sortie.
    * Appel : `joincache --role finisher --conf conf.json`

#### Configuration

Possibilités de contenu du fichier JSON (généré à partir du schéma JSON avec `jsonschema2md src/rok4_tools/joincache_utils/schema.json /dev/stdout`)

- **`logger`** *(object)*: Paramètres du logger.
  - **`layout`** *(string)*: Format du log, selon la syntaxe Log4perl. Default: `%5p : %m (%M) %n`.
  - **`file`** *(string)*: Chemin vers le fichier où écrire les logs. Les logs sont dans la sortie standard si ce paramètre n'est pas fourni.
  - **`level`** *(string)*: Niveau de log. Must be one of: `['DEBUG', 'INFO', 'WARN', 'ERROR', 'ALWAYS']`. Default: `WARN`.
- **`datasources`** *(array)*: Pyramides sources.
  - **Items** *(object)*
    - **`bottom`** *(string)*: Niveau du TMS de la pyramide en sortie pour lequel la source est utilisée.
    - **`top`** *(string)*: Niveau du TMS de la pyramide en sortie jusqu'auquel la source sera utilisée.
    - **`source`** *(object)*: Base PostgreSQL comme source de données.
      - **`type`** *(string)*: Type de source. Must be one of: `['PYRAMIDS']`.
      - **`descriptors`** *(array)*: Liste des chemins vers les descripteurs de pyramides (toutes doivent avoir les même caractéristiques (stockage, pixel, TMS...).
        - **Items** *(string)*
- **`pyramid`** *(object)*: Génération d'une nouvelle pyramide comme produit de fusion.
  - **`name`** *(string)*: Nom de la nouvelle pyramide fusionnée.
  - **`root`** *(string)*: Racine de stockage : un dossier pour le type FILE, le nom du pool en CEPH, le nom du bucket en S3 et le nom du container en SWIFT.
  - **`mask`** *(boolean)*: Doit-on écrire les masques de données dans la pyramide en sortie. Si oui, ils seront utilisés dans les traitements. Default: `False`.

## Compiler la suite d'outils

```sh
apt install python3-venv python3-rados python3-gdal
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade build bump2version
bump2version --current-version 0.0.0 --new-version x.y.z patch

# Run unit tests
python3 -m pip install -e .[test]
# To use system installed modules rados and osgeo
echo "/usr/lib/python3/dist-packages/" >.venv/lib/python3.10/site-packages/system.pth
python3 -c 'import sys; print (sys.path)'
# Run tests
coverage run -m pytest
# Get tests report and generate site
coverage report -m
coverage html -d dist/tests/

# Build documentation
python3 -m pip install -e .[doc]
pdoc3 --html --output-dir dist/ rok4_tools

# Build artefacts
python3 -m build
```

## Contribuer

* Installer les dépendances de développement :

    ```sh
    python3 -m pip install -e[dev]
    ```

* Consulter les [directives de contribution](./CONTRIBUTING.md)

## Publier la suite d'outils sur Pypi

Configurer le fichier `$HOME/.pypirc` avec les accès à votre compte PyPI.

```sh
python3 -m pip install --upgrade twine
python3 -m twine upload --repository pypi dist/rok4_tools-x.y.z-py3-none-any.whl dist/rok4_tools-x.y.z.tar.gz
```
