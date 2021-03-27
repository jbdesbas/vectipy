from flask import current_app
import psycopg2
import psycopg2.extras
from psycopg2 import sql

import math
TILE_SCHEMA = 'public'

def get_layer_info(layer_name, layers_config,dbparam):
    print(layers_config)
    entry = [e for e in layers_config['layer'] if e.get('name')==layer_name]
    print(entry)
    return entry[0]

def _load_tile(dbparam, layer_name, x, y, z, columns, geom_column='geom', extent=4096, buffer=256, clip=True, srid=4326):
    tile = None

    # Generic query to select data from postgres
	# Each table has to contain columns: 'id', 'value', 'extrude', 'geom'
    # TODO : ne pas récupérer la geom dans les champs attribut
    # TODO : prevoir un dict pour préciser les champs à retourner (sinon, tous les champs)
    # TODO : attention, sensible injection (cf https://www.psycopg.org/docs/sql.html#module-usage )
    # avec geoalchemy https://gis.stackexchange.com/questions/291418/st-asmvt-in-geoalchemy2

    cols= ', '.join( list( map(lambda x: '"'+x+'"', columns ) ) )
    query = '''
        SELECT ST_AsMVT(tile, %(layer_name)s, %(extent)s, 'mvt_geom') AS mvt
        FROM (
            SELECT 
                {columns} ,
                ST_AsMVTGeom(
                    -- Geometry from table
                    ST_Transform(t.geom, 3857),
                    -- MVT tile boundary
                    ST_Makebox2d(
                        -- Lower left coordinate
                        ST_Transform(ST_SetSrid(ST_MakePoint(%(xmin)s, %(ymin)s), 4326), 3857),
                        -- Upper right coordinate
                        ST_Transform(ST_SetSrid(ST_MakePoint(%(xmax)s, %(ymax)s), 4326), 3857)
                    ),
                    -- Extent
                    %(extent)s,
                    -- Buffer
                    %(buffer)s,
                    -- Clip geom
                    %(clip)s
                ) AS mvt_geom
            FROM {schema}.{table_name} t
            WHERE
                st_transform(t.geom,4326) --A voir pour optimiser avec les index
                && ST_Makebox2d(
                    ST_Transform(ST_SetSrid(ST_MakePoint(%(xmin)s, %(ymin)s), 4326), %(srid_bbox)s),
                    ST_Transform(ST_SetSrid(ST_MakePoint(%(xmax)s, %(ymax)s), 4326), %(srid_bbox)s)
                )
        ) AS tile
    '''.format(
        columns=cols,
        schema=TILE_SCHEMA,
        table_name=layer_name,
    ) #utiliser plutôt SQL.sql

    # Transform TMS to BBOX
    xmin, ymin, xmax, ymax = _tms2bbox(x, y, z)

    query_parameters = {
        'layer_name': layer_name,
        'xmin': xmin,
        'ymin': ymin,
        'xmax': xmax,
        'ymax': ymax,
        'extent': extent,
        'buffer': buffer,
        'clip': clip,
        'srid_bbox': srid
    }

    with psycopg2.connect(**dbparam) as connection:
        with connection.cursor() as cursor:
            #print(cursor.mogrify(query,query_parameters).decode('utf8'))
            cursor.execute(query, query_parameters)
            res = cursor.fetchone()
            if 'mvt' in res and res['mvt'] is not None:
                tile = bytes(res['mvt'])

    return tile

def _tms2bbox(x, y, z):
        '''
            Convert a tile coordinate into a WGS84 bounding box.
            Ex: (0, 1, 1) => (-180.0, 0.0, 0.0, -85.0511287798066)
            :param x: horizontal tile index on the TMS grid
            :param y: vertical tile index on the TMS grid
            :param z: zoom index on the TMS grid
            :return: WGS84 bounding box as a tuple (minlon, minlat, maxlon, maxlat)
        '''
        xmin, ymin = _tms2ll(x, y, z)
        xmax, ymax = _tms2ll(x + 1, y + 1, z)

        return (xmin, ymin, xmax, ymax)


def _tms2ll(x, y, z):
    '''
        Convert a tile coordinate into a WGS84 coordinate.
        Ex: (0, 1, 1) => (-180.0, 0.0)
        :param x: horizontal tile index on the TMS grid
        :param y: vertical tile index on the TMS grid
        :param z: zoom index on the TMS grid
        :return: WGS84 coordinates as a tuple (lon, lat)
    '''
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lon_deg, lat_deg

def tilejson(layer, dbparam): #TODO prendre le nom de la colonne de geom dans le toml de config
    '''
        Generate a dict tilejson according to 
        https://github.com/mapbox/tilejson-spec
    '''
    query_str = """SELECT st_xMax(st_extent(st_transform(geom,4326))) as xmax, 
	st_xMin(st_extent(st_transform(geom,4326))) as xmin, 
	st_yMax(st_extent(st_transform(geom,4326))) as ymax, 
	st_yMin(st_extent(st_transform(geom,4326))) as ymin
	FROM {} ;"""
    query = sql.SQL(query_str).format(sql.Identifier(layer))
    with psycopg2.connect(**dbparam) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            bx = cursor.fetchone()
            print(bx)
    return {
        'tilejson':"2.2.0",
        "bounds": [bx['xmin'],bx['ymin'],bx['xmax'],bx['ymax'] ],
        "tiles": [
            "http://127.0.0.1:5001/"+layer+"/{z}/{x}/{y}.pbf"
        ],
        "legend": "Generated by Flask-MVT",    
    }

def scandb(dbparam): #find geolayer, colnames et geom cols
    query="""SELECT table_schema,
           table_name, 
           string_agg(DISTINCT column_name, ',') AS "columns", 
           max(DISTINCT gc.f_geometry_column ) AS geom_column,
           max(gc.srid) AS srid
        FROM geometry_columns gc
        JOIN information_schema.columns i ON gc.f_table_schema = i.table_schema AND gc.f_table_name = i.table_name  AND i.column_name != gc.f_geometry_column 
        GROUP BY table_schema, table_name;"""
    with psycopg2.connect(**dbparam) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            out=list()
            for e in cursor.fetchall():
                full_table_name = e['table_schema']+'.'+e['table_name']
                
                out.append({
                    'schema': e['table_schema'],
                    'name': e['table_name'],
                    'columns': e['columns'].split(','),
                    'geom': e['geom_column'],
                    'srid':e['srid']
                })
    return {'layer':out}

