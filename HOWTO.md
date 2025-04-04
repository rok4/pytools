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

## MAKELAYER : un exemple de ligne de commande à lancer :
```sh
make-layer --pyramids s3://pyramids/ALTI.json  --name my_data --styles normal --title my_data --resampling bicubic --directory .
```
Voici le fichier de résultats au format JSON `my_data.json` obtenu :
```json 
{"title": "my_data", "abstract": "bicubic", "keywords": ["RASTER", "my_data"], "wmts": {"authorized": true}, "tms": {"authorized": true}, "bbox": {"south": 14.221788628396906, "west": -61.435546874999375,
 "north": 14.944784875087676, "east": -60.64453124999938}, "pyramids": [{"bottom_level": "13", "top_level": "0", "path": "s3://pyramids/ALTI.json"}], "wms": {"authorized": true, "crs": ["CRS:84", "IGNF:WG
S84G", "EPSG:3857", "EPSG:4258", "EPSG:4326"]}, "styles": ["normal", "normal"], "resampling": "nn"}
```

## PYROLYSE : un exemple de ligne de commande à lancer :
```sh
pyr2pyr --role check --conf Téléchargements/PM.json | pyr2pyr --role master --conf Téléchargements/PM.json |  pyr2pyr --role agent --conf Téléchargements/PM.json --split 3 | pyr2pyr --role finisher --conf Téléchargements/PM.json
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