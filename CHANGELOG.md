# Changelog
Tous les changements sont consignés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/) et ce projet respecte le [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Added
- Outil TMSIZER :
    * ajout de la conversion GETTILE_PARAMS -> SLAB, pour avoir les informations sur la dalle contenant la tuile (indices et chemin de stockage)
    * ajout des conversions PYRAMID_LIST -> SLAB et PYRAMID_LIST -> HEATMAP pour avoir des informations de dalle ou une carte de chaleur à partir du fichier liste d'une pyramide
### Changed
- Refonte du CHANGELOG au format [Keep a Changelog](https://keepachangelog.com/)

## [1.5.2] - 2024-11-06
### Added
- Outil TMSIZER : possibilité de préciser une aire prédéinie à la place de la bbox et un niveau à la place des dimensions pour l'écriture d'une heatmap (une tuile du niveau correspondra à un pixel)

## [1.5.1] - 2024-09-18
### Added
- Outil TMSIZER : ajout d'une option pour filtrer sur la couche pour le format en entrée GETTILE_PARAMS : fourniture d'une liste de couches avec l'option `layers`

### Changed
- Outil TMSIZER : modification de l'option pour filtrer sur le niveau pour le format en entrée GETTILE_PARAMS : fourniture d'une liste de niveaux et l'option `level` devient `levels`

## [1.5.0] - 2024-04-30
### Added
- Outil TMSIZER : convertit des informations en d'autres en s'appuyant sur un TMS pivot. Conversions implémentées :
    * GETTILE_PARAMS -> HEATMAP
    * GETTILE_PARAMS -> COUNT
    * GEOMETRY -> GETTILE_PARAMS
- Outil PYROLYSE : compile des statistiques (nombre de dalles / tuile, taille, temps d'accès) sur une pyramide de données, au global et par niveau

## [1.3.2] - 2024-01-31
### Added
- Outil JOINCACHE génèrent une pyramide à partir d'autres pyramides raster compatibles. Fonctionne en plusieurs modes :
    * 3 pour la génération : master, agent et finisher
    * 2 pour l'aide : example et check
- Création de la classe "source" pour charger des sources de données

### Changed
- Division de l'outil PYR2PYR en un fichier principal (pyr2pyr.py) et des fichier par rôles (pyr2pyr_utils/agent.py, pyr2pyr_utils.master.py, pyr2pyr_utils.finisher.py)
- Gestion des documentations des différentes versions avec l'outil [mike](https://github.com/jimporter/mike)

## [1.2.1] - 2023-03-10
### Added
- Outil MAKE-LAYER : génère un descripteur de couche compatible avec le serveur à partir des pyramides de données à utiliser
- Ajout de la publication PyPI dans la CI GitHub

### Changed
- Renommage pour plus de cohérence avec les pratiques :
    * Le module rok4 est renommé : rok4lib -> rok4
    * Le module d'outil est renommé : rok4tools -> rok4_tools. Le package a le nom rok4-tools
    * Le script make-layer.py -> make_layer.py
- Passage de la configuration du projet dans le fichier `pyproject.toml`

## [1.1.0] - 2023-01-13
### Changed
- Outil PYR2PYR :
    * Les pyramides source et destination peuvent être sur des clusters S3 différents. Ils sont précisés lors de la recopie des dalles. Pour préciser le cluster dans le chemin vers le descripteur de la pyramide source (ou l'emplacement de la pyramide destination), il suffit de suffixer le nom du bucket avec `@{hôte du cluster}`.

## [1.0.0] - 2022-11-28
### Added
- Outil PYR2PYR de copie de pyramide : copie d'une pyramide d'un stockage à une autre. Contrôle les signatures MD5 si présente dans le fichier liste. Fonctionne en plusieurs modes :
    * 3 pour la recopie : master, agent et finisher
    * 2 pour l'aide : example et check

[Unreleased]: https://github.com/rok4/pytools/compare/v1.5.2...HEAD
[1.5.2]: https://github.com/rok4/pytools/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/rok4/pytools/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/rok4/pytools/compare/v1.3.2...v1.5.0
[1.3.2]: https://github.com/rok4/pytools/compare/v1.2.1...v1.3.2
[1.2.1]: https://github.com/rok4/pytools/compare/v1.1.0...v1.2.1
[1.1.0]: https://github.com/rok4/pytools/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/rok4/pytools/releases/tag/v1.0.0
