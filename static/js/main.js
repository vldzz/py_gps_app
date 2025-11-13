(function () {
    const form = document.getElementById("ride-form");
    const overlay = document.getElementById("loading-overlay");

    if (form && overlay) {
        form.addEventListener("submit", () => {
            overlay.classList.add("loading-overlay--visible");
        });
    }

    window.initializeMap = function initializeMap(station) {
        const mapContainer = document.getElementById("map");
        if (!mapContainer) {
            return;
        }

        const { latitude, longitude, name } = station;
        const map = L.map(mapContainer, {
            zoomControl: false,
            scrollWheelZoom: false,
        }).setView([latitude, longitude], 12);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "© OpenStreetMap contributors",
        }).addTo(map);

        L.control.zoom({ position: "bottomright" }).addTo(map);

        const popupContent = `
            <div class="popup">
                <strong>${name}</strong><br>
                Координаты: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}
            </div>
        `;

        L.marker([latitude, longitude]).addTo(map).bindPopup(popupContent).openPopup();
        L.circle([latitude, longitude], {
            radius: 750,
            color: "#58a6ff",
            weight: 1,
            fillOpacity: 0.08,
        }).addTo(map);
    };
})();

