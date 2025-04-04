## JOINCACHE : Exemple de fichier de configuration :

*   Exemple de fichier de configuration valide `exemple_valid_json.json`:
  ```json
{
    "logger": {
        "level": "INFO"
    },
    "datasources": [
        {
            "top": "0",
            "bottom": "1",
            "source": {
                "type": "PYRAMIDS",
                "descriptors": [
		    "~/Téléchargements/ALTI.json"]
            }
        }
    ],
    "pyramid": {
        "name": "joincache",
        "root": "pyramids"
    },
    "process": {
        "directory": "s3://bucket_temp/joincache",
        "parallelization": 1,
        "mask": true
    }
}
```

*   Résultat obtenu :
  ```sh
   joincache --role check --conf  exemple_valid_json.json 
    Valid configuration !
  ```

## TMSIZER : un exemple de lignes de commande avec différents filtres :
```sh
tmsizer -i requests.txt --tms PM -io levels=15,12 -io layer=LAYER.NAME2 -if GETTILE_PARAMS -of HEATMAP -oo bbox=65000,6100000,665000,6500000 -oo dimensions=600x400 -o heatmap.tif
HeatmapProcessor : 81 hits on image with dimensions (600, 400) and bbox (65000.0, 6100000.0, 665000.0, 6500000.0) (resolutions (1000.0, 1000.0))
```

```sh
tmsizer -i requests.txt --tms PM -io levels=15,14 -io layer=LAYER.NAME1 -if GETTILE_PARAMS -of HEATMAP -oo bbox=65000,6100000,665000,6500000 -oo dimensions=600x400 -o heatmap.tif
HeatmapProcessor : 110 hits on image with dimensions (600, 400) and bbox (65000.0, 6100000.0, 665000.0, 6500000.0) (resolutions (1000.0, 1000.0))
```

```sh
tmsizer -i requests.txt --tms PM -io levels=0,15 -io layer=LAYER.NAME2 -if GETTILE_PARAMS -of HEATMAP -oo bbox=65000,6100000,665000,6500000 -oo dimensions=600x400 -o heatmap.tif
HeatmapProcessor : 59 hits on image with dimensions (600, 400) and bbox (65000.0, 6100000.0, 665000.0, 6500000.0) (resolutions (1000.0, 1000.0))
```