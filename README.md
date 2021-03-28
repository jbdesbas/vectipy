# Vectipy

Serveur simple de tuiles vectorielles MVT de couches PostGIS.

## Fonctionnalités :

- Publier une couches PostGIS en MVT (tuiles vecteurs pbf)
- Publication du fichier de métadonnées tileJSON (https://github.com/mapbox/tilejson-spec)
- Facile à déployer sans geoserveur, Python uniquement (virtualenv, supervisor, heroku, etc.)
- Autodescription des couches présentes (scan de la db, puis génération d'un fichier de config avec champs et emprise)
- Symbologie simpe par défaut, carte de (pré)visualisation (MapLibre)

[ Routes disponibles : flux (pbf), tilejson, prévisualisation ]


## Points forts
- Publier un flux geographique sans recourir à un geoserveur (un simple appli python facilement déployable : supervisor/virtualenv, heroku, etc..)
- Performances (cache flask + génération mvt depuis postgis + pbf)


## Limitations
- Fonctionne seulement avec PostGIS > 2.4
- Le format MVT commence seulement à être bien intégré dans QGIS


## Future
- Support WFS
- Support GeoJson
- Cache (Flask-Cache)
- Surcouche du fichier de config (choisir les champs pour chaque couche)

## Requierements
- *PostGIS >= 2.4*
- Nginx/Apache, supervisor, gunicorn (prod)

```
git clone git@github.com:jbdesbas/vectipy.git

cd vectipy

virtualenv -p python3 venv

source venv/bin/activate

pip install -r requierements.txt

#configure db_param

python vectipy.py scan_db > layers.toml

python vectipy.py run -p 5000
```
