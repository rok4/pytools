## PYR2PYR : un exemple de ligne de commande à lancer :
```sh
pyr2pyr --role check --conf Téléchargements/PM.json | pyr2pyr --role master --conf Téléchargements/PM.json |  pyr2pyr --role agent --conf Téléchargements/PM.json --split 3 | pyr2pyr --role finisher --conf Téléchargements/PM.json
```

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
pyrolyse --pyramid s3://pyramids/ALTI.json --output resultats.json --tiles --progress --deciles --ratio 1
```

Le résultat donne le fichier de résultats `resultats.json` suivant : 
```json
{"global": {"slab_count": 17, "slab_sizes": [77819.0, 77844.6, 77860.6, 77975.8, 78644.6, 82379.0, 119482.99999999999, 335572.59999999986, 825531.0000000003, 2665611.0, 3715851.0], "link_count": 0, "tile_
sizes": [283.0, 283.0, 283.0, 283.0, 283.0, 283.0, 283.0, 283.0, 283.0, 287.0, 310.0]}, "levels": {"13": {"slab_count": 4, "slab_sizes": [77819.0, 199047.80000000002, 320276.60000000003, 441505.3999999999
7, 863780.6000000003, 1436579.0, 2009377.3999999997, 2523703.7999999993, 2921086.2, 3318468.6, 3715851.0], "link_count": 0, "tile_sizes": [283.0, 283.0, 283.0, 283.0, 283.0, 283.0, 283.0, 283.0, 283.0, 28
3.0, 283.0]}, "12": {"slab_count": 1, "slab_sizes": [3077163], "link_count": 0, "tile_sizes": [283]}, "11": {"slab_count": 1, "slab_sizes": [911435], "link_count": 0, "tile_sizes": [283]}, "10": {"slab_co
unt": 1, "slab_sizes": [298987], "link_count": 0, "tile_sizes": [283]}, "9": {"slab_count": 1, "slab_sizes": [136827], "link_count": 0, "tile_sizes": [283]}, "8": {"slab_count": 1, "slab_sizes": [93467], 
"link_count": 0, "tile_sizes": [283]}, "7": {"slab_count": 1, "slab_sizes": [82379], "link_count": 0, "tile_sizes": [283]}, "6": {"slab_count": 1, "slab_sizes": [79211], "link_count": 0, "tile_sizes": [28
3]}, "5": {"slab_count": 1, "slab_sizes": [78267], "link_count": 0, "tile_sizes": [283]}, "4": {"slab_count": 1, "slab_sizes": [77995], "link_count": 0, "tile_sizes": [283]}, "3": {"slab_count": 1, "slab_
sizes": [77899], "link_count": 0, "tile_sizes": [283]}, "2": {"slab_count": 1, "slab_sizes": [77851], "link_count": 0, "tile_sizes": [283]}, "1": {"slab_count": 1, "slab_sizes": [77851], "link_count": 0, 
"tile_sizes": [310]}, "0": {"slab_count": 1, "slab_sizes": [77835], "link_count": 0, "tile_sizes": [293]}}, "perfs": [0.002020657000684878, 0.0021233711999229855, 0.0021787890007544776, 0.0023693994000495
875, 0.0024838273999193915, 0.0027725769996322924, 0.002991372598626185, 0.0032549347990425298, 0.004386014799820259, 0.005820798000422655, 0.006239024000024074]}
```

## TMSIZER : un exemple de lignes de commande avec différents filtres :

Dans l'exemple ci-après, on a 81 requêtes pris en compte pour générer l'image, en fonction des filtres choisis et de la zone couverte par la carte de chaleur:
```sh
tmsizer -i requests.txt --tms PM -io levels=15,12 -io layer=LAYER.NAME2 -if GETTILE_PARAMS -of HEATMAP -oo bbox=65000,6100000,665000,6500000 -oo dimensions=600x400 -o heatmap.tif
HeatmapProcessor : 81 hits on image with dimensions (600, 400) and bbox (65000.0, 6100000.0, 665000.0, 6500000.0) (resolutions (1000.0, 1000.0))
```

Dans l'exemple ci-après, on a 110 requêtes pris en compte pour générer l'image, en fonction des filtres choisis et de la zone couverte par la carte de chaleur:
```sh
tmsizer -i requests.txt --tms PM -io levels=15,14 -io layer=LAYER.NAME1 -if GETTILE_PARAMS -of HEATMAP -oo bbox=65000,6100000,665000,6500000 -oo dimensions=600x400 -o heatmap.tif
HeatmapProcessor : 110 hits on image with dimensions (600, 400) and bbox (65000.0, 6100000.0, 665000.0, 6500000.0) (resolutions (1000.0, 1000.0))
```

Dans l'exemple ci-après, on a 59 requêtes pris en compte pour générer l'image, en fonction des filtres choisis et de la zone couverte par la carte de chaleur:
```sh
tmsizer -i requests.txt --tms PM -io levels=0,15 -io layer=LAYER.NAME2 -if GETTILE_PARAMS -of HEATMAP -oo bbox=65000,6100000,665000,6500000 -oo dimensions=600x400 -o heatmap.tif
HeatmapProcessor : 59 hits on image with dimensions (600, 400) and bbox (65000.0, 6100000.0, 665000.0, 6500000.0) (resolutions (1000.0, 1000.0))
```