from flask import Flask, render_template

import os
import toml, json
import psycopg2.extras

from .mvtserver import scandb, Layer, LayerCollection

def page_not_found(e):
  return render_template('404.html'), 404

def create_app():
    app = Flask(__name__)
    try:
        with open('app/motd.txt','r') as f:
            print(f.read())
    except FileNotFoundError:
        pass
    app.secret_key = os.environ.get('SECRET_KEY','testingSssecretKey')
    default_config={
        'TILES':{
            'MAX_FEATURES': 2000,
            'SRID' : 4326,
            'EXTENT' : 4096,
            'BUFFER' : 256
        },
        'SERVER':{
            'DEFAULT_SCHEMA':'public',
            'AUTO_PUBLISH_LAYERS':False
        }

    }
    app.config.update(default_config)
    with open('config.toml', 'r') as f:
         app.config.update(toml.load(f) )
    app.config['DB']={
        'host' : os.getenv('PG_HOST'),
        'port' : os.getenv('PG_PORT'),
        'database' : os.getenv('PG_DATABASE'),
        'user' : os.getenv('PG_USER'),
        'password' : os.getenv('PG_PASSWORD'),
        'cursor_factory': psycopg2.extras.RealDictCursor
    }
    app.config['DEFAULT_SCHEMA'] = 'public'

    from app.routes import geo
    app.register_blueprint(geo)
    app.register_error_handler(404, page_not_found)

    app.config['data'] = dict()
    if app.config['SERVER']['AUTO_PUBLISH_LAYERS']:
        for l in  scandb(dbparam=app.config['DB'])['layer']:
            app.config['data'][l['name']] = Layer(layer_name=l['name'], table_name=l['name'], dbparam=app.config['DB'], geometry_column = l['geom'], columns=l['columns']) #TODO parameter pour scanner ou non la db
    else :
        print('Table with geom are NOT auto-published')
   
    try:
        #### TRAITEMENT DU FICHIER DE CONFIG layers.toml ####
        with open('layers.toml','r') as f:
            tom = toml.load(f)
            for c in tom['collection']: #Multi-layers tiles
                layers_list=list()
                for l in c['layer']:
                    layers_list.append( Layer(layer_name=l['name'], table_name = l['table_name'], dbparam=app.config['DB'], columns=l.get('columns',None), minzoom=l.get('minzoom',None), maxzoom=l.get('maxzoom',None)  , geometry_column = l.get('geometry_column','geom')    ) )
                app.config['data'][ c['name'] ] = LayerCollection(collection_name=c['name'], layers = layers_list)
            for l in tom['layers']: #Simple layer tiles
                app.config['data'][ l['name'] ] = Layer(layer_name=l['name'], table_name=l['table_name'], dbparam=app.config['DB'], columns=l.get('columns',None), minzoom=l.get('minzoom',None), maxzoom=l.get('maxzoom',None) , geometry_column = l.get('geometry_column','geom') ) 
    except FileNotFoundError:
        print("No layers.toml file found")
    print('🌐 \033[1;32;40m {} layers or collections \033[0m'.format(len( app.config['data'] )) )
    for k,v in app.config['data'].items():
        if isinstance(v,LayerCollection): 
            print('- Collection: {}'.format(v.collection_name) )
            for l in v.layers:
                print('  - Layer: {} ("{}")'.format(l.layer_name, l.table_name) )
        else :
            print('- Layer: {} ("{}")'.format(v.layer_name, v.table_name) )
    return app
