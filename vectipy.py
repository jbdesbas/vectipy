from app import create_app

import os

from flask.cli import FlaskGroup, click
from flask import current_app


from dotenv import load_dotenv
load_dotenv() 


cli = FlaskGroup(create_app=create_app)

from app.mvtserver import *
from app.exemples import import_cadastre


import toml
#@cli.command('scan_db')
#def scan_db():
#    click.echo( toml.dumps(pg2mvt.scandb()) )



@cli.command('cadastre')
@click.argument('insee_com')
def cli_import_cadastre(insee_com):
    import_cadastre(insee_com)
        

if __name__ == '__main__':
    cli()
