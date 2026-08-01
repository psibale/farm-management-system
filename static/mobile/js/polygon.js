//--------------------------------------------------
// DCGL POLYGON RECORDER
//--------------------------------------------------

class PolygonRecorder {

    constructor(map) {

        this.map = map;

        this.points = [];

        this.recording = false;

        this.track = L.polyline([], {
            color: "#0d6efd",
            weight: 4
        }).addTo(map);

        this.polygon = null;

    }

    //--------------------------------------------------
    // START NEW SURVEY
    //--------------------------------------------------

    start() {

        this.recording = true;

        this.points = [];

        this.track.setLatLngs([]);

        if (this.polygon) {

            this.map.removeLayer(this.polygon);

            this.polygon = null;

        }

        console.log("Survey started.");

    }

    //--------------------------------------------------
    // STOP RECORDING
    //--------------------------------------------------

    stop() {

        this.recording = false;

        console.log("Survey stopped.");

    }

    //--------------------------------------------------
    // ADD GPS POINT
    //--------------------------------------------------

    addPoint(lat, lng, accuracy = 0) {

        if (!this.recording)
            return;

        this.points.push({
            lat,
            lng,
            accuracy,
            time: new Date()
        });

        this.redraw();

    }

    //--------------------------------------------------
    // REDRAW TRACK
    //--------------------------------------------------

    redraw() {

        const latlngs = this.points.map(p => [p.lat, p.lng]);

        this.track.setLatLngs(latlngs);

    }

    //--------------------------------------------------
    // CLOSE POLYGON
    //--------------------------------------------------

    closePolygon() {

        if (this.points.length < 3)
            return;

        if (this.polygon) {

            this.map.removeLayer(this.polygon);

        }

        this.polygon = L.polygon(

            this.points.map(p => [p.lat, p.lng]),

            {
                color: "#198754",
                weight: 3,
                fillOpacity: 0.25
            }

        ).addTo(this.map);

    }

    //--------------------------------------------------
    // EXPORT GEOJSON
    //--------------------------------------------------

    exportGeoJSON() {

        if (!this.polygon)
            return null;

        return this.polygon.toGeoJSON();

    }

    //--------------------------------------------------
    // RESET
    //--------------------------------------------------

    reset() {

        this.points = [];

        this.track.setLatLngs([]);

        if (this.polygon) {

            this.map.removeLayer(this.polygon);

            this.polygon = null;

        }

        this.recording = false;

    }

}