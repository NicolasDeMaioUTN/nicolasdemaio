import h3
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from flask_socketio import SocketIO
from config import DevelopmentConfig, ProductionConfig, configure_app
from flask_cors import CORS
from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)


# Inicialización de la aplicación Flask
app = Flask(__name__)

# Configuración de JWT
app.config["JWT_SECRET_KEY"] = "tu_clave_secreta"  # Cambia esto por una clave segura
jwt = JWTManager(app)

# Permitir CORS para todos los orígenes
CORS(app, resources={r"/*": {"origins": "*"}})

# Seleccionar configuración según FLASK_ENV
config_class = ProductionConfig if os.getenv('FLASK_ENV') == 'production' else DevelopmentConfig
configure_app(app, config_class)  # Asegúrate de que esta función esté configurando la app correctamente

# Inicializar SocketIO y la base de datos
socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

class Stop(db.Model):
    __tablename__ = 'stops'  # O asegúrate de que coincida con la tabla en la BD

    stop_id = db.Column(db.Integer, primary_key=True)
    h3_index = db.Column(db.String(15), nullable=False, unique=True)
    stop_name = db.Column(db.String(100), nullable=False)
    stop_desc = db.Column(db.String(140))
    stop_lat = db.Column(db.Float, nullable=False)
    stop_lon = db.Column(db.Float, nullable=False)
    location_type = db.Column(db.SmallInteger, nullable=True)
    geom = db.Column(Geometry('POINT', srid=4326), nullable=False)


@app.route('/')
def home():
    return "Servidor para sistema de paradas!"

#Ruta para pruebas de conexión
"""
@app.route('/api/test', methods=['GET'])
def test_connection():
    return jsonify({'message': 'Conexión exitosa con el backend!'}), 200/


@app.route('/api/db-test', methods=['GET'])
def test_database_connection():
    try:
        # Intenta realizar una consulta básica
        test_query = Stop.query.first()  # Devuelve el primer registro de la tabla 'stops'
        if test_query:
            return jsonify({'message': 'Conexión exitosa con la base de datos!', 'data': test_query.stop_name}), 200
        else:
            return jsonify({'message': 'Conexión exitosa, pero la tabla está vacía.'}), 200
    except Exception as e:
        return jsonify({'error': 'Error al conectar con la base de datos: ' + str(e)}), 500
"""


# Ruta para guardar paradas
@app.route('/api/paradas', methods=['POST'])
def crear_parada():
    try:
        data = request.json

        # Validación de datos
        if not data:
            return jsonify({'error': 'No se proporcionaron datos.'}), 400

        nombre = data.get('name')
        descripcion = data.get('description')
        tipo = data.get('tipo')
        lat = data.get('latitude')
        lon = data.get('longitude')

        if not all([nombre, descripcion, tipo, lat, lon]):
            return jsonify({'error': 'Faltan datos requeridos.'}), 400

        # Verificar que lat y lon sean números válidos
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            return jsonify({'error': 'Latitud y longitud deben ser números válidos.'}), 400

        # Convertir latitud y longitud a índice H3
        try:
            h3_index = h3.latlng_to_cell(lat, lon, 14)
        except AttributeError as e:
            return jsonify({'error': 'Error al convertir a índice H3: ' + str(e)}), 500
        except Exception as e:
            return jsonify({'error': 'Error inesperado al convertir a índice H3: ' + str(e)}), 500

        # Verificar si el índice H3 ya existe
        if Stop.query.filter_by(h3_index=h3_index).first():
            return jsonify({'error': 'Este hexágono ya está ocupado.'}), 400

        # Crear el objeto geom usando WKTElement
        geom = WKTElement(f'POINT({lon} {lat})', srid=4326)

        # Insertar la nueva parada usando SQLAlchemy
        nueva_parada = Stop(
            stop_name=nombre,
            stop_desc=descripcion,
            stop_lat=lat,
            stop_lon=lon,
            location_type=tipo,
            h3_index=h3_index,
            geom=geom
        )
        db.session.add(nueva_parada)
        db.session.commit()

        # Emitir evento para actualizar en tiempo real
        parada_json = {
            'stop_id': nueva_parada.stop_id,
            'stop_name': nueva_parada.stop_name,
            'stop_desc': nueva_parada.stop_desc,
            'stop_lat': nueva_parada.stop_lat,
            'stop_lon': nueva_parada.stop_lon,
            'h3_index': nueva_parada.h3_index
        }
        socketio.emit('nueva_parada', parada_json)

        return jsonify({'status': 'success', 'stop_id': nueva_parada.stop_id}), 201

    except Exception as e:
        return jsonify({'error': 'Error inesperado: ' + str(e)}), 500


# Ruta para modificar una parada existente
@app.route('/api/paradas/<int:stop_id>', methods=['PUT'])
def modificar_parada(stop_id):
    try:
        data = request.json

        # Validación de datos
        if not data:
            return jsonify({'error': 'No se proporcionaron datos.'}), 400

        # Buscar la parada en la base de datos
        parada = Stop.query.get(stop_id)
        if not parada:
            return jsonify({'error': 'La parada no existe.'}), 404

        # Obtener los datos de la solicitud
        nombre = data.get('name', parada.stop_name)  # Si no se proporciona, se mantiene el valor actual
        descripcion = data.get('description', parada.stop_desc)
        tipo = data.get('tipo', parada.location_type)
        lat = data.get('latitude', parada.stop_lat)
        lon = data.get('longitude', parada.stop_lon)

        # Verificar que lat y lon sean números válidos
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            return jsonify({'error': 'Latitud y longitud deben ser números válidos.'}), 400

        # Convertir latitud y longitud a índice H3
        try:
            h3_index = h3.latlng_to_cell(lat, lon, 14)
        except AttributeError as e:
            return jsonify({'error': 'Error al convertir a índice H3: ' + str(e)}), 500
        except Exception as e:
            return jsonify({'error': 'Error inesperado al convertir a índice H3: ' + str(e)}), 500

        # Verificar si otro registro ya usa el mismo índice H3
        otra_parada = Stop.query.filter_by(h3_index=h3_index).first()
        if otra_parada and otra_parada.stop_id != stop_id:
            return jsonify({'error': 'Otra parada ya ocupa esta ubicación.'}), 400

        # Crear el objeto geom usando WKTElement
        geom = WKTElement(f'POINT({lon} {lat})', srid=4326)

        # Actualizar los datos en la base de datos
        parada.stop_name = nombre
        parada.stop_desc = descripcion
        parada.location_type = tipo
        parada.stop_lat = lat
        parada.stop_lon = lon
        parada.h3_index = h3_index
        parada.geom = geom

        db.session.commit()

        # Emitir evento para actualizar en tiempo real
        parada_json = {
            'stop_id': parada.stop_id,
            'stop_name': parada.stop_name,
            'stop_desc': parada.stop_desc,
            'stop_lat': parada.stop_lat,
            'stop_lon': parada.stop_lon,
            'h3_index': parada.h3_index
        }
        socketio.emit('parada_actualizada', parada_json)

        return jsonify({'status': 'success', 'message': 'Parada actualizada correctamente.'}), 200

    except Exception as e:
        return jsonify({'error': 'Error inesperado: ' + str(e)}), 500

#

# Ruta para obtener todas las paradas
@app.route('/api/paradas', methods=['GET'])
def obtener_paradas():
    try:
        paradas = Stop.query.all()
        paradas_json = [{
            'stop_id': parada.stop_id,
            'stop_name': parada.stop_name,
            'stop_desc': parada.stop_desc,
            'stop_lat': parada.stop_lat,
            'stop_lon': parada.stop_lon,
            'h3_index': parada.h3_index
        } for parada in paradas]
        return jsonify(paradas_json)
    except Exception as e:
        return jsonify({'error': 'Error al obtener las paradas: ' + str(e)}), 500


# Ruta para eliminar una parada existente
@app.route('/api/paradas/<int:stop_id>', methods=['DELETE'])
def eliminar_parada(stop_id):
    try:
        # Buscar la parada en la base de datos
        parada = Stop.query.get(stop_id)
        if not parada:
            return jsonify({'error': 'La parada no existe.'}), 404

        # Eliminar la parada de la base de datos
        db.session.delete(parada)
        db.session.commit()

        # Emitir evento para actualizar en tiempo real
        socketio.emit('parada_eliminada', {'stop_id': stop_id})

        return jsonify({'status': 'success', 'message': 'Parada eliminada correctamente.'}), 200

    except Exception as e:
        return jsonify({'error': 'Error inesperado: ' + str(e)}), 500


#Loggin Geoserver
@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    # Verifica las credenciales (esto es un ejemplo)
    if username != "admin" or password != "password":
        return jsonify({"msg": "Credenciales inválidas"}), 401

    # Crea un token de acceso
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)


# Verificacion token
@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    # Obtiene la identidad del usuario desde el token
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

if __name__ == '__main__':
    socketio.run(app, debug=True)

