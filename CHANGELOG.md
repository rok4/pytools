# Outils ROK4 Python

## Summary

PYR2PYR gère les copies inter cluster S3

## Changelog

### [Changed]

* Outil PYR2PYR :
  * Les pyramides source et destination peuvent être sur des clusters S3 différents. Ils sont précisés lors de la recopie des dalles. Pour préciser le cluster dans le chemin vers le descripteur de la pyramide source (ou l'emplacement de la pyramide destination), il suffit de suffixer le nom du bucket avec `@{hôte du cluster}`.


<!-- 
### [Added]

### [Changed]

### [Deprecated]

### [Removed]

### [Fixed]

### [Security] 
-->