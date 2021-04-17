from flask import Flask, render_template

import os
import toml
import psycopg2.extras

from .mvtserver import Pg2mvt

def page_not_found(e):
  return render_template('404.html'), 404

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY','testingSssecretKey')
    #app.config.from_pyfile('config.py')
    app.config['DB']={
        'host' : os.getenv('PG_HOST'),
        'port' : os.getenv('PG_PORT'),
        'database' : os.getenv('PG_DATABASE'),
        'user' : os.getenv('PG_USER'),
        'password' : os.getenv('PG_PASSWORD'),
        'cursor_factory': psycopg2.extras.RealDictCursor
    }
    app.config['DEFAULT_SCHEMA'] = 'public'
    app.pg2mvt = Pg2mvt(app.config['DB'] )
    from app.routes import geo
    app.register_blueprint(geo)
    app.register_error_handler(404, page_not_found)
    app.config['layers'] = app.pg2mvt.scandb()
    print('{} geo-layers found'.format(len(app.config['layers'].get('layer',list()))) )
    return app
