/* ==========================================================
   DCGL FIELDMATE
   Progressive Web App
   Service Worker
   Version 5.0

   OFFLINE-FIRST FIELD SURVEY APPLICATION

   FEATURES
   ----------------------------------------------------------
   - FieldMate application shell
   - Offline FieldMate navigation
   - Cache successful FieldMate pages
   - Cache FieldMate JavaScript
   - Cache FieldMate CSS
   - Cache images/icons
   - Network first while connected
   - Cache fallback while offline
   - Never intercept POST requests
   - Never cache redirects
   - Never cache failed responses
   - Never cache login page
   - Never redirect offline requests to login
   - Automatic cache upgrade
   - Safe Flask authentication handling
========================================================== */


/* ==========================================================
   VERSION
========================================================== */

const CACHE_NAME =
    "dcgl-fieldmate-v5";


/* ==========================================================
   FIELD MATE ROOT
========================================================== */

const FIELDMATE_ROOT =
    "/mobile/";


/* ==========================================================
   FIELD MATE APPLICATION PAGES
========================================================== */

const APPLICATION_PAGES = [

    "/mobile/",

    "/mobile/home",

    "/mobile/survey",

    "/mobile/inspection",

    "/mobile/sync",

    "/mobile/survey_details",

    "/mobile/survey_review"

];


/* ==========================================================
   FIELD MATE STATIC FILES
========================================================== */

const STATIC_FILES = [

    /* ------------------------------------------------------
       Manifest
    ------------------------------------------------------ */

    "/static/mobile/manifest.json",


    /* ------------------------------------------------------
       Icons
    ------------------------------------------------------ */

    "/static/mobile/icons/icon-192.png",

    "/static/mobile/icons/icon-512.png",


    /* ------------------------------------------------------
       CSS
    ------------------------------------------------------ */

    "/static/mobile/css/mobile.css",


    /* ------------------------------------------------------
       Offline / Application JavaScript
    ------------------------------------------------------ */

    "/static/mobile/js/offline_db.js",

    "/static/mobile/js/offline_sync.js",

    "/static/mobile/js/offline_status.js",

    "/static/mobile/js/survey_offline.js",

    "/static/mobile/js/gps_engine.js",

    "/static/mobile/js/gps.js",

    "/static/mobile/js/polygon.js",

    "/static/mobile/js/area.js",

    "/static/mobile/js/measurements.js",

    "/static/mobile/js/survey_validator.js",

    "/static/mobile/js/survey_ui.js",

    "/static/mobile/js/survey_save.js",

    "/static/mobile/js/survey.js",

    "/static/mobile/js/photos.js",

    "/static/mobile/js/utils.js",

    "/static/mobile/js/survey_details.js",

    "/static/mobile/js/survey_review.js"

];


/* ==========================================================
   INSTALL
========================================================== */

self.addEventListener(

    "install",

    function(event) {

        console.log(
            "=================================================="
        );

        console.log(
            "DCGL FieldMate Service Worker v5 installing..."
        );

        console.log(
            "=================================================="
        );


        event.waitUntil(

            caches.open(
                CACHE_NAME
            )

            .then(

                async function(cache) {

                    console.log(
                        "Preparing FieldMate static cache..."
                    );


                    /* ------------------------------------------------
                       Cache static resources individually.

                       We intentionally do NOT use cache.addAll()
                       because one missing file should not cause the
                       entire installation to fail.
                    ------------------------------------------------ */

                    for (
                        const file of STATIC_FILES
                    ) {

                        try {

                            const response =
                                await fetch(

                                    file,

                                    {
                                        cache:
                                            "no-cache",

                                        redirect:
                                            "follow"
                                    }

                                );


                            /* ----------------------------------------
                               Only cache genuine HTTP 200 responses.
                            ---------------------------------------- */

                            if (

                                response.ok &&

                                response.status === 200 &&

                                !response.redirected

                            ) {

                                await cache.put(

                                    file,

                                    response.clone()

                                );


                                console.log(
                                    "FieldMate static cached:",
                                    file
                                );

                            }

                            else {

                                console.warn(

                                    "FieldMate static file "
                                    + "not cached:",

                                    file,

                                    response.status

                                );

                            }

                        }

                        catch (error) {

                            console.warn(

                                "FieldMate static file "
                                + "unavailable during install:",

                                file

                            );

                        }

                    }


                    console.log(
                        "FieldMate static cache preparation complete."
                    );

                }

            )

            .catch(

                function(error) {

                    console.error(

                        "FieldMate Service Worker "
                        + "installation error:",

                        error

                    );

                }

            )

        );


        /* ------------------------------------------------------
           Activate this Service Worker immediately.
        ------------------------------------------------------ */

        self.skipWaiting();

    }

);


/* ==========================================================
   ACTIVATE
========================================================== */

self.addEventListener(

    "activate",

    function(event) {

        console.log(
            "=================================================="
        );

        console.log(
            "DCGL FieldMate Service Worker v5 activated."
        );

        console.log(
            "=================================================="
        );


        event.waitUntil(

            caches.keys()

            .then(

                function(cacheNames) {

                    return Promise.all(

                        cacheNames

                            .filter(

                                function(cacheName) {

                                    return (

                                        cacheName !==
                                        CACHE_NAME

                                    );

                                }

                            )

                            .map(

                                function(cacheName) {

                                    console.log(

                                        "Removing old "
                                        + "FieldMate cache:",

                                        cacheName

                                    );


                                    return caches.delete(

                                        cacheName

                                    );

                                }

                            )

                    );

                }

            )

            .then(

                function() {

                    return self.clients.claim();

                }

            )

        );

    }

);


/* ==========================================================
   FETCH
========================================================== */

self.addEventListener(

    "fetch",

    function(event) {

        const request =
            event.request;


        /* ======================================================
           ONLY GET REQUESTS
        ====================================================== */

        if (
            request.method !== "GET"
        ) {

            /*
             * POST requests such as:
             *
             * /mobile/save_survey
             *
             * are allowed to go directly to Flask.
             */

            return;

        }


        const url =
            new URL(
                request.url
            );


        /* ======================================================
           SAME ORIGIN ONLY
        ====================================================== */

        if (
            url.origin !==
            self.location.origin
        ) {

            return;

        }


        /* ======================================================
           NAVIGATION
        ====================================================== */

        if (
            request.mode ===
            "navigate"
        ) {

            /*
             * Only control FieldMate navigation.
             */

            if (
                url.pathname === FIELDMATE_ROOT ||

                url.pathname.startsWith(
                    "/mobile/"
                )

            ) {

                event.respondWith(

                    fieldMateNavigation(
                        request
                    )

                );

            }


            return;

        }


        /* ======================================================
           FIELD MATE STATIC FILE
        ====================================================== */

        if (
            url.pathname.startsWith(
                "/static/mobile/"
            )
        ) {

            event.respondWith(

                fieldMateStatic(
                    request
                )

            );


            return;

        }

    }

);


/* ==========================================================
   FIELDMATE NAVIGATION
========================================================== */

async function fieldMateNavigation(
    request
) {

    console.log(
        "=================================================="
    );

    console.log(
        "FieldMate navigation:",
        request.url
    );

    console.log(
        "=================================================="
    );


    /* ======================================================
       IMPORTANT: LOGIN PAGE
    ====================================================== */

    const requestURL =
        new URL(
            request.url
        );


    if (
        requestURL.pathname ===
        "/mobile/login"
    ) {

        /*
         * Login MUST always be handled by Flask while online.
         *
         * We do NOT cache the login page.
         *
         * This prevents an old authentication page from
         * interfering with FieldMate authentication.
         */

        try {

            const response =
                await fetch(

                    new Request(

                        request,

                        {
                            redirect:
                                "follow"
                        }

                    )

                );


            return response;

        }

        catch (error) {

            console.warn(
                "FieldMate login unavailable while offline."
            );


            return offlineLoginResponse();

        }

    }


    /* ======================================================
       ONLINE / NETWORK FIRST
    ====================================================== */

    try {

        const networkRequest =
            new Request(

                request,

                {
                    redirect:
                        "follow"
                }

            );


        const response =
            await fetch(
                networkRequest
            );


        /* ==================================================
           REDIRECT RESPONSE
        ================================================== */

        if (
            response.redirected
        ) {

            console.log(

                "FieldMate navigation followed "
                + "redirect:",

                request.url,

                "→",

                response.url

            );


            /*
             * IMPORTANT:
             *
             * Do not cache redirected responses.
             */

            return response;

        }


        /* ==================================================
           SUCCESSFUL PAGE
        ================================================== */

        if (

            response.ok &&

            response.status === 200

        ) {

            const cache =
                await caches.open(
                    CACHE_NAME
                );


            /*
             * Cache the successful final page.
             */

            await cache.put(

                request,

                response.clone()

            );


            console.log(
                "FieldMate page cached:",
                request.url
            );


            return response;

        }


        /* ==================================================
           SERVER ERROR
        ================================================== */

        console.warn(

            "FieldMate navigation returned:",
            response.status

        );


        /* --------------------------------------------------
           Try exact cached page.
        -------------------------------------------------- */

        const cached =
            await caches.match(
                request
            );


        if (
            cached
        ) {

            console.log(

                "Using cached FieldMate page:",
                request.url

            );


            return cached;

        }


        return response;

    }


    catch (error) {

        console.warn(

            "FieldMate network unavailable:",
            request.url

        );


        /* ==================================================
           OFFLINE
        ================================================== */

        const cached =
            await caches.match(
                request
            );


        if (
            cached
        ) {

            console.log(

                "=================================================="

            );

            console.log(

                "OFFLINE: Serving cached FieldMate page:",
                request.url

            );

            console.log(

                "=================================================="

            );


            return cached;

        }


        /* ==================================================
           PAGE NOT CACHED
        ================================================== */

        console.warn(

            "OFFLINE: FieldMate page has not "
            + "been cached yet:",

            request.url

        );


        /*
         * IMPORTANT:
         *
         * Do NOT automatically return /mobile/.
         *
         * Otherwise the user could request:
         *
         * /mobile/survey_details
         *
         * and unexpectedly receive:
         *
         * /mobile/
         *
         * while offline.
         */


        return offlinePageNotCached(
            request.url
        );

    }

}


/* ==========================================================
   STATIC FILE HANDLER
========================================================== */

async function fieldMateStatic(
    request
) {

    /* ======================================================
       CACHE FIRST
    ====================================================== */

    const cached =
        await caches.match(
            request
        );


    if (
        cached
    ) {

        return cached;

    }


    /* ======================================================
       NETWORK
    ====================================================== */

    try {

        const response =
            await fetch(

                request,

                {
                    redirect:
                        "follow"
                }

            );


        /* ==================================================
           NEVER CACHE REDIRECTS
        ================================================== */

        if (
            response.redirected
        ) {

            console.warn(

                "FieldMate static redirect not cached:",

                request.url

            );


            return response;

        }


        /* ==================================================
           CACHE ONLY 200
        ================================================== */

        if (

            response.ok &&

            response.status === 200

        ) {

            const cache =
                await caches.open(
                    CACHE_NAME
                );


            await cache.put(

                request,

                response.clone()

            );


            console.log(

                "FieldMate static cached:",
                request.url

            );

        }


        return response;

    }


    catch (error) {

        console.warn(

            "FieldMate static resource unavailable:",

            request.url

        );


        /* ==================================================
           SECOND CACHE CHECK
        ================================================== */

        const cached =
            await caches.match(
                request
            );


        if (
            cached
        ) {

            return cached;

        }


        return new Response(

            "",

            {

                status:
                    503,

                statusText:
                    "FieldMate resource unavailable."

            }

        );

    }

}


/* ==========================================================
   OFFLINE PAGE NOT CACHED
========================================================== */

function offlinePageNotCached(
    requestedURL
) {

    return new Response(

        `
        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1"
            >

            <meta
                name="theme-color"
                content="#198754"
            >

            <title>
                DCGL FieldMate - Offline
            </title>

        </head>


        <body
            style="
                margin:0;
                padding:30px;
                background:#f5f7fa;
                font-family:Arial,sans-serif;
                text-align:center;
            "
        >

            <div
                style="
                    max-width:420px;
                    margin:auto;
                    background:white;
                    padding:30px;
                    border-radius:20px;
                    box-shadow:0 5px 20px rgba(0,0,0,.15);
                "
            >

                <div
                    style="
                        font-size:55px;
                        margin-bottom:15px;
                    "
                >
                    📱
                </div>


                <h2>
                    DCGL FieldMate
                </h2>


                <h3>
                    You are offline
                </h3>


                <p>
                    This FieldMate page has not yet been
                    saved on this phone.
                </p>


                <p>
                    Connect to the DCGL LAN once to load
                    this page before working offline.
                </p>


                <button
                    onclick="location.reload()"
                    style="
                        border:0;
                        background:#198754;
                        color:white;
                        padding:12px 22px;
                        border-radius:10px;
                        font-weight:bold;
                        margin-top:10px;
                    "
                >
                    Try Again
                </button>

            </div>

        </body>

        </html>
        `,

        {

            status:
                503,

            headers: {

                "Content-Type":
                    "text/html; charset=utf-8"

            }

        }

    );

}


/* ==========================================================
   OFFLINE LOGIN RESPONSE
========================================================== */

function offlineLoginResponse() {

    return new Response(

        `
        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1"
            >

            <meta
                name="theme-color"
                content="#198754"
            >

            <title>
                DCGL FieldMate
            </title>

        </head>


        <body
            style="
                margin:0;
                padding:30px;
                background:#f5f7fa;
                font-family:Arial,sans-serif;
                text-align:center;
            "
        >

            <div
                style="
                    max-width:420px;
                    margin:auto;
                    background:white;
                    padding:30px;
                    border-radius:20px;
                    box-shadow:0 5px 20px rgba(0,0,0,.15);
                "
            >

                <div
                    style="
                        font-size:55px;
                        margin-bottom:15px;
                    "
                >
                    📱
                </div>


                <h2>
                    DCGL FieldMate
                </h2>


                <p>
                    FieldMate login requires a connection
                    to the DCGL server.
                </p>


                <p>
                    Once logged in, FieldMate pages that
                    have already been cached can be used
                    offline.
                </p>

            </div>

        </body>

        </html>
        `,

        {

            status:
                503,

            headers: {

                "Content-Type":
                    "text/html; charset=utf-8"

            }

        }

    );

}


/* ==========================================================
   SERVICE WORKER MESSAGE
========================================================== */

self.addEventListener(

    "message",

    function(event) {

        if (

            event.data &&

            event.data.type ===
            "SKIP_WAITING"

        ) {

            console.log(
                "FieldMate requested Service Worker update."
            );


            self.skipWaiting();

        }

    }

);