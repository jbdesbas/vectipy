from flask import current_app
import psycopg2
import psycopg2.extras
from psycopg2 import sql

import math

from os.path import join


DEFAULT_SCHEMA = 'public'



def layer_info_from_db(layer_name, dbparam):
    '''
        Get info in DB : columns, geometry column, bbox
        Return a dict :
    '''
    out = dict()
    sql1 = """SELECT st_xMax(st_extent(st_transform(geom,4326))) as xmax, 
    st_xMin(st_extent(st_transform(geom,4326))) as xmin, 
    st_yMax(st_extent(st_transform(geom,4326))) as ymax, 
    st_yMin(st_extent(st_transform(geom,4326))) as ymin
    FROM {layer} te  ;""".format(layer=layer_name)

    sql2 = """   SELECT table_schema,
           table_name, 
           string_agg(DISTINCT column_name, ',') AS "columns", 
       max(DISTINCT gc.f_geometry_column ) AS geom_column,
       max(gc.srid) AS srid,
       max(gc.type) as geom_type
    FROM geometry_columns gc
    JOIN information_schema.columns i ON gc.f_table_schema = i.table_schema AND gc.f_table_name = i.table_name  
    AND i.column_name != gc.f_geometry_column 
    WHERE table_name='{}'
    GROUP BY table_schema, table_name;""".format(layer_name)
    with psycopg2.connect(**dbparam) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql1)
            out['bbox'] = dict(cursor.fetchone())
            cursor.execute(sql2)
            out.update( dict(cursor.fetchone()) )
    out['columns'] = out['columns'].split(',')
    return out

def tilejson(layer, base_url, dbparam, schema=DEFAULT_SCHEMA): #TODO prendre le nom de la colonne de geom dans le toml de config
    '''
        Generate a dict tilejson according to 
        https://github.com/mapbox/tilejson-spec
    '''

    layer_url = join(base_url,"{}.{}".format(schema,layer),'{z}/{x}/{y}.pbf')

    query_str = """SELECT st_xMax(st_extent(st_transform(geom,4326))) as xmax, 
    st_xMin(st_extent(st_transform(geom,4326))) as xmin, 
    st_yMax(st_extent(st_transform(geom,4326))) as ymax, 
    st_yMin(st_extent(st_transform(geom,4326))) as ymin
    FROM {}.{} ;"""
    query = sql.SQL(query_str).format(sql.Identifier(schema), sql.Identifier(layer))
    with psycopg2.connect(**dbparam) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            bx = cursor.fetchone()
    return {
        'tilejson':"2.2.0",
        "bounds": [bx['xmin'],bx['ymin'],bx['xmax'],bx['ymax'] ],
        "tiles": [
            layer_url
        ]
    }

def get_layer_info(layer_name, dbparam, layers_config, schema = DEFAULT_SCHEMA, default_schema = DEFAULT_SCHEMA ):
    entry = [e for e in layers_config['layer'] if e.get('name')==layer_name and e.get('schema', default_schema ) == schema]
    return entry[0]

def scandb(dbparam): #find geolayer, colnames et geom cols #a stocker dans current_app.config
    query="""SELECT table_schema,
           table_name, 
           string_agg(DISTINCT column_name, ',') AS "columns", 
           max(DISTINCT gc.f_geometry_column ) AS geom_column,
           max(gc.srid) AS srid,
           max(gc.type) as geom_type
        FROM geometry_columns gc
        JOIN information_schema.columns i ON gc.f_table_schema = i.table_schema AND gc.f_table_name = i.table_name  AND i.column_name != gc.f_geometry_column
        WHERE gc.f_table_schema='public'
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
                    'table_name':e['table_name'],
                    'columns': e['columns'].split(','),
                    'geom': e['geom_column'],
                    'srid':e['srid'],
                    'geom_type':e['geom_type']
                })
    return {'layer':out}

def load_tile(table_name, x, y, z, columns, dbparam, schema = DEFAULT_SCHEMA, geom_column='geom', layer_name = None, extent=4096, buffer=256, clip=True, limit=2000):
    tile = None
    layer_name = layer_name or table_name
    #TODO : r??cup??rer la limite dans les param??tres
    # Generic query to select data from postgres
    # Each table has to contain columns: 'id', 'value', 'extrude', 'geom'
    # TODO : ne pas r??cup??rer la geom dans les champs attribut
    # TODO : prevoir un dict pour pr??ciser les champs ?? retourner (sinon, tous les champs)
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
                    ST_Transform(t.{geom}, 3857),
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
                st_transform(t.{geom},3857) --A voir pour optimiser avec les index
                && ST_Makebox2d(
                    ST_Transform(ST_SetSrid(ST_MakePoint(%(xmin)s, %(ymin)s), 4326), 3857),
                    ST_Transform(ST_SetSrid(ST_MakePoint(%(xmax)s, %(ymax)s), 4326), 3857)
                )
            LIMIT {limit}
        ) AS tile
    '''.format(
        columns=cols,
        geom=geom_column,
        schema=schema,
        table_name=table_name,
        limit=limit,
    ) #utiliser plut??t SQL.sql

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
        'clip': clip
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


def geojson(layer_name, columns, dbparam, schema = DEFAULT_SCHEMA, geom_column='geom'):
    cols = ', '.join( list( map(lambda x: '"'+x+'"', columns ) ) )
    query_str = """SELECT row_to_json(fc)
         FROM ( SELECT 'FeatureCollection' As type, array_to_json(array_agg(f)) As features
         FROM (SELECT 'Feature' As type
            , ST_AsGeoJSON(lg.{geom})::json As geometry
            , row_to_json((SELECT l FROM (SELECT {fields} ) As l
              )) As properties
           FROM {schema}.{table} lg   ) As f )  As fc;""" #https://www.postgresonline.com/journal/archives/267-Creating-GeoJSON-Feature-Collections-with-JSON-and-PostGIS-functions.html
    query = sql.SQL(query_str).format(
        fields=sql.SQL(',').join( [sql.Identifier(c) for c in columns ]),
        geom=sql.Identifier(geom_column),
        schema=sql.Identifier(schema), 
        table=sql.Identifier(layer_name))
    with psycopg2.connect(**dbparam) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            res = cursor.fetchone()
    return res['row_to_json']

def global_extent(bbox_lst):
    """return global extent from multiples bbox"""
    return {'xmin':min( [b['xmin'] for b in bbox_lst] ),
            'xmax':max( [b['xmax'] for b in bbox_lst] ), 
            'ymin':min( [b['ymin'] for b in bbox_lst] ), 
            'ymax':max( [b['ymax'] for b in bbox_lst] ) }

class Layer(object):
    "A database table"
    def __init__(self, table_name, dbparam, layer_name = None, columns = None, layers_config = None, minzoom = None, maxzoom = None, geometry_column = 'geom', **kwargs):
        self.table_name = table_name
        self.dbparam = dbparam
        self.layer_name = layer_name or table_name
        self.columns = columns or self.info_db()['columns']
        self.layers_config = layers_config #a suppr
        self.bbox = self.info_db()['bbox']
        self.minzoom = minzoom
        self.maxzoom = maxzoom
        self.geometry_column = geometry_column
    
    def info(self):
        return {'name':self.table_name, 'schema':'public', 'columns':self.columns}

    def info_db(self):
        return layer_info_from_db(layer_name = self.table_name, dbparam = self.dbparam )

    def tile(self, x, y, z):
        if  z < ( self.minzoom or 0) or z > (self.maxzoom or 99) :
            return None
        return load_tile(layer_name = self.layer_name, table_name = self.table_name, columns = self.info()['columns'], x = x, y = y, z = z, geom_column = self.geometry_column, dbparam = self.dbparam)

    def geojson(self):
        return geojson(layer_name = self.layer_name, columns = self.info()['columns'], geom_column = self.geometry_column, dbparam = self.dbparam)

    def tilejson(self, base_url):
        bx = self.info_db()['bbox']
        return {
        'tilejson':"2.2.0",
        "bounds": [bx['xmin'],bx['ymin'],bx['xmax'],bx['ymax'] ],
        "tiles": [
            join(base_url,self.layer_name,'{z}/{x}/{y}.pbf')
        ],
        "legend": "Generated by Vectipy",    
        }

class LayerCollection(Layer):
    "Some layers on the same tiles"
    def __init__(self, collection_name, layers: list):
        self.collection_name = collection_name
        self.table_name = collection_name #TODO delete
        self.layers = layers
        self.bbox = global_extent( [l.bbox for l in self.layers] )

    def tile(self, x, y, z):
        o = bytes()
        for l in self.layers:
            o+=( l.tile(x, y, z) or b'' )
        return o

    def tilejson(self, base_url):
        return {
        'tilejson':"2.2.0",
        "bounds": [self.bbox['xmin'],self.bbox['ymin'],self.bbox['xmax'],self.bbox['ymax'] ],
        "tiles": [
            join(base_url,self.collection_name,'{z}/{x}/{y}.pbf')
        ]
        }


