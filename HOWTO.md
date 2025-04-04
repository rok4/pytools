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