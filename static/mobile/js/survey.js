/* ==========================================================
   DCGL MOBILE FIELD SURVEY
========================================================== */

//----------------------------------------------------------
// LEAFLET MAP
//----------------------------------------------------------

const map = L.map("map").setView([-12.25, 34.30], 15);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 22,
        attribution: "&copy; OpenStreetMap"
    }
).addTo(map);

//----------------------------------------------------------
// GPS + POLYGON
//----------------------------------------------------------

const gps = new GpsEngine();

const polygon = new PolygonRecorder(map);

let gpsMarker = null;

//----------------------------------------------------------
// UPDATE USER INTERFACE
//----------------------------------------------------------

function updateUI(engine){

    const gpsBtn =
        document.getElementById("startGPS");

    const surveyBtn =
        document.getElementById("startSurvey");

    const finishBtn =
        document.getElementById("finishSurvey");

    switch(engine.state){

        case "STOPPED":

            gpsBtn.innerHTML =
                "📡 Start GPS";

            surveyBtn.innerHTML =
                "▶ Start Survey";

            surveyBtn.disabled = true;

            finishBtn.disabled = true;

            break;

        case "SEARCHING":

            gpsBtn.innerHTML =
                "🛰 Searching...";

            surveyBtn.disabled = true;

            finishBtn.disabled = true;

            break;

        case "READY":

            gpsBtn.innerHTML =
                "🟢 GPS Ready";

            surveyBtn.innerHTML =
                "▶ Start Survey";

            surveyBtn.disabled = false;

            finishBtn.disabled = true;

            break;

        case "RECORDING":

            gpsBtn.innerHTML =
                "🟢 GPS Ready";

            surveyBtn.innerHTML =
                "🔴 Recording...";

            surveyBtn.disabled = true;

            finishBtn.disabled = false;

            break;

    }

}

//----------------------------------------------------------
// UPDATE SCREEN
//----------------------------------------------------------

gps.onUpdate(engine => {

    //------------------------------------------------------
    // STATUS
    //------------------------------------------------------

    document.getElementById("gpsStatus").innerHTML =
        engine.state;

    //------------------------------------------------------
    // WAIT FOR GPS FIX
    //------------------------------------------------------

    if (!engine.current)
        return;

    //------------------------------------------------------
    // LOCATION
    //------------------------------------------------------

    document.getElementById("lat").innerHTML =
        engine.current.latitude.toFixed(6);

    document.getElementById("lng").innerHTML =
        engine.current.longitude.toFixed(6);

    //------------------------------------------------------
    // ACCURACY
    //------------------------------------------------------

    document.getElementById("accuracy").innerHTML =
        "± " +
        engine.current.accuracy.toFixed(1) +
        " m";

    //------------------------------------------------------
    // QUALITY
    //------------------------------------------------------

    document.getElementById("gpsQuality").innerHTML =
        engine.quality();

    //------------------------------------------------------
    // CURRENT POSITION
    //------------------------------------------------------

    const position = [
        engine.current.latitude,
        engine.current.longitude
    ];

    //------------------------------------------------------
    // UPDATE MAP MARKER
    //------------------------------------------------------

    if (!gpsMarker) {

        gpsMarker = L.marker(position).addTo(map);

        map.setView(position, 18);

    } else {

        gpsMarker.setLatLng(position);

    }

    //------------------------------------------------------
    // DRAW SURVEY TRACK
    //------------------------------------------------------

    if (polygon.recording) {

    polygon.addPoint(
        engine.current.latitude,
        engine.current.longitude,
        engine.current.accuracy
    );

    //--------------------------------------------------
    // LIVE SURVEY STATISTICS
    //--------------------------------------------------

    const area =
        AreaCalculator.calculate(polygon.points);

    const perimeter =
        AreaCalculator.perimeter(polygon.points);

    document.getElementById("surveyArea").innerHTML =
        (area / 10000).toFixed(3);

    document.getElementById("surveyPerimeter").innerHTML =
        perimeter.toFixed(1);

    document.getElementById("surveyPoints").innerHTML =
        polygon.points.length;

}

    //------------------------------------------------------
    // UPDATE USER INTERFACE
    //------------------------------------------------------

    updateUI(engine);

    //------------------------------------------------------
    // DEBUG
    //------------------------------------------------------

    console.clear();

    console.log("STATE:", engine.state);

    console.log("QUALITY:", engine.quality());

    console.log("POINTS:", polygon.points.length);

    console.log(engine.current);

});

//----------------------------------------------------------
// START GPS
//----------------------------------------------------------

document.getElementById("startGPS").onclick = function () {

    gps.start();

};

//----------------------------------------------------------
// START SURVEY
//----------------------------------------------------------

document.getElementById("startSurvey").onclick = function () {

    gps.startRecording();

    polygon.start();

    console.log("Survey Started");

};

//----------------------------------------------------------
// FINISH SURVEY
//----------------------------------------------------------

document.getElementById("finishSurvey").onclick = function () {

    gps.stopRecording();

    polygon.stop();

    polygon.closePolygon();

    updateUI(gps);

    const area =
        AreaCalculator.calculate(polygon.points);

    const perimeter =
        AreaCalculator.perimeter(polygon.points);

    console.clear();

    console.log("=================================");

    console.log(" DCGL SURVEY COMPLETE");

    console.log("=================================");

    console.log("Area (ha):", (area / 10000).toFixed(3));

    console.log("Perimeter (m):", perimeter.toFixed(1));

    console.log("Points:", polygon.points.length);

    console.log("GeoJSON:");

    console.log(polygon.exportGeoJSON());

    const survey = {

    field: "NEW_FIELD",

    crop: "",

    soil: "",

    area: area / 10000,

    geojson: polygon.exportGeoJSON()

};

fetch("/mobile/save_survey", {

    method: "POST",

    headers: {

        "Content-Type": "application/json"

    },

    body: JSON.stringify(survey)

})

.then(r => r.json())

.then(data => {

    alert(data.message);

    console.log(data);

})

.catch(err => {

    console.error(err);

});

};