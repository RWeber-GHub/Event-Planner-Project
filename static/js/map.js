async function loadEvents(apiUrl) {

    const res = await fetch(apiUrl);

    if (!res.ok) {
        throw new Error("Failed to load events");
    }

    return await res.json();
}

function createMarker(map, event) {

    const lat = Number(event.Latitude);
    const lng = Number(event.Longitude);

    if (isNaN(lat) || isNaN(lng)) {
        return null;
    }

    const marker = new google.maps.Marker({
        position: { lat, lng },
        map,
        title: event.EventName,

        animation: google.maps.Animation.DROP,

        icon: {
            url: "https://maps.google.com/mapfiles/ms/icons/blue-dot.png"
        }
    });

    const infoWindow = new google.maps.InfoWindow({
        content: `
            <div style="
                width:220px;
                font-family:Arial;
            ">

                <h4 style="
                    margin:4px 0;
                    font-size:14px;
                    color:#1e293b;
                ">
                    ${event.EventName}
                </h4>

                <p style="
                    margin:0;
                    font-size:12px;
                    color:#475569;
                ">
                    ${event.VenueName || ""}
                </p>

                <p style="
                    margin:0 0 8px;
                    font-size:11px;
                    color:#64748b;
                ">
                    ${event.Location || ""}
                </p>

                ${
                    event.ImageURL
                    ? `
                    <img
                        src="${event.ImageURL}"
                        style="
                            width:100%;
                            height:120px;
                            object-fit:contain;
                            background:#f8fafc;
                            border-radius:8px;
                            margin-top:8px;
                        "
                    >
                    `
                    : ""
                }

                <a
                    href="/events/view/${event.VariantID}"
                    style="
                        display:inline-block;
                        margin-top:10px;
                        padding:6px 10px;
                        background:#2563eb;
                        color:white;
                        border-radius:6px;
                        text-decoration:none;
                        font-size:12px;
                    "
                >
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

        if (!place.geometry || !place.geometry.location) {
            return;
        }

        if (searchMarker) {
            searchMarker.setMap(null);
        }

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

        styles: [
            {
                elementType: "geometry",
                stylers: [{ color: "#f8fafc" }]
            },
            {
                elementType: "labels.text.fill",
                stylers: [{ color: "#616161" }]
            },
            {
                elementType: "labels.text.stroke",
                stylers: [{ color: "#f5f5f5" }]
            },
            {
                featureType: "road",
                elementType: "geometry",
                stylers: [{ color: "#ffffff" }]
            },
            {
                featureType: "water",
                elementType: "geometry",
                stylers: [{ color: "#cbd5e1" }]
            },
            {
                featureType: "poi",
                stylers: [{ visibility: "off" }]
            }
        ]
    });

    const events = await loadEvents(api);

    events.forEach(event => {
        createMarker(map, event);
    });

    map.setCenter({ lat: 39.5, lng: -98.35 });
    map.setZoom(4);

    if (enableSearch) {
        enableSearchBox(map, searchInputId);
    }

    return map;
}