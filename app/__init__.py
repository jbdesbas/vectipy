from flask import Flask, render_template

import os
import toml, json
import psycopg2.extras

from .mvtserver import scandb, Layer, LayerCollection

def page_not_found(e):
  return render_template('404.html'), 404

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY','testingSssecretKey')
    default_config={
        'TILES':{
            'MAX_FEATURES': 2000,
            'SRID' : 4326,
            'EXTENT' : 4096,
            'BUFFER' : 256
        },
        'DEFAULT_SCHEMA':'public'
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
    for l in  scandb(dbparam=app.config['DB'])['layer']:
        app.config['data'][l['name']] = Layer(layer_name=l['name'], table_name=l['name'], dbparam=app.config['DB'], columns=l['columns']) 
    try:
        with open('app/motd.txt','r') as f:
            print(f.read())
    except FileNotFoundError:
        pass
    try:
        with open('layers.toml','r') as f:
            tom = toml.load(f)
            #print(tom)
            for c in tom['collection']:
                layers_list=list()
                for l in c['layer']:
                    layers_list.append( Layer(layer_name=l['name'], table_name = l['name'], dbparam=app.config['DB'], columns=l['columns']) )
                app.config['data'][ c['name'] ] = LayerCollection(collection_name=c['name'], layers = layers_list)
            for l in tom['layers']:
                app.config['data'][ l['name'] ] = Layer(layer_name=l['name'], table_name=l['name'], dbparam=app.config['DB'], columns=l['columns']) 
    except FileNotFoundError:
        print("No layers.toml file found")
    print(json.dumps(app.config['data'], default=str))
    print('{} geo-layer(s) found'.format(len(app.config['data'].get('layer',list() ) ) ) )
    print('{} collection(s) found'.format(len(app.config['data'].get('feed',list() ) ) ) )
    return app
