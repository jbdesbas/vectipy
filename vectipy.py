from app import create_app

import os

from flask.cli import FlaskGroup, click
from flask import current_app


from dotenv import load_dotenv
load_dotenv() 


cli = FlaskGroup(create_app=create_app)

from app.mvtserver import *



import toml
#@cli.command('scan_db')
#def scan_db():
#    click.echo( toml.dumps(pg2mvt.scandb()) )



@cli.command('cadastre')
@click.argument('insee_com')
def import_cadastre(insee_com):
    area_code = insee_com
    import requests
    import gzip
    base_url = 'https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/'
    for p in ['parcelles','batiments','sections']:
        r = requests.get(join(base_url,'{dpt_code}/{area_code}/cadastre-{area_code}-{p}.json.gz'.format(area_code=area_code, dpt_code=area_code[:2], p = p)))
        print(r.url)
        with open('cadastre-{area_code}-{p}.json.gz'.format(area_code = area_code, p = p),'wb') as f:
            f.write(r.content)
        with gzip.open('cadastre-{area_code}-{p}.json.gz'.format(area_code = area_code, p = p),'rb') as fzip :
            with open('cadastre-{area_code}-{p}.json'.format(area_code = area_code, p = p),'wb') as f_out:
                f_out.write(fzip.read())
        os.remove('cadastre-{area_code}-{p}.json.gz'.format(area_code = area_code, p = p) )

        #Read json and insert utiliser ijson si les fichiers en entré risque d'être lourd

        os.remove('cadastre-{area_code}-{p}.json'.format(area_code = area_code, p = p) )
        

if __name__ == '__main__':
    cli()
