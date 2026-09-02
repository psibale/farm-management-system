/* ==========================================================
   DCGL FIELDMATE
   Progressive Web App
   Service Worker
   Version 6.0

   OFFLINE-FIRST FIELD SURVEY APPLICATION

   Features
   ----------------------------------------------------------
   - FieldMate application shell
   - Offline FieldMate navigation
   - Cache successful FieldMate pages
   - Cache FieldMate JavaScript
   - Cache FieldMate CSS
   - Cache images/icons
   - Cache GET API data
   - Network first while connected
   - Cache fallback while offline
   - Never intercept POST requests
   - Never cache redirects
   - Never cache failed responses
   - Never cache login page
   - Never redirect offline requests to login
   - Offline survey details
   - Offline survey configuration
   - Automatic cache upgrade
========================================================== */


/* ==========================================================
   VERSION
========================================================== */

const CACHE_NAME =
    "dcgl-fieldmate-v6";


/* ==========================================================
   FIELD MATE ROOT
========================================================== */

const FIELDMATE_ROOT =
    "/mobile/";


/* ==========================================================
   FIELD MATE API CACHE
========================================================== */

const API_CACHE_NAME =
    "dcgl-fieldmate-api-v1";


/* ==========================================================
   APPLICATION PAGES
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
   STATIC FILES
========================================================== */

const STATIC_FILES = [

    "/static/mobile/manifest.json",

    "/static/mobile/icons/icon-192.png",

    "/static/mobile/icons/icon-512.png",

    "/static/mobile/css/mobile.css",

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
            "DCGL FieldMate Service Worker v6 installing..."
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
            "DCGL FieldMate Service Worker v6 activated."
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
                                        CACHE_NAME &&

                                        cacheName !==
                                        API_CACHE_NAME

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
             * POST requests continue directly
             * to Flask.
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

            if (

                url.pathname ===
                FIELDMATE_ROOT ||

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
           FIELD MATE API
        ====================================================== */

        if (
            isFieldMateAPI(
                url
            )
        ) {

            event.respondWith(

                fieldMateAPI(
                    request
                )

            );


            return;

        }


        /* ======================================================
           FIELD MATE STATIC
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
   IDENTIFY FIELDMATE API REQUESTS
========================================================== */

function isFieldMateAPI(url) {

    return (

        url.pathname ===
        "/mobile/survey_data"

        ||

        url.pathname.startsWith(
            "/mobile/next_subfield/"
        )

    );

}


/* ==========================================================
   FIELDMATE API HANDLER
========================================================== */

async function fieldMateAPI(
    request
) {

    console.log(
        "FieldMate API request:",
        request.url
    );


    const apiCache =
        await caches.open(
            API_CACHE_NAME
        );


    /* ======================================================
       ONLINE
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
           NEVER CACHE REDIRECTS
        ================================================== */

        if (
            response.redirected
        ) {

            console.log(

                "FieldMate API followed redirect:",

                request.url,

                "→",

                response.url

            );


            return response;

        }


        /* ==================================================
           CACHE SUCCESSFUL API RESPONSE
        ================================================== */

        if (

            response.ok &&

            response.status === 200

        ) {

            await apiCache.put(

                request,

                response.clone()

            );


            console.log(
                "FieldMate API cached:",
                request.url
            );


            return response;

        }


        /* ==================================================
           SERVER ERROR
        ================================================== */

        console.warn(

            "FieldMate API returned:",
            response.status

        );


        const cached =
            await apiCache.match(
                request
            );


        if (
            cached
        ) {

            console.log(
                "Using cached API response:",
                request.url
            );


            return cached;

        }


        return response;

    }


    /* ======================================================
       OFFLINE
    ====================================================== */

    catch (error) {

        console.warn(

            "FieldMate API offline:",
            request.url

        );


        const cached =
            await apiCache.match(
                request
            );


        if (
            cached
        ) {

            console.log(

                "=================================================="

            );

            console.log(

                "OFFLINE API CACHE HIT:",
                request.url

            );

            console.log(

                "=================================================="

            );


            return cached;

        }


        console.warn(

            "OFFLINE API DATA NOT CACHED:",
            request.url

        );


        return new Response(

            JSON.stringify({

                offline:
                    true,

                error:
                    "This FieldMate data has not yet been cached."

            }),

            {

                status:
                    503,

                headers: {

                    "Content-Type":
                        "application/json"

                }

            }

        );

    }

}


/* ==========================================================
   FIELDMATE NAVIGATION
========================================================== */

async function fieldMateNavigation(
    request
) {

    console.log(
        "FieldMate navigation:",
        request.url
    );


    const requestURL =
        new URL(
            request.url
        );


    /* ======================================================
       LOGIN
    ====================================================== */

    if (
        requestURL.pathname ===
        "/mobile/login"
    ) {

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
                "FieldMate login unavailable offline."
            );


            return offlineLoginResponse();

        }

    }


    /* ======================================================
       NETWORK FIRST
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
           NEVER CACHE REDIRECTS
        ================================================== */

        if (
            response.redirected
        ) {

            console.log(

                "FieldMate navigation followed redirect:",

                request.url,

                "→",

                response.url

            );


            return response;

        }


        /* ==================================================
           CACHE SUCCESSFUL PAGE
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


        const cached =
            await caches.match(
                request
            );


        if (
            cached
        ) {

            return cached;

        }


        return response;

    }


    /* ======================================================
       OFFLINE
    ====================================================== */

    catch (error) {

        console.warn(

            "FieldMate network unavailable:",
            request.url

        );


        const cached =
            await caches.match(
                request
            );


        if (
            cached
        ) {

            console.log(

                "OFFLINE: Serving cached FieldMate page:",
                request.url

            );


            return cached;

        }


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

    const cached =
        await caches.match(
            request
        );


    if (
        cached
    ) {

        return cached;

    }


    try {

        const response =
            await fetch(

                request,

                {
                    redirect:
                        "follow"
                }

            );


        if (
            response.redirected
        ) {

            console.warn(
                "FieldMate static redirect not cached:",
                request.url
            );


            return response;

        }


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

        }


        return response;

    }


    catch (error) {

        console.warn(

            "FieldMate static resource unavailable:",
            request.url

        );


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
   OFFLINE PAGE
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
   OFFLINE LOGIN
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

            <title>
                DCGL FieldMate
            </title>

        </head>

        <body
            style="
                margin:0;
                padding:30px;
                text-align:center;
                font-family:Arial,sans-serif;
            "
        >

            <h2>
                📱 DCGL FieldMate
            </h2>

            <p>
                FieldMate login requires a connection
                to the DCGL server.
            </p>

            <p>
                Reconnect to the DCGL LAN to log in.
            </p>

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