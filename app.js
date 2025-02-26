// Formularios
const popupForm = document.getElementById('popup-form');
const stopForm = document.getElementById('stop-form');
const ModifyStopForm = document.getElementById('stop-form');
const cancelButton = document.getElementById('cancel');
var map; 
//Barra Lateral
const sidebar = document.getElementById('sidebar');
const toggleSidebar = document.getElementById('toggleSidebar');
let selectedLatLng = null;       // Puntero de Latitud y Longitud

//#region Carga de Mapa e Inicio
const mapElement = document.getElementById('map');
if (mapElement) {
    // Inicializar el mapa
    map = L.map('map', {
        center: [-34.622064, -58.43552], // Coordenadas iniciales (AMBA)
        zoom: 10,
        minZoom: 10, // Establecer el zoom mínimo permitido
        maxBounds: [[-35.2, -59.5], [-34.3, -57.9]], // Límites del área
        maxBoundsViscosity: 1.0, // Asegura que el mapa no pueda ir fuera de los límites
    });

    cargarParadasGuardadas();    

    // Agregar capa base
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© Registro de Paradas - DNDT#MTR'
    }).addTo(map);

    // Deshabilitar zoom out fuera de la zona permitida
    map.on('zoomend', function () {
        if (!map.getBounds().contains(map.getCenter())) {
            map.setZoom(map.getZoom() - 1); // Si el mapa está fuera de los límites, deshacer el zoom out
        }
    });

    // Deshabilito clicks por fuera del area
    map.on('mousemove', function (e) {
        if (!map.getBounds().contains(e.latlng)) {
            map.dragging.disable();
        } else {
            map.dragging.enable();
        }
    });
    
    // Manejar clic derecho en el mapa
    map.on('contextmenu', function (e) {
        if (!map.getBounds().contains(e.latlng)) {
            alert("El punto seleccionado está fuera del AMBA. Por favor, selecciona un punto dentro del área permitida.");
        } else {
            selectedLatLng = e.latlng;
            const popupForm = document.getElementById('popup-form');
            document.getElementById('stop_lat').value = e.latlng.lat.toFixed(10);
            document.getElementById('stop_lon').value = e.latlng.lng.toFixed(10);
            popupForm.classList.remove('hidden');
        }
    });  
} else {
    console.error("El contenedor del mapa no se encontró en el DOM.");
}
//#endregion


//#region Barra Lateral
// Plegar barra lateral
toggleSidebar.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});

// mostrar barra lateral    
function toggleForm(formId) {
    const formContainer = document.getElementById(formId);
    formContainer.style.display = formContainer.style.display === 'none' ? 'block' : 'none';
}
//#endregion


//#region Formularios
// Funcion para mostrar formularios
function togglePopupForm(show, latlng) {
    if (show) {
        popupForm.classList.remove('hidden');
        document.getElementById('stop_lat').value = latlng.lat.toFixed(10);
        document.getElementById('stop_lon').value = latlng.lng.toFixed(10);
    } else {
        popupForm.classList.add('hidden');
        ModifyStopForm.reset();
    }
}

// Cerrar formulario emergente
document.getElementById('cancel').addEventListener('click', () => {
    document.getElementById('popup-form').classList.add('hidden');
});

// Manejar cancelación del formulario
cancelButton.addEventListener('click', function () {
    popupForm.classList.add('hidden');
    ModifyStopForm.reset();
});
//#endregion


//#region Guardado de Paradas
// Evento para manejar el envío del formulario
stopForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    // Obtener los valores del formulario
    const stopName = document.getElementById('stop_name').value;
    const stopDesc = document.getElementById('stop_desc').value;
    const stopTipo = document.getElementById('locationType').value;
    const stopLat = parseFloat(document.getElementById('stop_lat').value);
    const stopLon = parseFloat(document.getElementById('stop_lon').value);

    // Crear el objeto con los datos del Stop
    const stopData = {
        //h3_index: h3Index, // Incluir el campo h3_index
        stop_name: stopName,
        stop_desc: stopDesc,
        location_type: stopTipo, // Cambiar "tipo" a "location_type"
        stop_lat: stopLat,       // Cambiar "latitude" a "stop_lat"
        stop_lon: stopLon,       // Cambiar "longitude" a "stop_lon"
        //geom: `POINT(${stopLon} ${stopLat})` // Crear el campo geom en formato WKT
    };

    try {
        const response = await fetch('http://127.0.0.1:5000/api/paradas', {

            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(stopData), // Enviar los datos en formato JSON
        });
    
        if (response.ok) {
            const result = await response.json();
            console.log('Respuesta del servidor:', result);
            alert('Parada guardada exitosamente!');
            stopForm.reset();
            stopForm.classList.add('hidden');

        } else {
            const errorData = await response.json(); // Leer el error en formato JSON
            console.error('Error en la respuesta:', errorData);
            alert(`Error al guardar la parada: ${errorData.message || 'Error desconocido'}`);
        }
    } catch (error) {
        console.error('Error en la solicitud:', error);
        alert('Error de conexión con el servidor.');
    }
});

// Evento para manejar la cancelación del formulario
cancelButton.addEventListener('click', () => {
    popupForm.classList.add('hidden');
    stopForm.reset(); // Opcional: limpiar el formulario
});

//#endregion


//#region Capa de Paradas
const socket = io('http://localhost:5000'); // conecta al Flask


/* Prueba de conexión
fetch('http://127.0.0.1:5000/api/test')
  .then(response => response.json())
  .then(data => {
    console.log('Respuesta del backend:', data);
    alert(data.message); // Muestra la respuesta en una alerta
  })
  .catch(error => {
    console.error('Error al conectar con el backend:', error);
});*/


// Obtener todas las paradas iniciales
fetch('http://localhost:5000/api/paradas')
    .then(response => response.json())
    .then(data => {
        data.forEach(parada => agregarParada(parada));
    })
    .catch(error => console.error('Error al obtener paradas:', error));

// Escuchar actualizaciones en tiempo real
socket.on('nueva_parada', parada => {
    agregarParada(parada);
});
//#endregion


// Cargar todas las paradas guardadas al iniciar la página
async function cargarParadasGuardadas() {
    try {
        const response = await fetch('http://localhost:5000/api/paradas');
        if (!response.ok) {
            throw new Error('Error al obtener las paradas guardadas');
        }

        const paradas = await response.json();
        paradas.forEach(parada => agregarParada(parada));        
    } catch (error) {
        console.error('Error en la solicitud:', error);
    }
}


// Función para agregar un marcador con evento de detalles
function agregarParada(parada) {

    if (typeof parada.stop_lat !== "number" || typeof parada.stop_lon !== "number") {
        console.error("Error: parada sin coordenadas válidas", parada);
        return;
    }

    const geojsonFeature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [parada.stop_lon, parada.stop_lat]  // GeoJSON usa [longitud, latitud]
        },
        "properties": {
            "name": parada.stop_name,
            "description": parada.stop_desc
        }
    };

    const marker = L.geoJSON(geojsonFeature, {
        pointToLayer: function (feature, latlng) {
            return L.circleMarker(latlng, {
                radius: 6,
                color: "#0078ff",
                fillColor: "#0078ff",
                fillOpacity: 0.8
            });
        },
        onEachFeature: function (feature, layer) {
            layer.bindPopup(`
                <b>Nombre:</b> ${feature.properties.name} <br>
                <b>Detalles:</b> ${feature.properties.description}
            `);
        }
    }).addTo(map);

    return marker;
}

//#region Loggin en  Geoserver
// Ejemplo de inicio de sesión
async function login(username, password) {
    const response = await fetch('http://tuservidor/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
    });
    const data = await response.json();
    if (response.ok) {
        localStorage.setItem('token', data.access_token);  // Almacena el token
    } else {
        console.error('Error:', data.msg);
    }
}

async function fetchProtectedData() {
    const token = localStorage.getItem('token');
    const response = await fetch('http://tuservidor/protected', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    });
    const data = await response.json();
    if (response.ok) {
        console.log('Datos protegidos:', data);
    } else {
        console.error('Error:', data.msg);
    }
}
//#endregion