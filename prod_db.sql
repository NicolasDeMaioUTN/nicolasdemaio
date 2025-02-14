-- DROP DATABASE IF EXISTS paradas_prod_db;
CREATE DATABASE paradas_prod_db
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Spanish_Argentina.1252'
    LC_CTYPE = 'Spanish_Argentina.1252'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

CREATE USER prod_user WITH PASSWORD 'paradas_prod_2025';
GRANT ALL PRIVILEGES ON DATABASE paradas_prod_db TO dev_user;

-- Crear la tabla de paradas con referencia H3
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE stops (
    stop_id SERIAL PRIMARY KEY,
    h3_index VARCHAR(15) NOT NULL UNIQUE, -- H3 único para resolución 15
    stop_name VARCHAR(100) NOT NULL,
    stop_desc VARCHAR(140),
    stop_lat DOUBLE PRECISION NOT NULL,
    stop_lon DOUBLE PRECISION NOT NULL,
    location_type SMALLINT CHECK (location_type IN (0, 1, 2)), -- Valores válidos según GTFS
    geom GEOMETRY(Point, 4326) NOT NULL,
    CONSTRAINT unique_h3_index UNIQUE (h3_index) -- Asegura unicidad basada en H3
);

-- Agregar un índice espacial para acelerar las búsquedas geográficas
CREATE INDEX stops_geom_idx ON stops USING GIST (geom);

-- Crear la tabla de agencias / empresas
CREATE TABLE agency (
    agency_id SERIAL PRIMARY KEY,
    agency_name VARCHAR(100) NOT NULL,
    agency_url VARCHAR(255),
    agency_timezone VARCHAR(50) NOT NULL,
    agency_lang VARCHAR(2) DEFAULT 'en',
    agency_phone VARCHAR(20)
);

-- Crear la tabla de rutas (routes)
CREATE TABLE routes (
    route_id SERIAL PRIMARY KEY,
    agency_id INT NOT NULL,
    route_name VARCHAR(100) NOT NULL,
    route_type SMALLINT NOT NULL CHECK (route_type IN (0, 1, 2, 3)),
    route_url VARCHAR(255),
    route_color CHAR(6),
    route_text_color CHAR(6),
    FOREIGN KEY (agency_id) REFERENCES agency(agency_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Crear la tabla para asociar paradas con rutas
CREATE TABLE stops_routes (
    stop_id INT NOT NULL,
    route_id INT NOT NULL,
    PRIMARY KEY (stop_id, route_id),
    CONSTRAINT fk_stop FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_route FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Crear la tabla de viajes (trips)
CREATE TABLE trips (
    trip_id SERIAL PRIMARY KEY,
    route_id INT NOT NULL,
    trip_name VARCHAR(100),
	service_id VARCHAR(50) NOT NULL,
    CONSTRAINT fk_route_trip FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Crear la tabla de horarios de paradas
CREATE TABLE stop_times (
    trip_id INT NOT NULL,
    arrival_time TIMESTAMP NOT NULL,
    departure_time TIMESTAMP NOT NULL,
    stop_id INT NOT NULL,
    stop_sequence INT NOT NULL,
    shape_dist_traveled FLOAT,
    PRIMARY KEY (trip_id, stop_id, stop_sequence),
    CONSTRAINT fk_trip FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_stop_time FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE calendar (
    service_id VARCHAR(50) PRIMARY KEY, -- Identificador único del servicio
    monday SMALLINT NOT NULL CHECK (monday IN (0, 1)), -- 0 = No operativo, 1 = Operativo
    tuesday SMALLINT NOT NULL CHECK (tuesday IN (0, 1)),
    wednesday SMALLINT NOT NULL CHECK (wednesday IN (0, 1)),
    thursday SMALLINT NOT NULL CHECK (thursday IN (0, 1)),
    friday SMALLINT NOT NULL CHECK (friday IN (0, 1)),
    saturday SMALLINT NOT NULL CHECK (saturday IN (0, 1)),
    sunday SMALLINT NOT NULL CHECK (sunday IN (0, 1)),
    start_date DATE NOT NULL CHECK (start_date <= end_date), -- Fecha de inicio del servicio
    end_date DATE NOT NULL, -- Fecha de fin del servicio

    CONSTRAINT chk_days_valid CHECK (
        monday + tuesday + wednesday + thursday + friday + saturday + sunday >= 1
    ) -- Asegura que al menos un día esté activo
);
CREATE INDEX idx_calendar_date_range ON calendar (start_date, end_date);
ALTER TABLE trips
ADD CONSTRAINT fk_trips_calendar
FOREIGN KEY (service_id)
REFERENCES calendar (service_id)
ON DELETE CASCADE;

-- Crear tabla de seguimiento de actividades de Asignacion de Paradas
CREATE TABLE actividades_paradas (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(255) NOT NULL,
    accion VARCHAR(255) NOT NULL, -- 'crear', 'modificar', 'asignar'
    stop_id INT REFERENCES stops (stop_id) ON DELETE CASCADE,
    route_id INT REFERENCES routes(route_id),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Validar h3 
CREATE EXTENSION IF NOT EXISTS h3;
CREATE OR REPLACE FUNCTION validate_h3_index()
RETURNS TRIGGER AS $$
DECLARE
    calculated_h3_index VARCHAR(15);
BEGIN
    -- Calcular el índice H3 basado en las coordenadas
    calculated_h3_index := h3_geo_to_h3(NEW.stop_lat, NEW.stop_lon, 14); -- usamos hexagonos 14 con area maxima de 7 m2 y min de 3m2
    -- Comparar el índice calculado con el proporcionado
    IF NEW.h3_index <> calculated_h3_index THEN
        RAISE EXCEPTION 'El índice H3 % no coincide con las coordenadas proporcionadas (calculado: %)', 
                        NEW.h3_index, calculated_h3_index;
    END IF;
    -- Si coinciden, permitir la operación
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear Trigger para validar antes de cada insercion
CREATE TRIGGER trigger_validate_h3_index
BEFORE INSERT OR UPDATE ON stops
FOR EACH ROW
EXECUTE FUNCTION validate_h3_index();


