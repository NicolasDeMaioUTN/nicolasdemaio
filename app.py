import h3
import os
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify
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


# Decorador para manejar errores de base de datos
def manejar_errores_db(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error en la operación de base de datos: {e}")
            raise e
    return wrapper

# Decorador para validar datos antes de crear o actualizar un registro
def validar_datos(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Validar que los campos obligatorios estén presentes
        if not kwargs.get("h3_index"):
            raise ValueError("El campo 'h3_index' es obligatorio.")
        if not kwargs.get("stop_name"):
            raise ValueError("El campo 'stop_name' es obligatorio.")
        if not kwargs.get("stop_lat") or not kwargs.get("stop_lon"):
            raise ValueError("Los campos 'stop_lat' y 'stop_lon' son obligatorios.")
        if not isinstance(kwargs.get("stop_lat"), (int, float)) or not isinstance(kwargs.get("stop_lon"), (int, float)):
            raise ValueError("Los campos 'stop_lat' y 'stop_lon' deben ser números.")
        return func(self, *args, **kwargs)
    return wrapper

# Decorador para registrar cambios en las propiedades
def registrar_cambios(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if func.__name__ == "actualizar":
            cambios = {k: v for k, v in kwargs.items() if hasattr(self, k) and getattr(self, k) != v}
            print(f"Cambios detectados en Stop {self.stop_id}: {cambios}")
        return func(self, *args, **kwargs)
    return wrapper

class Stop(db.Model):
    __tablename__ = 'stops'  # Asegúrate de que coincida con la tabla en la BD

    stop_id = db.Column(db.Integer, primary_key=True)
    h3_index = db.Column(db.String(15), nullable=False, unique=True)
    stop_name = db.Column(db.String(100), nullable=False)
    stop_desc = db.Column(db.String(140))
    stop_lat = db.Column(db.Float, nullable=False)
    stop_lon = db.Column(db.Float, nullable=False)
    location_type = db.Column(db.SmallInteger, nullable=True)
    geom = db.Column(Geometry('POINT', srid=4326), nullable=False)

    @classmethod
    @manejar_errores_db
    @validar_datos
    def crear(cls, **kwargs):
        print(f"Creando Stop: {kwargs}")
        stop = cls(**kwargs)
        db.session.add(stop)
        db.session.commit()
        return stop

    @classmethod
    @manejar_errores_db
    def leer(cls, stop_id):
        print(f"Leyendo Stop con id: {stop_id}")
        return cls.query.get(stop_id)

    @manejar_errores_db
    @validar_datos
    @registrar_cambios
    def actualizar(self, **kwargs):
        print(f"Actualizando Stop {self.stop_id}: {kwargs}")
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.session.commit()
        return self

    @manejar_errores_db
    def eliminar(self):
        print(f"Eliminando Stop con id: {self.stop_id}")
        db.session.delete(self)
        db.session.commit()
        return True


@app.route('/')
def home():
    return "Bienvenido al servidor para sistema de paradas!"


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
        nueva_parada = Stop.crear(
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


# Ruta para leer una parada por su ID de hexagono
@app.route('/api/paradas/<str:stop_id>', methods=['GET'])
def obtener_parada(stop_id):
    try:
        # Obtener la parada usando el método de clase `leer`
        parada = Stop.leer(stop_id)
        if parada:
            # Convertir la parada a un diccionario
            parada_dict = {
                'stop_id': parada.stop_id,
                'h3_index': parada.h3_index,
                'stop_name': parada.stop_name,
                'stop_desc': parada.stop_desc,
                'stop_lat': parada.stop_lat,
                'stop_lon': parada.stop_lon,
                'location_type': parada.location_type,
            }
            return jsonify(parada_dict)
        else:
            return jsonify({'error': 'Parada no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': 'Error al obtener la parada: ' + str(e)}), 500


# Ruta para actualizar una parada por su ID de hexagono
def actualizar_parada(stop_id):
    try:
        # Obtener la parada usando el método de clase `leer`
        parada = Stop.leer(stop_id)
        if not parada:
            return jsonify({'error': 'Parada no encontrada'}), 404

        # Obtener los datos enviados en el cuerpo de la solicitud
        datos_actualizados = request.get_json()

        # Actualizar la parada usando el método de instancia `actualizar`
        parada.actualizar(**datos_actualizados)

        # Devolver la parada actualizada
        parada_dict = {
            'stop_id': parada.stop_id,
            'h3_index': parada.h3_index,
            'stop_name': parada.stop_name,
            'stop_desc': parada.stop_desc,
            'stop_lat': parada.stop_lat,
            'stop_lon': parada.stop_lon,
            'location_type': parada.location_type,
            'geom': f'POINT({parada.stop_lon} {parada.stop_lat})'  # Formato WKT
        }
        return jsonify(parada_dict)
    except Exception as e:
        return jsonify({'error': 'Error al actualizar la parada: ' + str(e)}), 500


# Ruta para eliminar una parada por su ID
@app.route('/api/paradas/<str:stop_id>', methods=['DELETE'])
def eliminar_parada(stop_id):
    try:
        # Obtener la parada usando el método de clase `leer`
        parada = Stop.leer(stop_id)
        if not parada:
            return jsonify({'error': 'Parada no encontrada'}), 404

        # Eliminar la parada usando el método de instancia `eliminar`
        parada.eliminar()

        # Devolver un mensaje de éxito
        return jsonify({'mensaje': 'Parada eliminada correctamente'})
    except Exception as e:
        return jsonify({'error': 'Error al eliminar la parada: ' + str(e)}), 500


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

