/* ==========================================================
   DCGL FIELDMATE
   MOBILE FIELD SURVEY
   Version 3.0

   GPS PIPELINE
   ----------------------------------------------------------
   GpsEngine
        ↓
   PolygonRecorder
        ↓
   AreaCalculator
        ↓
   Survey Data
        ↓
   IndexedDB / Review
   ==========================================================

   DEPENDENCIES
   ----------------------------------------------------------
   - Leaflet
   - GpsEngine
   - PolygonRecorder
   - AreaCalculator
   - offline_db.js
   - survey UI functions
========================================================== */


/* ==========================================================
   LEAFLET MAP
========================================================== */

const map =
    L.map("map").setView(
        [-12.25, 34.30],
        15
    );


L.tileLayer(

    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",

    {

        maxZoom: 22,

        attribution:
            "&copy; OpenStreetMap"

    }

).addTo(map);


/* ==========================================================
   GPS ENGINE
========================================================== */

const gps =
    new GpsEngine();


/* ==========================================================
   POLYGON RECORDER
========================================================== */

const polygon =
    new PolygonRecorder(map);


/* ==========================================================
   GPS MARKER
========================================================== */

let gpsMarker = null;


/* ==========================================================
   HELPER — SAFE UI UPDATE
========================================================== */

function setElementText(
    id,
    value
) {

    const element =
        document.getElementById(id);


    if (element) {

        element.innerHTML =
            value;

    }

}


/* ==========================================================
   FORMAT TIME
========================================================== */

function formatSurveyTime(
    totalSeconds
) {

    const seconds =
        Math.max(
            0,
            Number(totalSeconds) || 0
        );


    const hours =
        Math.floor(
            seconds / 3600
        );


    const minutes =
        Math.floor(
            (seconds % 3600) / 60
        );


    const secs =
        seconds % 60;


    return (

        String(hours)
            .padStart(2, "0")

        +

        ":" +

        String(minutes)
            .padStart(2, "0")

        +

        ":" +

        String(secs)
            .padStart(2, "0")

    );

}


/* ==========================================================
   UPDATE SURVEY STATISTICS
========================================================== */

function updateSurveyStatistics() {

    /*
     * Make sure measurements are current.
     */

    polygon.calculateSurveyMeasurements();


    const statistics =
        polygon.getStatistics();


    /* ------------------------------------------------------
       AREA
    ------------------------------------------------------ */

    setElementText(

        "surveyArea",

        statistics.areaHa.toFixed(3)

    );


    /* ------------------------------------------------------
       PERIMETER
    ------------------------------------------------------ */

    setElementText(

        "surveyPerimeter",

        statistics.perimeter.toFixed(1)

    );


    /* ------------------------------------------------------
       GPS POINTS
    ------------------------------------------------------ */

    setElementText(

        "surveyPoints",

        statistics.pointCount

    );


    /* ------------------------------------------------------
       DISTANCE WALKED
    ------------------------------------------------------ */

    setElementText(

        "surveyDistance",

        gps.statistics.distance.toFixed(1)

    );


    /* ------------------------------------------------------
       CURRENT ACCURACY
    ------------------------------------------------------ */

    if (gps.current) {

        setElementText(

            "currentAccuracy",

            Number(
                gps.current.accuracy
            ).toFixed(1)

        );

    }


    /* ------------------------------------------------------
       AVERAGE ACCURACY
    ------------------------------------------------------ */

    setElementText(

        "averageAccuracy",

        Number(
            gps.statistics.averageAccuracy || 0
        ).toFixed(1)

    );


    /* ------------------------------------------------------
       GPS QUALITY
    ------------------------------------------------------ */

    const quality =
        gps.quality();


    setElementText(

        "gpsQualityStatus",

        quality

    );


    /* ------------------------------------------------------
       SURVEY TIME
    ------------------------------------------------------ */

    setElementText(

        "surveyTime",

        formatSurveyTime(
            gps.statistics.elapsedSeconds
        )

    );

}


/* ==========================================================
   GPS UPDATE CALLBACK
========================================================== */

gps.onUpdate(

    engine => {


        /* ==================================================
           GPS STATUS
        ================================================== */

        setElementText(

            "gpsStatus",

            engine.state

        );


        /* ==================================================
           WAIT FOR GPS FIX
        ================================================== */

        if (!engine.current) {

            return;

        }


        /* ==================================================
           CURRENT LOCATION
        ================================================== */

        const latitude =
            engine.current.latitude;


        const longitude =
            engine.current.longitude;


        const accuracy =
            engine.current.accuracy;


        /* ==================================================
           DISPLAY LATITUDE
        ================================================== */

        setElementText(

            "lat",

            latitude.toFixed(6)

        );


        /* ==================================================
           DISPLAY LONGITUDE
        ================================================== */

        setElementText(

            "lng",

            longitude.toFixed(6)

        );


        /* ==================================================
           DISPLAY ACCURACY
        ================================================== */

        setElementText(

            "accuracy",

            "± " +
            accuracy.toFixed(1) +
            " m"

        );


        /* ==================================================
           GPS QUALITY
        ================================================== */

        setElementText(

            "gpsQuality",

            engine.quality()

        );


        /* ==================================================
           POSITION
        ================================================== */

        const position = [

            latitude,

            longitude

        ];


        /* ==================================================
           GPS MARKER
        ================================================== */

        if (!gpsMarker) {


            gpsMarker =
                L.marker(
                    position
                ).addTo(map);


            map.setView(

                position,

                18

            );

        }

        else {

            gpsMarker.setLatLng(
                position
            );

        }


        /* ==================================================
           RECORD SURVEY POINT
        ==================================================

           IMPORTANT:

           GpsEngine owns the GPS watch.

           PolygonRecorder owns the field boundary.

           We transfer each GPS fix to PolygonRecorder
           only while a survey is being recorded.
        */

        if (
            polygon.recording
        ) {


            polygon.addGpsPoint(

                engine.current

            );


            /*
             * Update live survey measurements.
             */

            updateSurveyStatistics();

        }


        /* ==================================================
           UPDATE MAIN UI
        ================================================== */

        if (
            typeof updateUI ===
            "function"
        ) {

            updateUI(
                engine
            );

        }


        /* ==================================================
           DEBUG INFORMATION
        ================================================== */

        console.log(
            "------------------------------------------"
        );

        console.log(
            "DCGL FieldMate GPS"
        );

        console.log(
            "STATE:",
            engine.state
        );

        console.log(
            "LAT:",
            latitude
        );

        console.log(
            "LNG:",
            longitude
        );

        console.log(
            "ACCURACY:",
            accuracy
        );

        console.log(
            "GPS QUALITY:",
            engine.quality()
        );

        console.log(
            "SURVEY RECORDING:",
            polygon.recording
        );

        console.log(
            "SURVEY POINTS:",
            polygon.points.length
        );

        console.log(
            "DISTANCE:",
            engine.statistics.distance
        );

        console.log(
            "------------------------------------------"
        );

    }

);


/* ==========================================================
   START GPS
========================================================== */

const startGPSButton =
    document.getElementById(
        "startGPS"
    );


if (startGPSButton) {

    startGPSButton.onclick =
        function () {

            console.log(
                "Starting DCGL FieldMate GPS..."
            );


            gps.start();

        };

}


/* ==========================================================
   START SURVEY
========================================================== */

const startSurveyButton =
    document.getElementById(
        "startSurvey"
    );


if (startSurveyButton) {

    startSurveyButton.onclick =
        function () {


            /* ----------------------------------------------
               GPS MUST BE RUNNING
            ---------------------------------------------- */

            if (
                gps.state !== "READY" &&
                gps.state !== "RECORDING"
            ) {

                alert(
                    "Please start GPS and wait for a GPS fix before starting the survey."
                );

                return;

            }


            /* ----------------------------------------------
               RESET POLYGON
            ---------------------------------------------- */

            polygon.start();


            /* ----------------------------------------------
               START GPS RECORDING
            ---------------------------------------------- */

            gps.startRecording();


            console.log(
                "=========================================="
            );

            console.log(
                "DCGL FIELD SURVEY STARTED"
            );

            console.log(
                "=========================================="
            );


            updateSurveyStatistics();

        };

}


/* ==========================================================
   FINISH SURVEY
========================================================== */

const finishSurveyButton =
    document.getElementById(
        "finishSurvey"
    );


if (finishSurveyButton) {

    finishSurveyButton.onclick =
        async function () {


            /* ----------------------------------------------
               CHECK POINT COUNT
            ---------------------------------------------- */

            if (
                polygon.points.length < 3
            ) {

                alert(
                    "At least 3 GPS points are required to create a field boundary."
                );

                return;

            }


            /* ----------------------------------------------
               STOP GPS RECORDING
            ---------------------------------------------- */

            gps.stopRecording();


            /* ----------------------------------------------
               STOP POLYGON RECORDING
            ---------------------------------------------- */

            polygon.stop();


            /* ----------------------------------------------
               CLOSE POLYGON
            ---------------------------------------------- */

            const closedPolygon =
                polygon.closePolygon();


            if (!closedPolygon) {

                alert(
                    "Unable to close the survey polygon."
                );

                return;

            }


            /* ----------------------------------------------
               FINAL MEASUREMENTS
            ---------------------------------------------- */

            polygon.calculateSurveyMeasurements();


            const statistics =
                polygon.getStatistics();


            /* ----------------------------------------------
               GEOJSON
            ---------------------------------------------- */

            const geojson =
                polygon.exportGeoJSON();


            if (!geojson) {

                alert(
                    "Unable to create survey GeoJSON."
                );

                return;

            }


            /* =================================================
               LOAD EXISTING SURVEY SESSION
            ================================================= */

            let survey = {};


            try {

                survey =
                    JSON.parse(

                        sessionStorage.getItem(
                            "dcglSurvey"
                        )

                    ) || {};

            }

            catch (error) {

                console.warn(
                    "Existing survey session could not be read.",
                    error
                );

                survey = {};

            }


            /* =================================================
               SURVEY MEASUREMENTS
            ================================================= */

            survey.area =
                statistics.areaHa;


            survey.area_m2 =
                statistics.area;


            survey.perimeter =
                statistics.perimeter;


            survey.points =
                statistics.pointCount;


            survey.distance =
                gps.statistics.distance;


            survey.time =
                formatSurveyTime(

                    gps.statistics.elapsedSeconds

                );


            survey.elapsed_seconds =
                gps.statistics.elapsedSeconds;


            /* =================================================
               GPS ACCURACY
            ================================================= */

            survey.average_accuracy =
                gps.statistics.averageAccuracy;


            survey.best_accuracy =
                gps.statistics.bestAccuracy;


            survey.worst_accuracy =
                gps.statistics.worstAccuracy;


            survey.current_accuracy =

                gps.current

                ? gps.current.accuracy

                : null;


            /* =================================================
               GPS STATUS
            ================================================= */

            survey.gps_quality =
                gps.quality();


            /* =================================================
               SURVEY TIMING
            ================================================= */

            survey.started_at =
                polygon.statistics.startTime;


            survey.completed_at =
                polygon.statistics.endTime;


            /* =================================================
               RAW GPS POINTS
            ================================================= */

            survey.gps_points =
                polygon.exportPoints();


            /* =================================================
               GEOJSON
            ================================================= */

            survey.geojson =
                geojson;


            /* =================================================
               SURVEY VERSION
            ================================================= */

            survey.survey_version =
                "3.0";


            survey.source =
                "DCGL FieldMate Mobile Survey";


            /* =================================================
               SAVE TO SESSION STORAGE
            ================================================= */

            sessionStorage.setItem(

                "dcglSurvey",

                JSON.stringify(
                    survey
                )

            );


            /* =================================================
               SAVE TO OFFLINE DATABASE
            ================================================= */

            /*
             * saveSurveyOffline() is supplied by
             * offline_db.js.
             */

            if (
                typeof saveSurveyOffline ===
                "function"
            ) {

                try {

                    const offlineRecord =
                        await saveSurveyOffline(
                            survey
                        );


                    console.log(
                        "Survey saved to offline database:",
                        offlineRecord.survey_id
                    );


                    /*
                     * Keep the generated survey ID
                     * in session storage as well.
                     */

                    survey.survey_id =
                        offlineRecord.survey_id;


                    sessionStorage.setItem(

                        "dcglSurvey",

                        JSON.stringify(
                            survey
                        )

                    );

                }

                catch (error) {

                    console.error(
                        "Offline survey save failed:",
                        error
                    );


                    /*
                     * The session copy remains available.
                     */

                    alert(
                        "Survey was prepared, but the offline database could not save it. Please do not close the application yet."
                    );

                    return;

                }

            }

            else {

                console.warn(
                    "saveSurveyOffline() is not available. Survey kept in sessionStorage."
                );

            }


            /* =================================================
               DEBUG
            ================================================= */

            console.clear();


            console.log(
                "=========================================="
            );

            console.log(
                "DCGL FIELD SURVEY COMPLETE"
            );

            console.log(
                "=========================================="
            );


            console.log(
                "SURVEY:",
                survey
            );


            console.log(
                "AREA:",
                statistics.areaHa,
                "ha"
            );


            console.log(
                "AREA:",
                statistics.area,
                "m²"
            );


            console.log(
                "PERIMETER:",
                statistics.perimeter,
                "m"
            );


            console.log(
                "POINTS:",
                statistics.pointCount
            );


            console.log(
                "DISTANCE:",
                gps.statistics.distance,
                "m"
            );


            console.log(
                "AVERAGE ACCURACY:",
                gps.statistics.averageAccuracy,
                "m"
            );


            console.log(
                "GEOJSON:",
                geojson
            );


            /* =================================================
               OPEN REVIEW SCREEN
            ================================================= */

            window.location.href =
                "/mobile/survey_review";

        };

}


/* ==========================================================
   INITIALIZE SCREEN
========================================================== */

if (
    typeof updateUI ===
    "function"
) {

    updateUI(
        gps
    );

}


if (
    typeof initialiseSurveyDashboard ===
    "function"
) {

    initialiseSurveyDashboard();

}


/* ==========================================================
   INITIALIZATION MESSAGE
========================================================== */

console.log(
    "=================================================="
);

console.log(
    "DCGL FieldMate survey.js Version 3.0 loaded."
);

console.log(
    "GPS: GpsEngine"
);

console.log(
    "Polygon: PolygonRecorder"
);

console.log(
    "Area: AreaCalculator"
);

console.log(
    "Offline storage: IndexedDB"
);

console.log(
    "=================================================="
);