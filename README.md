# Vectipy

Simple Mapbox Vector Tiles (MVT) server with Flask and PostGIS.

## Quickstart

⚠️ You need a fonctionnal PostGIS (>2.4) base.

Clone the repo, create a virtual python environment and install requierements

```bash
git clone git@github.com:jbdesbas/vectipy.git

cd vectipy

virtualenv -p python3 venv

source venv/bin/activate

pip install -r requierements.txt

```

Create a _.env_ file with your credentials or export them

```bash
export PG_HOST=my_db_host
export PG_PORT=5432
export PG_DATABASE=my_db_name
export PG_USER=my_db_user
export PG_PASSWORD=my_db_password
```

Generate a layers definition file _layers.toml_. You can edit it if necessary.
```bash
python vectipy.py scan_db > layers.toml
```

Enjoy !
```bash
python vectipy.py run -p 5000
```

Use following routes 
- http://localhost:5000/MY_LAYER.json TileJSON file
- http://localhost:5000/MY_LAYER/{z}/{x}/{y}.pbf Tiles endpoints
- http://localhost:5000/map/MY_LAYER Layer preview

## Features :
- [x] Easy to deploy MVT (pbf) server
- [x] TileJson metadata
- [x] Frontend preview with [MapLibre GL](https://github.com/maplibre/maplibre-gl-js) 
- [x] Choose exposed fields
- [ ] Support MVT Feature ID
- [ ] CQL Filter
- [ ] Cache system
- [ ] Manage style files ?



