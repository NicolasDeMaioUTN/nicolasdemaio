import h3
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from config import DevelopmentConfig, ProductionConfig, configure_app
from flask_cors import CORS

# Inicialización de la aplicación Flask
app = Flask(__name__)

# Permitir CORS para todos los orígenes
CORS(app, resources={r"/*": {"origins": "*"}})

# Seleccionar configuración según FLASK_ENV
config_class = ProductionConfig if os.getenv('FLASK_ENV') == 'production' else DevelopmentConfig
configure_app(app, config_class)  # Asegúrate de que esta función esté configurando la app correctamente

# Inicializar SocketIO y la base de datos
socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

# Modelo de la tabla 'stops'
class Stop(db.Model):
    __tablename__ = 'stops'
    stop_id = db.Column(db.Integer, primary_key=True)
    stop_name = db.Column(db.String(255))
    stop_desc = db.Column(db.String(255))
    stop_lat = db.Column(db.Float)
    stop_lon = db.Column(db.Float)
    h3_index = db.Column(db.String(15))

@app.route('/')
def home():
    return "Servidor para sistema de paradas!"

@app.route('/api/test', methods=['GET'])
def test_connection():
    return jsonify({'message': 'Conexión exitosa con el backend!'}), 200

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

# Ruta para manejar la creación de paradas
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

        # Insertar la nueva parada usando SQLAlchemy
        nueva_parada = Stop(
            stop_name=nombre,
            stop_desc=descripcion,
            stop_lat=lat,
            stop_lon=lon,
            h3_index=h3_index
        )
        db.session.add(nueva_parada)
        db.session.commit()

        # Emitir evento en tiempo real
        socketio.emit('nueva_parada', {
            'stop_id': nueva_parada.stop_id,
            'stop_name': nueva_parada.stop_name,
            'stop_desc': nueva_parada.stop_desc,
            'stop_lat': nueva_parada.stop_lat,
            'stop_lon': nueva_parada.stop_lon,
            'h3_index': nueva_parada.h3_index
        })

        return jsonify({'status': 'success', 'stop_id': nueva_parada.stop_id}), 201

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
        return jsonify({'error': 'Error al obtener las paradas: ' + str(e)}), 500


if __name__ == '__main__':
    socketio.run(app, debug=True)
