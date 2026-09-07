/* ===========================================================
   DCGL FIELDMATE
   GPS ENGINE
   Enterprise GPS Module
   Version: 2.0

   PURPOSE
   -----------------------------------------------------------
   Single GPS engine for DCGL FieldMate.

   FEATURES
   -----------------------------------------------------------
   - Phone GPS location
   - High accuracy positioning
   - Continuous GPS watch
   - GPS quality monitoring
   - Accuracy statistics
   - Distance calculation
   - Survey point recording
   - GPS jitter protection
   - Survey pause / resume
   - GPS error handling
   - Immediate GPS fix
   - Callback notifications
   - Survey statistics
   - Compatible with PolygonRecorder
=========================================================== */


/* ===========================================================
   GPS ENGINE
=========================================================== */

class GpsEngine {

    constructor() {

        /* ---------------------------------------------------
           GPS WATCH
        --------------------------------------------------- */

        this.watchId = null;


        /* ---------------------------------------------------
           ENGINE STATE

           STOPPED
           SEARCHING
           READY
           RECORDING
           ERROR
        --------------------------------------------------- */

        this.state = "STOPPED";


        /* ---------------------------------------------------
           CURRENT GPS POSITION
        --------------------------------------------------- */

        this.current = null;


        /* ---------------------------------------------------
           RECORDED SURVEY POINTS
        --------------------------------------------------- */

        this.points = [];


        /* ---------------------------------------------------
           CALLBACKS
        --------------------------------------------------- */

        this.callbacks = [];


        /* ---------------------------------------------------
           GPS SETTINGS
        --------------------------------------------------- */

        this.settings = {

            enableHighAccuracy: true,

            timeout: 15000,

            maximumAge: 0,

            /*
             * Ignore GPS positions worse than this.
             *
             * 50 m is deliberately generous.
             * The survey can still operate when GPS accuracy
             * temporarily becomes poor.
             */

            maximumSurveyAccuracy: 50,

            /*
             * Minimum movement before another survey point
             * contributes to distance.
             *
             * This helps reduce GPS jitter.
             */

            minimumMovementMeters: 1

        };


        /* ---------------------------------------------------
           SURVEY STATISTICS
        --------------------------------------------------- */

        this.statistics = {

            startTime: null,

            elapsedSeconds: 0,

            distance: 0,

            bestAccuracy: null,

            worstAccuracy: null,

            averageAccuracy: 0,

            pointCount: 0

        };

    }


    /* =======================================================
       SUBSCRIBE TO GPS UPDATES
    ======================================================= */

    onUpdate(callback) {

        if (
            typeof callback !== "function"
        ) {

            console.warn(
                "GpsEngine.onUpdate(): callback must be a function."
            );

            return;

        }


        this.callbacks.push(callback);


        /*
         * Return unsubscribe function.
         */

        return () => {

            this.callbacks =
                this.callbacks.filter(
                    cb => cb !== callback
                );

        };

    }


    /* =======================================================
       NOTIFY LISTENERS
    ======================================================= */

    notify() {

        this.callbacks.forEach(callback => {

            try {

                callback(this);

            }

            catch (error) {

                console.error(
                    "GPS callback error:",
                    error
                );

            }

        });

    }


    /* =======================================================
       START GPS WATCH
    ======================================================= */

    start() {

        /* ---------------------------------------------------
           Browser support
        --------------------------------------------------- */

        if (
            !navigator.geolocation
        ) {

            this.state = "ERROR";

            this.notify();

            console.error(
                "DCGL FieldMate: Geolocation is not supported."
            );

            return false;

        }


        /* ---------------------------------------------------
           Already running
        --------------------------------------------------- */

        if (
            this.watchId !== null
        ) {

            console.log(
                "GPS watch is already running."
            );

            return true;

        }


        /* ---------------------------------------------------
           Searching
        --------------------------------------------------- */

        this.state = "SEARCHING";

        this.notify();


        console.log(
            "DCGL FieldMate GPS: starting..."
        );


        /* ---------------------------------------------------
           Start browser GPS watch
        --------------------------------------------------- */

        try {

            this.watchId =
                navigator.geolocation.watchPosition(

                    this.positionSuccess.bind(this),

                    this.positionError.bind(this),

                    {

                        enableHighAccuracy:
                            this.settings.enableHighAccuracy,

                        timeout:
                            this.settings.timeout,

                        maximumAge:
                            this.settings.maximumAge

                    }

                );


            return true;

        }

        catch (error) {

            console.error(
                "Unable to start GPS:",
                error
            );

            this.state = "ERROR";

            this.notify();

            return false;

        }

    }


    /* =======================================================
       STOP GPS WATCH
    ======================================================= */

    stop() {

        if (
            this.watchId !== null
        ) {

            navigator.geolocation.clearWatch(
                this.watchId
            );

            this.watchId = null;

        }


        this.state = "STOPPED";


        console.log(
            "DCGL FieldMate GPS stopped."
        );


        this.notify();

    }


    /* =======================================================
       REQUEST ONE IMMEDIATE GPS FIX

       Useful when opening the survey page before the
       continuous watch has produced a position.
    ======================================================= */

    getCurrentPosition() {

        return new Promise((resolve, reject) => {

            if (
                !navigator.geolocation
            ) {

                const error =
                    new Error(
                        "GPS is not supported by this browser."
                    );

                reject(error);

                return;

            }


            navigator.geolocation.getCurrentPosition(

                position => {

                    this.positionSuccess(
                        position
                    );

                    resolve(
                        this.current
                    );

                },

                error => {

                    this.positionError(
                        error
                    );

                    reject(error);

                },

                {

                    enableHighAccuracy:
                        this.settings.enableHighAccuracy,

                    timeout:
                        this.settings.timeout,

                    maximumAge:
                        this.settings.maximumAge

                }

            );

        });

    }


    /* =======================================================
       GPS POSITION SUCCESS
    ======================================================= */

    positionSuccess(position) {

        if (
            !position ||
            !position.coords
        ) {

            return;

        }


        const c =
            position.coords;


        /* ---------------------------------------------------
           Store current GPS position
        --------------------------------------------------- */

        this.current = {

            latitude:
                Number(c.latitude),

            longitude:
                Number(c.longitude),

            accuracy:
                Number(c.accuracy),

            altitude:
                c.altitude !== null
                    ? Number(c.altitude)
                    : null,

            altitudeAccuracy:
                c.altitudeAccuracy !== null
                    ? Number(c.altitudeAccuracy)
                    : null,

            heading:
                c.heading !== null
                    ? Number(c.heading)
                    : null,

            speed:
                c.speed !== null
                    ? Number(c.speed)
                    : null,

            timestamp:
                position.timestamp || Date.now()

        };


        /* ---------------------------------------------------
           Validate coordinates
        --------------------------------------------------- */

        if (
            !Number.isFinite(
                this.current.latitude
            ) ||

            !Number.isFinite(
                this.current.longitude
            )
        ) {

            console.warn(
                "Invalid GPS coordinates received."
            );

            return;

        }


        /* ---------------------------------------------------
           GPS SEARCH COMPLETE
        --------------------------------------------------- */

        if (
            this.state === "SEARCHING" ||

            this.state === "ERROR"
        ) {

            /*
             * Do not automatically change RECORDING.
             */

            if (
                this.state !== "RECORDING"
            ) {

                this.state = "READY";

            }


            if (
                !this.statistics.startTime
            ) {

                this.statistics.startTime =
                    Date.now();

            }

        }


        /* ---------------------------------------------------
           Accuracy statistics
        --------------------------------------------------- */

        this.updateAccuracyStatistics();


        /* ---------------------------------------------------
           Record survey point
        --------------------------------------------------- */

        if (
            this.state === "RECORDING"
        ) {

            this.recordPoint();

        }


        /* ---------------------------------------------------
           Update elapsed survey time
        --------------------------------------------------- */

        this.updateElapsedTime();


        /* ---------------------------------------------------
           Notify application
        --------------------------------------------------- */

        this.notify();

    }


    /* =======================================================
       GPS ERROR
    ======================================================= */

    positionError(error) {

        console.warn(
            "DCGL FieldMate GPS error:",
            error
        );


        /*
         * Error codes:
         *
         * 1 = Permission denied
         * 2 = Position unavailable
         * 3 = Timeout
         */

        if (
            error &&
            error.code === 1
        ) {

            console.error(
                "GPS permission was denied."
            );

        }

        else if (
            error &&
            error.code === 2
        ) {

            console.warn(
                "GPS position is currently unavailable."
            );

        }

        else if (
            error &&
            error.code === 3
        ) {

            console.warn(
                "GPS request timed out."
            );

        }


        /*
         * Do not destroy an active survey simply because
         * one GPS reading failed.
         */

        if (
            this.state !== "RECORDING"
        ) {

            this.state = "ERROR";

        }


        this.notify();

    }


    /* =======================================================
       START SURVEY RECORDING
    ======================================================= */

    startRecording() {

        /*
         * Make sure GPS is running.
         */

        if (
            this.watchId === null
        ) {

            this.start();

        }


        /* ---------------------------------------------------
           Reset survey points
        --------------------------------------------------- */

        this.points = [];


        /* ---------------------------------------------------
           Reset survey statistics
        --------------------------------------------------- */

        this.statistics = {

            startTime: Date.now(),

            elapsedSeconds: 0,

            distance: 0,

            bestAccuracy: null,

            worstAccuracy: null,

            averageAccuracy: 0,

            pointCount: 0

        };


        /* ---------------------------------------------------
           Start recording
        --------------------------------------------------- */

        this.state = "RECORDING";


        console.log(
            "DCGL FieldMate survey recording started."
        );


        this.notify();

    }


    /* =======================================================
       STOP SURVEY RECORDING
    ======================================================= */

    stopRecording() {

        if (
            this.state === "RECORDING"
        ) {

            this.updateElapsedTime();

        }


        /*
         * Keep GPS running so the user can still see
         * their location.
         */

        this.state = "READY";


        console.log(
            "DCGL FieldMate survey recording stopped."
        );


        this.notify();

    }


    /* =======================================================
       PAUSE SURVEY
    ======================================================= */

    pause() {

        if (
            this.state !== "RECORDING"
        ) {

            return;

        }


        this.updateElapsedTime();


        this.state = "READY";


        console.log(
            "DCGL FieldMate survey paused."
        );


        this.notify();

    }


    /* =======================================================
       RESUME SURVEY
    ======================================================= */

    resume() {

        if (
            this.state === "RECORDING"
        ) {

            return;

        }


        if (
            this.watchId === null
        ) {

            this.start();

        }


        this.state = "RECORDING";


        console.log(
            "DCGL FieldMate survey resumed."
        );


        this.notify();

    }


    /* =======================================================
       RECORD GPS POINT
    ======================================================= */

    recordPoint() {

        if (
            !this.current
        ) {

            return false;

        }


        const p = {

            latitude:
                this.current.latitude,

            longitude:
                this.current.longitude,

            accuracy:
                this.current.accuracy,

            altitude:
                this.current.altitude,

            heading:
                this.current.heading,

            speed:
                this.current.speed,

            timestamp:
                this.current.timestamp

        };


        /* ---------------------------------------------------
           Accuracy protection
        --------------------------------------------------- */

        if (
            Number.isFinite(
                p.accuracy
            ) &&

            p.accuracy >
            this.settings.maximumSurveyAccuracy
        ) {

            console.warn(

                "GPS point ignored because accuracy is " +

                p.accuracy.toFixed(1) +

                " m."

            );


            return false;

        }


        /* ---------------------------------------------------
           First point
        --------------------------------------------------- */

        if (
            this.points.length === 0
        ) {

            this.points.push(p);

            this.statistics.pointCount =
                this.points.length;

            this.recalculateAverageAccuracy();

            return true;

        }


        /* ---------------------------------------------------
           Previous point
        --------------------------------------------------- */

        const previous =
            this.points[
                this.points.length - 1
            ];


        /* ---------------------------------------------------
           Calculate movement
        --------------------------------------------------- */

        const distance =
            this.calculateDistance(

                previous.latitude,

                previous.longitude,

                p.latitude,

                p.longitude

            );


        /*
         * Ignore tiny movements caused by GPS jitter.
         */

        if (
            distance <
            this.settings.minimumMovementMeters
        ) {

            return false;

        }


        /* ---------------------------------------------------
           Add movement distance
        --------------------------------------------------- */

        this.statistics.distance +=
            distance;


        /* ---------------------------------------------------
           Save point
        --------------------------------------------------- */

        this.points.push(p);


        /* ---------------------------------------------------
           Update statistics
        --------------------------------------------------- */

        this.statistics.pointCount =
            this.points.length;


        this.recalculateAverageAccuracy();


        return true;

    }


    /* =======================================================
       UPDATE ACCURACY STATISTICS
    ======================================================= */

    updateAccuracyStatistics() {

        if (
            !this.current
        ) {

            return;

        }


        const accuracy =
            this.current.accuracy;


        if (
            !Number.isFinite(
                accuracy
            )
        ) {

            return;

        }


        if (
            this.statistics.bestAccuracy === null ||

            accuracy <
            this.statistics.bestAccuracy
        ) {

            this.statistics.bestAccuracy =
                accuracy;

        }


        if (
            this.statistics.worstAccuracy === null ||

            accuracy >
            this.statistics.worstAccuracy
        ) {

            this.statistics.worstAccuracy =
                accuracy;

        }

    }


    /* =======================================================
       RECALCULATE AVERAGE ACCURACY
    ======================================================= */

    recalculateAverageAccuracy() {

        if (
            this.points.length === 0
        ) {

            this.statistics.averageAccuracy =
                0;

            return;

        }


        const total =
            this.points.reduce(

                (sum, point) => {

                    return sum +
                        Number(
                            point.accuracy || 0
                        );

                },

                0

            );


        this.statistics.averageAccuracy =
            total /
            this.points.length;

    }


    /* =======================================================
       UPDATE ELAPSED TIME
    ======================================================= */

    updateElapsedTime() {

        if (
            !this.statistics.startTime
        ) {

            return;

        }


        this.statistics.elapsedSeconds =

            Math.floor(

                (
                    Date.now() -
                    this.statistics.startTime
                ) / 1000

            );

    }


    /* =======================================================
       HAVERSINE DISTANCE

       Returns meters.
    ======================================================= */

    calculateDistance(
        lat1,
        lon1,
        lat2,
        lon2
    ) {

        const R =
            6371000;


        const dLat =
            (
                lat2 -
                lat1
            ) *
            Math.PI /
            180;


        const dLon =
            (
                lon2 -
                lon1
            ) *
            Math.PI /
            180;


        const a =

            Math.sin(
                dLat / 2
            ) ** 2 +

            Math.cos(
                lat1 *
                Math.PI /
                180
            ) *

            Math.cos(
                lat2 *
                Math.PI /
                180
            ) *

            Math.sin(
                dLon / 2
            ) ** 2;


        return (

            R *

            2 *

            Math.atan2(

                Math.sqrt(a),

                Math.sqrt(
                    1 - a
                )

            )

        );

    }


    /* =======================================================
       GPS QUALITY
    ======================================================= */

    quality() {

        if (
            !this.current
        ) {

            return "Unknown";

        }


        const accuracy =
            this.current.accuracy;


        if (
            accuracy <= 2
        ) {

            return "★★★★★ Excellent";

        }


        if (
            accuracy <= 5
        ) {

            return "★★★★ Good";

        }


        if (
            accuracy <= 10
        ) {

            return "★★★ Fair";

        }


        if (
            accuracy <= 20
        ) {

            return "★★ Poor";

        }


        return "★ Very Poor";

    }


    /* =======================================================
       GPS QUALITY LEVEL

       Useful for CSS/UI logic.
    ======================================================= */

    qualityLevel() {

        if (
            !this.current
        ) {

            return "unknown";

        }


        const accuracy =
            this.current.accuracy;


        if (
            accuracy <= 2
        ) {

            return "excellent";

        }


        if (
            accuracy <= 5
        ) {

            return "good";

        }


        if (
            accuracy <= 10
        ) {

            return "fair";

        }


        if (
            accuracy <= 20
        ) {

            return "poor";

        }


        return "very-poor";

    }


    /* =======================================================
       IS GPS READY?
    ======================================================= */

    isReady() {

        return (

            this.current !== null &&

            this.state !== "STOPPED" &&

            this.state !== "ERROR"

        );

    }


    /* =======================================================
       IS RECORDING?
    ======================================================= */

    isRecording() {

        return (
            this.state === "RECORDING"
        );

    }


    /* =======================================================
       GET CURRENT POSITION
    ======================================================= */

    getPosition() {

        if (
            !this.current
        ) {

            return null;

        }


        return {
            ...this.current
        };

    }


    /* =======================================================
       GET SURVEY POINTS
    ======================================================= */

    getPoints() {

        return this.points.map(
            point => ({
                ...point
            })
        );

    }


    /* =======================================================
       GET SURVEY DISTANCE
    ======================================================= */

    getDistance() {

        return Number(
            this.statistics.distance || 0
        );

    }


    /* =======================================================
       GET SURVEY SUMMARY
    ======================================================= */

    getSummary() {

        this.updateElapsedTime();


        return {

            state:
                this.state,

            current:
                this.getPosition(),

            pointCount:
                this.statistics.pointCount,

            distanceMeters:
                this.statistics.distance,

            distanceKilometers:
                this.statistics.distance /
                1000,

            elapsedSeconds:
                this.statistics.elapsedSeconds,

            bestAccuracy:
                this.statistics.bestAccuracy,

            worstAccuracy:
                this.statistics.worstAccuracy,

            averageAccuracy:
                this.statistics.averageAccuracy,

            quality:
                this.quality(),

            qualityLevel:
                this.qualityLevel()

        };

    }


    /* =======================================================
       RESET SURVEY

       GPS watch remains active.
    ======================================================= */

    resetSurvey() {

        this.points = [];


        this.statistics = {

            startTime: null,

            elapsedSeconds: 0,

            distance: 0,

            bestAccuracy: null,

            worstAccuracy: null,

            averageAccuracy: 0,

            pointCount: 0

        };


        this.state =
            this.current
                ? "READY"
                : "STOPPED";


        console.log(
            "DCGL FieldMate survey data reset."
        );


        this.notify();

    }


    /* =======================================================
       DESTROY ENGINE

       Stops GPS and removes callbacks.
    ======================================================= */

    destroy() {

        this.stop();


        this.callbacks = [];


        this.current = null;

        this.points = [];


        this.statistics = {

            startTime: null,

            elapsedSeconds: 0,

            distance: 0,

            bestAccuracy: null,

            worstAccuracy: null,

            averageAccuracy: 0,

            pointCount: 0

        };


        console.log(
            "DCGL FieldMate GPS engine destroyed."
        );

    }

}


/* ===========================================================
   OPTIONAL GLOBAL INSTANCE
   -----------------------------------------------------------
   This allows the rest of FieldMate to use:

       gpsEngine.start()
       gpsEngine.startRecording()
       gpsEngine.stopRecording()

   without creating multiple GPS engines.
=========================================================== */

if (
    typeof window !== "undefined"
) {

    if (
        !window.gpsEngine
    ) {

        window.gpsEngine =
            new GpsEngine();

    }

}