//#region Map
    const mapElement = document.getElementById('map');
    if (mapElement) {
        // Inicializar el mapa
        const map = L.map('map', {
            center: [-34.622064, -58.43552], // Coordenadas iniciales (AMBA)
            zoom: 10,
            minZoom: 10, // Establecer el zoom mínimo permitido
            maxZoom: 18, // Opcional: establecer el zoom máximo
            maxBounds: [[-35.2, -59.5], [-34.3, -57.9]], // Límites del área
            maxBoundsViscosity: 1.0, // Asegura que el mapa no pueda ir fuera de los límites
        });

        // Agregar capa base
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
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
            console.log('LatLng del clic:', e.latlng);
            console.log('Límites del mapa:', map.getBounds());

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

// Referencias a elementos del DOM
const popupForm = document.getElementById('popup-form');
const stopForm = document.getElementById('stop-form');
const ModifyStopForm = document.getElementById('stop-form');
const cancelButton = document.getElementById('cancel');

let selectedLatLng = null; // Puntero de Latitud y Longitud

//#region Barra Lateral
    // Barra lateral
    const sidebar = document.getElementById('sidebar');
    const toggleSidebar = document.getElementById('toggleSidebar');
    toggleSidebar.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
    });

        
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

    const stopName = document.getElementById('stop_name').value;
    const stopDesc = document.getElementById('stop_desc').value;
    const stopTipo = document.getElementById('locationType').value;
    const stopLat = parseFloat(document.getElementById('stop_lat').value);
    const stopLon = parseFloat(document.getElementById('stop_lon').value);

    const stopData = {
        name: stopName,
        description: stopDesc,
        tipo: stopTipo,
        latitude: stopLat,
        longitude: stopLon,
    };

    try {
        const response = await fetch('http://127.0.0.1:5000/api/paradas', {

            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(stopData),
        });
    
        if (response.ok) {
            const result = await response.json();
            console.log('Respuesta del servidor:', result);
            alert('Parada guardada exitosamente');
        } else {
            const errorData = await response.text();
            console.error('Error en la respuesta:', errorData);
            alert('Error al guardar la parada');
        }
    } catch (error) {
        console.error('Error en la solicitud:', error);
    }
    
});


// Evento para manejar la cancelación del formulario
cancelButton.addEventListener('click', () => {
    popupForm.classList.add('hidden');
    stopForm.reset(); // Opcional: limpiar el formulario
});

//#endregion

//#region Capa de Paradas
const socket = io();

// Función para agregar puntos al mapa
function agregarParada(parada) {
    const marker = L.marker([parada.stop_lat, parada.stop_lon]).addTo(map);
    marker.bindPopup(`<b>${parada.stop_name}</b><br>${parada.stop_desc}`);
}

// Prueba de conexión
fetch('http://127.0.0.1:5000/api/test')
  .then(response => response.json())
  .then(data => {
    console.log('Respuesta del backend:', data);
    alert(data.message); // Muestra la respuesta en una alerta
  })
  .catch(error => {
    console.error('Error al conectar con el backend:', error);
  });


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