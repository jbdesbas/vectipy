from flask import Flask, render_template

import os
import toml
import psycopg2.extras

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
    from app.routes import geo
    app.register_blueprint(geo)
    app.register_error_handler(404, page_not_found)
    with open('layers.toml', 'r') as f:
        app.config['layers']=toml.load(f)
    return app
