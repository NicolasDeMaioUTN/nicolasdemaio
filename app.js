// Formularios
const popupForm = document.getElementById('popup-form');
const stopForm = document.getElementById('stop-form');
const cancelButton = document.getElementById('cancel');
var map;
//Barra Lateral
const sidebar = document.getElementById('sidebar');
const toggleSidebar = document.getElementById('toggleSidebar');
let selectedLatLng = null;       // Puntero de Latitud y Longitud
let selectedH3Index = null; // Para identificar si se está sobre una parada existente

// Obtener referencia al menú y opciones
const contextMenu = document.getElementById("context-menu");
const addStopBtn = document.getElementById("add-stop");
const editStopBtn = document.getElementById("edit-stop");
const deleteStopBtn = document.getElementById("delete-stop");
const assignLinesBtn = document.getElementById("assign-lines");


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
    map.on("contextmenu", function (e) {
        selectedLatLng = e.latlng;
        // Mostrar menú en la posición del clic
        contextMenu.style.left = `${e.originalEvent.pageX}px`;
        contextMenu.style.top = `${e.originalEvent.pageY}px`;
        contextMenu.style.display = "block";
    });

    // Ocultar menú cuando se hace clic en otro lado
    document.addEventListener("click", function () {
        contextMenu.style.display = "none";
    });

    document.addEventListener("contextmenu", function (event) {
        event.preventDefault(); // Evita que el navegador bloquee el clic derecho
    });

} else {
    console.error("El contenedor del mapa no se encontró en el DOM.");
}
//#endregion


//#region Barra Lateral
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
    }
}

// Cerrar formulario emergente
document.getElementById('cancel').addEventListener('click', () => {
    document.getElementById('popup-form').classList.add('hidden');
});

// Manejar cancelación del formulario
cancelButton.addEventListener('click', function () {
    popupForm.classList.add('hidden');
});
//#endregion


//#region Guardado de Paradas
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
            alert('Parada guardada exitosamente!');
            stopForm.reset();
            stopForm.classList.add('hidden');

        } else {
            const errorData = await response.text();
            console.error('Error en la respuesta:', errorData);
            alert('Error al guardar la parada.');
        }
    } catch (error) {
        console.error('Error en la solicitud:', error);
    }

});
//#endregion


//#region Modificacion de Paradas
async function modificarParada(parada) {
    // Rellenar el formulario con la información actual de la parada
    document.getElementById("stop_name").value = parada.stop_name;
    document.getElementById("stop_desc").value = parada.stop_desc;
    document.getElementById("locationType").value = parada.location_type;
    document.getElementById("stop_lat").value = parada.stop_lat.toFixed(10);
    document.getElementById("stop_lon").value = parada.stop_lon.toFixed(10);

    // Mostrar el formulario para modificar la parada
    document.getElementById("popup-form").classList.remove("hidden");

    // Agregar evento al botón de guardar cambios
    document.getElementById("saveStopBtn").onclick = async function () {
        const stopData = {
            name: document.getElementById("stop_name").value,
            description: document.getElementById("stop_desc").value,
            tipo: document.getElementById("locationType").value,
            latitude: parseFloat(document.getElementById("stop_lat").value),
            longitude: parseFloat(document.getElementById("stop_lon").value),
        };

        try {
            const response = await fetch(`http://127.0.0.1:5000/api/paradas/${parada.h3_index}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(stopData),
            });

            if (response.ok) {
                const result = await response.json();
                console.log("Parada modificada:", result);
                alert("Parada modificada exitosamente!");
                document.getElementById("popup-form").classList.add("hidden");
            } else {
                const errorData = await response.text();
                console.error("Error en la respuesta:", errorData);
                alert("Error al modificar la parada.");
            }
        } catch (error) {
            console.error("Error en la solicitud:", error);
        }
    };
}

//#endregion


//#region Eliminacion de Paradas
function eliminarParada(h3Index) {
    if (!confirm("¿Estás seguro de que deseas eliminar esta parada?")) return;

    fetch(`http://127.0.0.1:5000/api/paradas/${h3Index}`, {
        method: 'DELETE',
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === "success") {
                alert("Parada eliminada correctamente.");

            } else {
                alert("Error al eliminar la parada: " + data.error);
            }
        })
        .catch(error => {
            console.error("Error en la solicitud:", error);
            alert("Ocurrió un error al intentar eliminar la parada.");
        });
}
//#endregion


//#region Capa de Paradas
const socket = io('http://localhost:5000'); // conecta al Flask
socket.on("actualizar_paradas", (paradas) => {
    console.log("Recibiendo actualización global de paradas:", paradas);
    actualizarMapaConParadas(paradas);
});

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


    
// Cargar todas las paradas guardadas al iniciar la página
function actualizarMapaConParadas(paradas) {
    // Eliminar todas las paradas actuales del mapa
    Object.values(markers).forEach(marker => map.removeLayer(marker));
    markers = {}; // Reiniciar objeto de marcadores

    // Agregar las nuevas paradas al mapa
    paradas.forEach(parada => {
        const marker = L.marker([parada.stop_lat, parada.stop_lon])
            .addTo(map)
            .bindPopup(`<b>${parada.stop_name}</b><br>${parada.stop_desc}`);

        markers[parada.h3_index] = marker; // Guardar marcador en el objeto
    });

    console.log("Mapa actualizado con nuevas paradas");
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
//#endregion


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


//#region Funciones del Menu Contextual
function handleMenuClick(action) {
    switch (action) {
        case "agregar":
            togglePopupForm(true, selectedLatLng); // logica de agregacion incluida en el stop-form
            break;
        case "modificar":
            buscarParadaPorUbicacion(selectedLatLng, modificarParada);
            break;
        case "eliminar":
            buscarParadaPorUbicacion(selectedLatLng, eliminarParada);
            break;
        case "asignar":
            alert("Funcionalidad en desarrollo: Asignar Líneas");
            break;
    }

    // Ocultar el menú después de la acción
    contextMenu.style.display = "none";
}

// Buscar paradas por ubicacion 
async function buscarParadaPorUbicacion(latlng, callback) {
    try {
        const response = await fetch("http://127.0.0.1:5000/api/paradas");
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const paradas = await response.json();

        const lat = parseFloat(latlng.lat);
        const lon = parseFloat(latlng.lng);

        if (isNaN(lat) || isNaN(lon)) {
            throw new Error("Latitud o longitud no son números válidos.");
        }

        // Convertir lat/lon a índice H3
        const h3Index = h3.latLngToCell(lat, lon, 12);

        // Buscar la parada correspondiente
        const parada = paradas.find(p => p.h3_index === h3Index);

        if (!parada) {
            alert("No se encontró la parada seleccionada.");
            return;
        }

        // Llamar al callback con la parada completa
        callback(parada);
    } catch (error) {
        console.error("Error al buscar parada:", error);
    }
}


// Acción: Agregar Paradas
/*
addStopBtn.addEventListener("click", function () {
    contextMenu.classList.add("hidden");

    if (!selectedLatLng) return;

    document.getElementById("stop_lat").value = selectedLatLng.lat.toFixed(10);
    document.getElementById("stop_lon").value = selectedLatLng.lng.toFixed(10);
    document.getElementById("popup-form").classList.remove("hidden");
    

    
});

// Acción: Modificar Parada
editStopBtn.addEventListener("click", function () {
    if (!selectedH3Index) {
        alert("Debes seleccionar una parada existente para modificar.");
        return;
    }

    contextMenu.classList.add("hidden");
    // Aquí puedes abrir el formulario con los datos de la parada
    alert("Abrir formulario de edición para: " + selectedH3Index);
});

// Acción: Eliminar Parada
deleteStopBtn.addEventListener("click", function () {
    if (!selectedH3Index) {
        alert("Debes seleccionar una parada existente para eliminar.");
        return;
    }

    eliminarParada(selectedH3Index);
    contextMenu.classList.add("hidden");
});

// Acción: Asignar Líneas
assignLinesBtn.addEventListener("click", function () {
    if (!selectedH3Index) {
        alert("Debes seleccionar una parada existente para asignar líneas.");
        return;
    }

    contextMenu.classList.add("hidden");
    alert("Asignar líneas a la parada con H3 Index: " + selectedH3Index);
});
*/
//#endregion