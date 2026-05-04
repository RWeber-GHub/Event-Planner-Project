async function loadEvents(apiUrl) {
    const res = await fetch(apiUrl);
    if (!res.ok) throw new Error("Failed to load events");
    return await res.json();
}

function createMarker(map, event) {
    const lat = Number(event.Latitude);
    const lng = Number(event.Longitude);

    if (isNaN(lat) || isNaN(lng)) return null;

    const marker = new google.maps.Marker({
        position: { lat, lng },
        map,
        title: event.EventName,
        animation: google.maps.Animation.DROP,
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 8,
            fillColor: "#3b82f6",
            fillOpacity: 1,
            strokeColor: "#ffffff",
            strokeWeight: 2,
        }
    });

    const infoWindow = new google.maps.InfoWindow({
        content: `
            <div style="padding:10px; max-width:220px;">
                <h3 style="margin:0; color:#3b82f6;">
                    ${event.EventName}
                </h3>
                <p style="margin:6px 0;">
                    ${event.VenueName || ""}
                </p>
                <small>${event.Location || ""}</small>
                <br>
                <a href="/events/${event.EventID}"
                   style="display:inline-block;
                          margin-top:8px;
                          padding:6px 10px;
                          background:#3b82f6;
                          color:white;
                          border-radius:4px;
                          text-decoration:none;">
                    View Event
                </a>
            </div>
        `
    });

    marker.addListener("click", () => {
        infoWindow.open(map, marker);
    });

    return marker;
}

function enableSearchBox(map, inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const searchBox = new google.maps.places.SearchBox(input);

    map.addListener("bounds_changed", () => {
        searchBox.setBounds(map.getBounds());
    });

    let searchMarker;

    searchBox.addListener("places_changed", () => {
        const places = searchBox.getPlaces();
        if (!places.length) return;

        const place = places[0];
        if (!place.geometry || !place.geometry.location) return;

        if (searchMarker) searchMarker.setMap(null);

        searchMarker = new google.maps.Marker({
            map,
            position: place.geometry.location,
            animation: google.maps.Animation.DROP,
        });

        map.panTo(place.geometry.location);
        map.setZoom(12);
    });
}

export async function initMap(config = {}) {
    const {
        mapId = "map",
        api = "/api/events",
        center = { lat: 39.5, lng: -98.35 },
        zoom = 4,
        enableSearch = false,
        searchInputId = "searchBox"
    } = config;

    const mapElement = document.getElementById(mapId);
    if (!mapElement) return;

    const map = new google.maps.Map(mapElement, {
        center,
        zoom,
        streetViewControl: false,
        mapTypeControl: false,
        fullscreenControl: false,
        zoomControl: true,
    });

    const events = await loadEvents(api);
    const bounds = new google.maps.LatLngBounds();

    events.forEach(event => {
        const marker = createMarker(map, event);
        if (marker) {
            bounds.extend(marker.getPosition());
        }
    });

    if (events.length) {
        map.fitBounds(bounds);
    }

    if (enableSearch) {
        enableSearchBox(map, searchInputId);
    }

    return map;
}