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
    click.echo( toml.dumps(scandb(current_app.config['DB'])) )


if __name__ == '__main__':
    cli()
