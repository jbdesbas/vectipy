from flask import render_template,request, flash,url_for,redirect,Response, session,abort,Blueprint, current_app,send_file,redirect,send_from_directory, make_response, jsonify

from .mvtserver import _load_tile, tilejson, scandb, get_layer_info

geo = Blueprint('geo', __name__, url_prefix='/',static_folder='static', template_folder='templates')

import toml

@geo.route('/')
def home():
    return render_template('hello.html')

@geo.route('/map/<string:layer>')
def route_map(layer):
    return render_template('map.html',layer_name=layer)


@geo.route('/<string:layer>/<int:z>/<int:x>/<int:y>.pbf', methods=['GET'])
def generic_mvt(layer, z, x, y):
    
    layer_info = get_layer_info(layer,current_app.config['layers'], current_app.config['DB'])    
    
    srid = int(request.args.get('srid', 4326))
    extent = int(request.args.get('extent', 4096))
    buffer = int(request.args.get('buffer', 256))
    clip = bool(request.args.get('clip', True))
    tile = _load_tile(current_app.config['DB'], layer, x, y, z, columns=layer_info['columns'], geom_column=layer_info['geom'], extent=extent, srid=srid)
    response = make_response(tile)
    response.headers.add('Content-Type', 'application/octet-stream')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@geo.route('/scanlayer/', methods=['GET'] ) #A passer en CLI
def scanlayer():
    return Response(toml.dumps( scandb(current_app.config['DB']) ), mimetype='text/plain')

@geo.route('/<string:layer>.json', methods=['GET'])
def tilejson_metadata(layer): 
    print(request.url_root)
    return jsonify( tilejson(layer, current_app.config['DB'], request.url_root) )

@geo.route('test')
def test_route():
    return get_layer_info('test_epci',current_app.config['layers'], current_app.config['DB'])
    return str(current_app.config['layers'])


