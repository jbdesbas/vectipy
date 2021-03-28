from app import create_app
import os
from flask.cli import FlaskGroup, click
from flask import current_app

app=create_app()

cli = FlaskGroup(create_app=create_app)

from app.mvtserver import scandb
import toml
@cli.command('scan_db')
def scan_db():
    """Auto-generate layers definition (layers.toml) from database"""
    click.echo( toml.dumps(scandb(current_app.config['DB'])) )


@cli.command('check')
def check():
    """Everything is fine ?"""
    click.echo('DB connection?         ✅❌')
    click.echo('Postgis version?       ✅❌')
    click.echo('Test st_asMvt Func     ✅❌')
    
    click.echo('Layer Index ?          ✅⚠️')
    click.echo('Layer SRID ?           ✅⚠️')
    click.echo('Layer Geometry type ?  ✅⚠️')

    click.echo('layers.toml            ✅❌')
    pass

if __name__ == '__main__':
    cli()
