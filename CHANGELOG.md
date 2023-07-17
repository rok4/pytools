## 1.2.1

### [Added]

* Outil MAKE-LAYER : génère un descripteur de couche compatible avec le serveur à partir des pyramides de données à utiliser
* Ajout de la publication PyPI dans la CI GitHub

### [Changed]

* Renommage pour plus de cohérence avec les pratiques :
    * Le module rok4 est renommé : rok4lib -> rok4
    * Le module d'outil est renommé : rok4tools -> rok4_tools. Le package a le nom rok4-tools
    * Le script make-layer.py -> make_layer.py
* Passage de la configuration du projet dans le fichier `pyproject.toml`

## 1.1.0

### [Changed]

* Outil PYR2PYR :
  * Les pyramides source et destination peuvent être sur des clusters S3 différents. Ils sont précisés lors de la recopie des dalles. Pour préciser le cluster dans le chemin vers le descripteur de la pyramide source (ou l'emplacement de la pyramide destination), il suffit de suffixer le nom du bucket avec `@{hôte du cluster}`.

## 1.0.0

### [Added]

* Outil PYR2PYR de copie de pyramide : copie d'une pyramide d'un stockage à une autre. Contrôle les signatures MD5 si présente dans le fichier liste. Fonctionne en plusieurs modes :
  * 3 pour la recopie : master, agent et finisher
  * 2 pour l'aide : example et check
