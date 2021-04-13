from flask import render_template,request, flash,url_for,redirect,Response, session,abort,Blueprint, current_app,send_file,redirect,send_from_directory, make_response, jsonify

geo = Blueprint('geo', __name__, url_prefix='/',static_folder='static', template_folder='templates')

import toml



@geo.route('/')
def home():
    return render_template('hello.html')

@geo.route('/map/<string:layer>')
def route_map(layer):
    schema = current_app.config['DEFAULT_SCHEMA']
    if '.' in layer :
        schema = layer.split('.')[0]
        layer = layer.split('.')[1]
    return render_template('map.html',layer_name="{}.{}".format(schema,layer)) 


@geo.route('/<string:layer>/<int:z>/<int:x>/<int:y>.pbf', methods=['GET'])
def generic_mvt(layer, z, x, y):
    schema = current_app.config['DEFAULT_SCHEMA']
    if '.' in layer :
        schema = layer.split('.')[0]
        layer = layer.split('.')[1]
    
    layer_info = current_app.pg2mvt.get_layer_info(layer,current_app.config['layers'], schema = schema )    
    
    srid = int(request.args.get('srid', 4326))
    extent = int(request.args.get('extent', 4096))
    buffer = int(request.args.get('buffer', 256))
    clip = bool(request.args.get('clip', True))
    tile = current_app.pg2mvt.load_tile(layer, x, y, z, schema = schema, columns=layer_info['columns'], geom_column=layer_info['geom'], extent=extent, srid=srid)
    response = make_response(tile)
    response.headers.add('Content-Type', 'application/octet-stream')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@geo.route('/scanlayer/', methods=['GET'] ) #A passer en CLI
def scanlayer():
    return Response(toml.dumps( scandb() ), mimetype='text/plain')

@geo.route('/<string:layer>.json', methods=['GET'])
def tilejson_metadata(layer): 
    schema = current_app.config['DEFAULT_SCHEMA']
    if '.' in layer :
        schema = layer.split('.')[0]
        layer = layer.split('.')[1]
    print(request.url_root)
    return jsonify( current_app.pg2mvt.tilejson(layer, request.url_root, schema=schema) )

@geo.route('/<string:layer>.geojson', methods=['GET'])
def test_route(layer):
    schema = current_app.config['DEFAULT_SCHEMA']
    if '.' in layer :
        schema = layer.split('.')[0]
        layer = layer.split('.')[1]
    layer_info = current_app.pg2mvt.get_layer_info(layer,current_app.config['layers'], schema = schema )    
    return jsonify( current_app.pg2mvt.geojson(layer, columns=layer_info['columns'], schema=schema) )



