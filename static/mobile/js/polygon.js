/* ==========================================================
   DCGL FIELDMATE
   Polygon Survey Recorder
   Version 2.0

   PURPOSE
   ----------------------------------------------------------
   - Record GPS survey points
   - Build live survey track
   - Prevent unnecessary duplicate GPS points
   - Display survey polygon
   - Calculate survey statistics
   - Export valid GeoJSON
   - Work with GpsEngine
   - Support offline survey workflow

   DEPENDENCIES
   ----------------------------------------------------------
   - Leaflet (L)
   - GpsEngine
   - AreaCalculator
========================================================== */


class PolygonRecorder {


    /* ======================================================
       CONSTRUCTOR
    ====================================================== */

    constructor(map) {

        this.map = map;

        this.points = [];

        this.recording = false;

        this.polygon = null;

        this.lastPoint = null;

        /*
         * Minimum movement required before another GPS
         * point is recorded.
         *
         * 1 metre prevents excessive duplicate points
         * when the surveyor is standing still.
         */
        this.minimumPointDistance = 1;


        /* --------------------------------------------------
           LIVE TRACK
        -------------------------------------------------- */

        this.track = L.polyline(

            [],

            {

                color: "#0d6efd",

                weight: 4,

                opacity: 0.85

            }

        ).addTo(map);


        /* --------------------------------------------------
           SURVEY MARKERS
        -------------------------------------------------- */

        this.pointMarkers = L.layerGroup().addTo(map);


        /* --------------------------------------------------
           SURVEY STATISTICS
        -------------------------------------------------- */

        this.statistics = {

            pointCount: 0,

            distance: 0,

            area: 0,

            perimeter: 0,

            startTime: null,

            endTime: null,

            elapsedSeconds: 0,

            bestAccuracy: null,

            worstAccuracy: null,

            averageAccuracy: 0

        };

    }


    /* ======================================================
       START NEW SURVEY
    ====================================================== */

    start() {

        /*
         * Clear previous survey.
         */

        this.reset();


        this.recording = true;

        this.statistics.startTime =
            new Date().toISOString();


        console.log(
            "=================================================="
        );

        console.log(
            "DCGL FieldMate polygon survey started."
        );

        console.log(
            "=================================================="
        );

    }


    /* ======================================================
       STOP RECORDING
    ====================================================== */

    stop() {

        if (!this.recording) {

            return;

        }


        this.recording = false;


        this.statistics.endTime =
            new Date().toISOString();


        if (
            this.statistics.startTime
        ) {

            const start =
                new Date(
                    this.statistics.startTime
                ).getTime();


            const end =
                new Date(
                    this.statistics.endTime
                ).getTime();


            this.statistics.elapsedSeconds =
                Math.max(
                    0,
                    Math.floor(
                        (end - start) / 1000
                    )
                );

        }


        /*
         * Close the visual polygon if enough
         * points have been recorded.
         */

        if (
            this.points.length >= 3
        ) {

            this.closePolygon();

        }


        console.log(
            "DCGL FieldMate polygon survey stopped."
        );

    }


    /* ======================================================
       ADD GPS POINT
    ====================================================== */

    addPoint(
        lat,
        lng,
        accuracy = 0,
        timestamp = null
    ) {

        /*
         * Do not accept points unless recording.
         */

        if (!this.recording) {

            return false;

        }


        /*
         * Validate coordinates.
         */

        if (
            !Number.isFinite(lat) ||
            !Number.isFinite(lng)
        ) {

            console.warn(
                "Invalid GPS coordinate rejected:",
                lat,
                lng
            );

            return false;

        }


        /*
         * Validate latitude and longitude ranges.
         */

        if (
            lat < -90 ||
            lat > 90 ||
            lng < -180 ||
            lng > 180
        ) {

            console.warn(
                "GPS coordinate outside valid range."
            );

            return false;

        }


        /* --------------------------------------------------
           DUPLICATE / MOVEMENT FILTER
        -------------------------------------------------- */

        if (this.lastPoint) {

            const distance =
                this.distanceBetweenPoints(

                    this.lastPoint.lat,

                    this.lastPoint.lng,

                    lat,

                    lng

                );


            /*
             * Ignore movement smaller than the
             * configured threshold.
             */

            if (
                distance <
                this.minimumPointDistance
            ) {

                return false;

            }

        }


        /* --------------------------------------------------
           CREATE POINT
        -------------------------------------------------- */

        const point = {

            lat: lat,

            lng: lng,

            accuracy:
                Number(accuracy) || 0,

            time:
                timestamp
                ? new Date(timestamp).toISOString()
                : new Date().toISOString()

        };


        /* --------------------------------------------------
           DISTANCE
        -------------------------------------------------- */

        if (this.points.length > 0) {

            const previous =
                this.points[
                    this.points.length - 1
                ];


            const distance =
                this.distanceBetweenPoints(

                    previous.lat,

                    previous.lng,

                    point.lat,

                    point.lng

                );


            this.statistics.distance +=
                distance;

        }


        /* --------------------------------------------------
           SAVE POINT
        -------------------------------------------------- */

        this.points.push(point);

        this.lastPoint = point;


        /* --------------------------------------------------
           UPDATE STATISTICS
        -------------------------------------------------- */

        this.updateStatistics();


        /* --------------------------------------------------
           REDRAW TRACK
        -------------------------------------------------- */

        this.redraw();


        return true;

    }


    /* ======================================================
       ADD GPS ENGINE POINT
    ====================================================== */

    addGpsPoint(gps) {

        if (!gps) {

            return false;

        }


        return this.addPoint(

            gps.latitude,

            gps.longitude,

            gps.accuracy,

            gps.timestamp

        );

    }


    /* ======================================================
       REDRAW TRACK
    ====================================================== */

    redraw() {

        const latlngs =
            this.points.map(

                point => [

                    point.lat,

                    point.lng

                ]

            );


        this.track.setLatLngs(
            latlngs
        );


        /*
         * Keep map centred on the latest
         * survey point.
         */

        if (
            this.points.length > 0
        ) {

            const latest =
                this.points[
                    this.points.length - 1
                ];


            /*
             * Do not constantly force the map
             * centre while the surveyor is working.
             *
             * The marker/track is enough.
             */

        }

    }


    /* ======================================================
       CLOSE POLYGON
    ====================================================== */

    closePolygon() {

        if (
            this.points.length < 3
        ) {

            console.warn(
                "At least 3 GPS points are required."
            );

            return null;

        }


        /*
         * Remove existing polygon.
         */

        if (this.polygon) {

            this.map.removeLayer(
                this.polygon
            );

            this.polygon = null;

        }


        /* --------------------------------------------------
           CREATE LEAFLET POLYGON
        -------------------------------------------------- */

        this.polygon =
            L.polygon(

                this.points.map(

                    point => [

                        point.lat,

                        point.lng

                    ]

                ),

                {

                    color: "#198754",

                    weight: 3,

                    opacity: 0.95,

                    fillColor: "#198754",

                    fillOpacity: 0.20

                }

            ).addTo(
                this.map
            );


        /* --------------------------------------------------
           CALCULATE AREA AND PERIMETER
        -------------------------------------------------- */

        this.calculateSurveyMeasurements();


        console.log(
            "Polygon closed."
        );


        console.log(
            "Area:",
            this.statistics.area,
            "m²"
        );


        console.log(
            "Perimeter:",
            this.statistics.perimeter,
            "m"
        );


        return this.polygon;

    }


    /* ======================================================
       CALCULATE SURVEY MEASUREMENTS
    ====================================================== */

    calculateSurveyMeasurements() {

        if (
            this.points.length < 3
        ) {

            this.statistics.area = 0;

            this.statistics.perimeter = 0;

            return;

        }


        /*
         * AreaCalculator is supplied by area.js.
         */

        if (
            typeof AreaCalculator !==
            "undefined"
        ) {

            this.statistics.area =
                AreaCalculator.calculate(
                    this.points
                );


            /*
             * Perimeter should represent the
             * closed polygon, not only the open track.
             */

            this.statistics.perimeter =
                this.closedPerimeter();

        }

    }


    /* ======================================================
       CLOSED POLYGON PERIMETER
    ====================================================== */

    closedPerimeter() {

        if (
            this.points.length < 3
        ) {

            return 0;

        }


        let perimeter = 0;


        for (
            let i = 0;
            i < this.points.length;
            i++
        ) {

            const current =
                this.points[i];


            const next =
                this.points[
                    (i + 1) %
                    this.points.length
                ];


            perimeter +=
                this.distanceBetweenPoints(

                    current.lat,

                    current.lng,

                    next.lat,

                    next.lng

                );

        }


        return perimeter;

    }


    /* ======================================================
       HAVERSINE DISTANCE
    ====================================================== */

    distanceBetweenPoints(

        lat1,
        lng1,
        lat2,
        lng2

    ) {

        const R =
            6378137;


        const dLat =
            (lat2 - lat1)
            *
            Math.PI
            /
            180;


        const dLng =
            (lng2 - lng1)
            *
            Math.PI
            /
            180;


        const a =

            Math.sin(
                dLat / 2
            ) ** 2

            +

            Math.cos(
                lat1 *
                Math.PI /
                180
            )

            *

            Math.cos(
                lat2 *
                Math.PI /
                180
            )

            *

            Math.sin(
                dLng / 2
            ) ** 2;


        return (

            2 *
            R *
            Math.atan2(

                Math.sqrt(a),

                Math.sqrt(
                    1 - a
                )

            )

        );

    }


    /* ======================================================
       UPDATE STATISTICS
    ====================================================== */

    updateStatistics() {

        this.statistics.pointCount =
            this.points.length;


        /*
         * Accuracy statistics.
         */

        const validAccuracy =
            this.points

                .map(
                    point =>
                        Number(
                            point.accuracy
                        )
                )

                .filter(
                    accuracy =>
                        Number.isFinite(
                            accuracy
                        ) &&
                        accuracy > 0
                );


        if (
            validAccuracy.length > 0
        ) {

            this.statistics.bestAccuracy =
                Math.min(
                    ...validAccuracy
                );


            this.statistics.worstAccuracy =
                Math.max(
                    ...validAccuracy
                );


            const total =
                validAccuracy.reduce(

                    (
                        sum,
                        value
                    ) =>
                        sum + value,

                    0

                );


            this.statistics.averageAccuracy =

                total /
                validAccuracy.length;

        }


        /*
         * Elapsed time.
         */

        if (
            this.statistics.startTime
        ) {

            this.statistics.elapsedSeconds =

                Math.floor(

                    (
                        Date.now()

                        -

                        new Date(
                            this.statistics.startTime
                        ).getTime()

                    )

                    /

                    1000

                );

        }

    }


    /* ======================================================
       GET AREA IN HECTARES
    ====================================================== */

    getAreaHectares() {

        return (

            this.statistics.area
            /
            10000

        );

    }


    /* ======================================================
       GET SURVEY STATISTICS
    ====================================================== */

    getStatistics() {

        /*
         * Recalculate measurements before
         * returning the final result.
         */

        this.calculateSurveyMeasurements();


        return {

            pointCount:
                this.statistics.pointCount,

            distance:
                this.statistics.distance,

            area:
                this.statistics.area,

            areaHa:
                this.getAreaHectares(),

            perimeter:
                this.statistics.perimeter,

            startTime:
                this.statistics.startTime,

            endTime:
                this.statistics.endTime,

            elapsedSeconds:
                this.statistics.elapsedSeconds,

            bestAccuracy:
                this.statistics.bestAccuracy,

            worstAccuracy:
                this.statistics.worstAccuracy,

            averageAccuracy:
                this.statistics.averageAccuracy

        };

    }


    /* ======================================================
       EXPORT GEOJSON
    ====================================================== */

    exportGeoJSON() {

        /*
         * A polygon requires at least
         * three points.
         */

        if (
            this.points.length < 3
        ) {

            console.warn(
                "Not enough points for GeoJSON polygon."
            );

            return null;

        }


        /*
         * Ensure polygon exists.
         */

        if (!this.polygon) {

            this.closePolygon();

        }


        if (!this.polygon) {

            return null;

        }


        const geojson =
            this.polygon.toGeoJSON();


        /*
         * Add DCGL survey information
         * to GeoJSON properties.
         */

        geojson.properties = {

            survey_type:
                "Field Boundary Survey",

            point_count:
                this.points.length,

            area_m2:
                this.statistics.area,

            area_ha:
                this.getAreaHectares(),

            perimeter_m:
                this.statistics.perimeter,

            survey_distance_m:
                this.statistics.distance,

            best_accuracy_m:
                this.statistics.bestAccuracy,

            worst_accuracy_m:
                this.statistics.worstAccuracy,

            average_accuracy_m:
                this.statistics.averageAccuracy,

            survey_started:
                this.statistics.startTime,

            survey_completed:
                this.statistics.endTime

        };


        return geojson;

    }


    /* ======================================================
       EXPORT RAW GPS POINTS
    ====================================================== */

    exportPoints() {

        return this.points.map(

            point => ({

                lat:
                    point.lat,

                lng:
                    point.lng,

                accuracy:
                    point.accuracy,

                time:
                    point.time

            })

        );

    }


    /* ======================================================
       GET LAST POINT
    ====================================================== */

    getLastPoint() {

        return this.lastPoint;

    }


    /* ======================================================
       GET POINT COUNT
    ====================================================== */

    getPointCount() {

        return this.points.length;

    }


    /* ======================================================
       IS RECORDING?
    ====================================================== */

    isRecording() {

        return this.recording;

    }


    /* ======================================================
       RESET
    ====================================================== */

    reset() {

        this.points = [];

        this.lastPoint = null;

        this.recording = false;


        this.track.setLatLngs([]);


        if (this.polygon) {

            this.map.removeLayer(
                this.polygon
            );

            this.polygon = null;

        }


        /*
         * Remove point markers.
         */

        if (this.pointMarkers) {

            this.pointMarkers.clearLayers();

        }


        /*
         * Reset statistics.
         */

        this.statistics = {

            pointCount: 0,

            distance: 0,

            area: 0,

            perimeter: 0,

            startTime: null,

            endTime: null,

            elapsedSeconds: 0,

            bestAccuracy: null,

            worstAccuracy: null,

            averageAccuracy: 0

        };


        console.log(
            "Polygon survey recorder reset."
        );

    }

}