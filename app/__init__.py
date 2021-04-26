from flask import Flask, render_template

import os
import toml
import psycopg2.extras

from .mvtserver import scandb, Layer

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
    #app.pg2mvt = Pg2mvt(dbparam = app.config['DB'])
    from app.routes import geo
    app.register_blueprint(geo)
    app.register_error_handler(404, page_not_found)
    #app.config['layers'] = scandb(dbparam=app.config['DB'])
    app.config['layers'] = dict()
    for l in  scandb(dbparam=app.config['DB'])['layer']:
        app.config['layers'][l['name']] = Layer(layer_name=l['name'], table_name=l['name'], dbparam=app.config['DB'], columns=l['columns']) 
    try:
        with open('app/motd.txt','r') as f:
            print(f.read())
    except FileNotFoundError:
        pass
    try:
        with open('layers.toml','r') as f:
            app.config['layers'].update( toml.load(f) )
    except FileNotFoundError:
        print("No layers.toml file found")
    print('{} geo-layer(s) found'.format(len(app.config['layers'].get('layer',list() ) ) ) )
    print('{} collection(s) found'.format(len(app.config['layers'].get('feed',list() ) ) ) )
    return app
