from app import create_app
import os
from flask.cli import FlaskGroup, click
from flask import current_app


from dotenv import load_dotenv
load_dotenv() 

app=create_app()

cli = FlaskGroup(create_app=create_app)

from app.mvtserver import *



import toml
#@cli.command('scan_db')
#def scan_db():
#    click.echo( toml.dumps(pg2mvt.scandb()) )


if __name__ == '__main__':
    cli()
