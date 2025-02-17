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
            h3_index = h3.latlng_to_cell(lat, lon, 12)
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
        emitir_actualizacion_paradas()
        socketio.emit('nueva_parada', parada_json)

        return jsonify({'status': 'success', 'stop_id': nueva_parada.stop_id}), 201

    except Exception as e:
        return jsonify({'error': 'Error inesperado: ' + str(e)}), 500


# Ruta para modificar una parada existente
@app.route('/api/paradas/<string:h3_index>', methods=['PUT'])
def modificar_parada(h3_index):
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No se proporcionaron datos.'}), 400

        # Buscar la parada existente
        parada = Stop.query.filter_by(h3_index=h3_index).first()
        if not parada:
            return jsonify({'error': 'Parada no encontrada.'}), 404

        # Validar y actualizar los valores si se proporcionan
        nombre = data.get('name')
        descripcion = data.get('description')
        tipo = data.get('tipo')
        nueva_lat = data.get('latitude')
        nueva_lon = data.get('longitude')

        if nombre:
            parada.stop_name = nombre
        if descripcion:
            parada.stop_desc = descripcion
        if tipo:
            parada.location_type = tipo

        # Validar si se proporcionan nuevas coordenadas
        if nueva_lat is not None and nueva_lon is not None:
            try:
                nueva_lat = float(nueva_lat)
                nueva_lon = float(nueva_lon)
            except ValueError:
                return jsonify({'error': 'Latitud y longitud deben ser números válidos.'}), 400

            # Convertir lat/lon a un índice H3 y verificar si ya existe otra parada ahí
            nueva_h3_index = h3.latlng_to_cell(nueva_lat, nueva_lon, 14)

            if nueva_h3_index != h3_index and Stop.query.filter_by(h3_index=nueva_h3_index).first():
                return jsonify({'error': 'Ya existe una parada en esta ubicación.'}), 400

            # Actualizar las coordenadas
            parada.stop_lat = nueva_lat
            parada.stop_lon = nueva_lon
            parada.h3_index = nueva_h3_index
            parada.geom = WKTElement(f'POINT({nueva_lon} {nueva_lat})', srid=4326)

        db.session.commit()

        # Emitir evento en tiempo real para actualizar en frontend
        parada_json = {
            'stop_id': parada.stop_id,
            'stop_name': parada.stop_name,
            'stop_desc': parada.stop_desc,
            'stop_lat': parada.stop_lat,
            'stop_lon': parada.stop_lon,
            'h3_index': parada.h3_index
        }
        emitir_actualizacion_paradas()
        socketio.emit('parada_modificada', parada_json)

        return jsonify({'status': 'success', 'stop_id': parada.stop_id}), 200

    except Exception as e:
        return jsonify({'error': 'Error inesperado: ' + str(e)}), 500


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
        print(f"Error: {e}")  # Mensaje de depuración
        return jsonify({'error': 'Error al obtener las paradas: ' + str(e)}), 500


# Ruta para eliminar una parada existente
@app.route('/api/paradas/<string:h3_index>', methods=['DELETE'])
def eliminar_parada(h3_index):
    print(f"Intentando eliminar la parada con h3_index: {h3_index}")  # Mensaje de depuración
    try:
        parada = Stop.query.filter_by(h3_index=h3_index).first()
        if not parada:
            print("Parada no encontrada")  # Mensaje de depuración
            return jsonify({'status': 'error', 'error': 'Parada no encontrada'}), 404

        db.session.delete(parada)
        db.session.commit()
        print("Parada eliminada correctamente")  # Mensaje de depuración
        # Emitir evento en tiempo real para eliminar la parada en el front
        emitir_actualizacion_paradas()
        socketio.emit('parada_eliminada', {'h3_index': h3_index})
        return jsonify({'status': 'success', 'message': 'Parada eliminada exitosamente.'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar la parada: {e}")  # Mensaje de depuración
        return jsonify({'status': 'error', 'error': str(e)}), 500


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

def emitir_actualizacion_paradas():
    """Consulta todas las paradas y las emite a todos los clientes conectados"""
    paradas = Stop.query.all()
    paradas_json = [{
        'stop_id': p.stop_id,
        'stop_name': p.stop_name,
        'stop_desc': p.stop_desc,
        'stop_lat': p.stop_lat,
        'stop_lon': p.stop_lon,
        'h3_index': p.h3_index
    } for p in paradas]

    socketio.emit('actualizar_paradas', paradas_json)


if __name__ == '__main__':
    socketio.run(app, debug=True)

