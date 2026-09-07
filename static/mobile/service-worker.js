/* ==========================================================
   DCGL FIELDMATE
   Progressive Web App
   Service Worker
   Version 9.0

   OFFLINE-FIRST FIELD SURVEY APPLICATION

   FEATURES
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
   - Never cache logout page
   - Never cache authentication redirects
   - Never redirect offline requests to login
   - Offline survey details
   - Offline survey configuration
   - Offline parent-field information
   - Query-string tolerant survey navigation
   - GPS Engine support
   - Polygon survey support
   - Area calculation support
   - Automatic cache upgrade
========================================================== */


/* ==========================================================
   VERSION
========================================================== */

const CACHE_NAME =
    "dcgl-fieldmate-v9";


/* ==========================================================
   API CACHE
========================================================== */

const API_CACHE_NAME =
    "dcgl-fieldmate-api-v4";


/* ==========================================================
   FIELDMATE ROOT
========================================================== */

const FIELDMATE_ROOT =
    "/mobile/";


/* ==========================================================
   AUTHENTICATION
========================================================== */

const LOGIN_PATH =
    "/mobile/login";

const LOGOUT_PATH =
    "/mobile/logout";


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

    /* ------------------------------------------------------
       PWA
    ------------------------------------------------------ */

    "/static/mobile/manifest.json",

    "/static/mobile/icons/icon-192.png",

    "/static/mobile/icons/icon-512.png",


    /* ------------------------------------------------------
       CSS
    ------------------------------------------------------ */

    "/static/mobile/css/mobile.css",


    /* ------------------------------------------------------
       OFFLINE / DATABASE
    ------------------------------------------------------ */

    "/static/mobile/js/offline_db.js",

    "/static/mobile/js/offline_sync.js",

    "/static/mobile/js/offline_status.js",

    "/static/mobile/js/survey_offline.js",


    /* ------------------------------------------------------
       GPS / SURVEY ENGINE
    ------------------------------------------------------ */

    "/static/mobile/js/gps_engine.js",

    "/static/mobile/js/polygon.js",

    "/static/mobile/js/area.js",

    "/static/mobile/js/measurements.js",


    /* ------------------------------------------------------
       SURVEY VALIDATION / UI
    ------------------------------------------------------ */

    "/static/mobile/js/survey_validator.js",

    "/static/mobile/js/survey_ui.js",

    "/static/mobile/js/survey_save.js",

    "/static/mobile/js/survey.js",


    /* ------------------------------------------------------
       SUPPORTING MODULES
    ------------------------------------------------------ */

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
            "DCGL FieldMate Service Worker v9 installing..."
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
                        "Preparing FieldMate v9 cache..."
                    );


                    /* ==================================================
                       PREPARE APPLICATION PAGES
                    ================================================== */

                    for (
                        const page of APPLICATION_PAGES
                    ) {

                        try {

                            /* ------------------------------------------
                               NEVER CACHE LOGIN
                            ------------------------------------------ */

                            if (
                                page === LOGIN_PATH
                            ) {

                                continue;

                            }


                            /* ------------------------------------------
                               NEVER CACHE LOGOUT
                            ------------------------------------------ */

                            if (
                                page === LOGOUT_PATH
                            ) {

                                continue;

                            }


                            const response =
                                await fetch(

                                    new Request(

                                        page,

                                        {

                                            method:
                                                "GET",

                                            cache:
                                                "no-cache",

                                            redirect:
                                                "follow"

                                        }

                                    )

                                );


                            /* ------------------------------------------
                               NEVER CACHE REDIRECTS
                            ------------------------------------------ */

                            if (
                                response.redirected
                            ) {

                                console.warn(

                                    "FieldMate page followed " +
                                    "redirect and was not cached:",

                                    page,

                                    "→",

                                    response.url

                                );

                                continue;

                            }


                            /* ------------------------------------------
                               NEVER CACHE LOGIN RESPONSE
                            ------------------------------------------ */

                            if (

                                response.url &&

                                new URL(
                                    response.url
                                ).pathname === LOGIN_PATH

                            ) {

                                console.warn(

                                    "Authentication page not cached:",

                                    page

                                );

                                continue;

                            }


                            /* ------------------------------------------
                               ONLY CACHE HTTP 200
                            ------------------------------------------ */

                            if (

                                response.ok &&

                                response.status === 200

                            ) {

                                await cache.put(

                                    page,

                                    response.clone()

                                );


                                console.log(

                                    "FieldMate application page cached:",
                                    page

                                );


                                /*
                                 * The survey page is commonly opened
                                 * with query parameters.
                                 *
                                 * Example:
                                 *
                                 * /mobile/survey?field=DG01000
                                 *
                                 * Store the base survey page as well.
                                 */

                                if (
                                    shouldCacheBaseNavigation(
                                        new URL(page).pathname
                                    )
                                ) {

                                    const baseURL =
                                        new URL(
                                            page,
                                            self.location.origin
                                        );


                                    baseURL.search = "";
                                    baseURL.hash = "";


                                    await cache.put(

                                        baseURL.pathname,

                                        response.clone()

                                    );


                                    console.log(

                                        "Base FieldMate page cached:",
                                        baseURL.pathname

                                    );

                                }

                            }

                            else {

                                console.warn(

                                    "FieldMate page not cached:",
                                    page,
                                    response.status

                                );

                            }

                        }

                        catch (error) {

                            console.warn(

                                "FieldMate page unavailable " +
                                "during installation:",

                                page,

                                error

                            );

                        }

                    }


                    /* ==================================================
                       STATIC FILES
                    ================================================== */

                    for (
                        const file of STATIC_FILES
                    ) {

                        try {

                            const response =
                                await fetch(

                                    new Request(

                                        file,

                                        {

                                            method:
                                                "GET",

                                            cache:
                                                "no-cache",

                                            redirect:
                                                "follow"

                                        }

                                    )

                                );


                            /* ------------------------------------------
                               NEVER CACHE REDIRECTS
                            ------------------------------------------ */

                            if (
                                response.redirected
                            ) {

                                console.warn(

                                    "Static resource followed " +
                                    "redirect and was not cached:",

                                    file,

                                    "→",

                                    response.url

                                );

                                continue;

                            }


                            /* ------------------------------------------
                               CACHE SUCCESSFUL FILES
                            ------------------------------------------ */

                            if (

                                response.ok &&

                                response.status === 200

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

                                    "FieldMate static file not cached:",
                                    file,
                                    response.status

                                );

                            }

                        }

                        catch (error) {

                            console.warn(

                                "FieldMate static file unavailable " +
                                "during install:",

                                file,

                                error

                            );

                        }

                    }


                    console.log(
                        "=================================================="
                    );

                    console.log(
                        "FieldMate v9 cache preparation complete."
                    );

                    console.log(
                        "=================================================="
                    );

                }

            )

            .catch(

                function(error) {

                    console.error(

                        "FieldMate Service Worker " +
                        "installation error:",

                        error

                    );

                }

            )

        );


        /* ------------------------------------------------------
           Activate immediately
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
            "DCGL FieldMate Service Worker v9 activated."
        );

        console.log(
            "=================================================="
        );


        event.waitUntil(

            caches.keys()

            .then(

                function(cacheNames) {

                    return Promise.all(

                        cacheNames.map(

                            function(cacheName) {

                                /* --------------------------------------
                                   REMOVE OLD APPLICATION CACHE
                                -------------------------------------- */

                                if (

                                    cacheName.startsWith(
                                        "dcgl-fieldmate-v"
                                    )

                                    &&

                                    cacheName !==
                                    CACHE_NAME

                                ) {

                                    console.log(

                                        "Removing old " +
                                        "FieldMate cache:",

                                        cacheName

                                    );


                                    return caches.delete(
                                        cacheName
                                    );

                                }


                                /* --------------------------------------
                                   REMOVE OLD API CACHE
                                -------------------------------------- */

                                if (

                                    cacheName.startsWith(
                                        "dcgl-fieldmate-api-v"
                                    )

                                    &&

                                    cacheName !==
                                    API_CACHE_NAME

                                ) {

                                    console.log(

                                        "Removing old " +
                                        "FieldMate API cache:",

                                        cacheName

                                    );


                                    return caches.delete(
                                        cacheName
                                    );

                                }


                                return Promise.resolve(
                                    false
                                );

                            }

                        )

                    );

                }

            )

            .then(

                function() {

                    console.log(
                        "FieldMate old caches removed."
                    );


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
             * POST /mobile/save_survey
             *
             * continues directly to Flask.
             */

            return;

        }


        /* ======================================================
           URL
        ====================================================== */

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
           NEVER INTERCEPT LOGOUT
        ====================================================== */

        if (
            url.pathname === LOGOUT_PATH
        ) {

            return;

        }


        /* ======================================================
           NAVIGATION
        ====================================================== */

        if (
            request.mode === "navigate"
        ) {

            if (
                url.pathname === FIELDMATE_ROOT

                ||

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
           FIELDMATE API
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
           FIELDMATE STATIC
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
   APPLICATION PAGE HELPERS
========================================================== */

function shouldCacheBaseNavigation(
    pathname
) {

    return (

        pathname ===
        "/mobile/survey"

        ||

        pathname ===
        "/mobile/survey_details"

        ||

        pathname ===
        "/mobile/survey_review"

        ||

        pathname ===
        "/mobile/inspection"

        ||

        pathname ===
        "/mobile/sync"

    );

}


/* ==========================================================
   BUILD BASE NAVIGATION URL
========================================================== */

function getBaseNavigationURL(
    request
) {

    const url =
        new URL(
            request.url
        );


    url.search = "";
    url.hash = "";


    return url;

}


/* ==========================================================
   IDENTIFY FIELDMATE API
========================================================== */

function isFieldMateAPI(
    url
) {

    return (

        url.pathname ===
        "/mobile/survey_data"

        ||

        url.pathname.startsWith(
            "/mobile/next_subfield/"
        )

        ||

        url.pathname.startsWith(
            "/mobile/parent_area/"
        )

    );

}


/* ==========================================================
   BUILD API CACHE KEY
========================================================== */

function getAPICacheKeys(
    request
) {

    const keys = [

        request

    ];


    const url =
        new URL(
            request.url
        );


    /*
     * Some API calls may contain harmless query strings.
     *
     * We first try the exact request.
     */

    if (
        url.search
    ) {

        const baseURL =
            new URL(
                request.url
            );


        baseURL.search = "";
        baseURL.hash = "";


        keys.push(

            new Request(
                baseURL.toString(),
                {
                    method:
                        "GET"
                }
            )

        );

    }


    return keys;

}


/* ==========================================================
   FIND API CACHE
========================================================== */

async function findAPICache(
    apiCache,
    request
) {

    const keys =
        getAPICacheKeys(
            request
        );


    for (
        const key of keys
    ) {

        const cached =
            await apiCache.match(
                key
            );


        if (
            cached
        ) {

            return cached;

        }

    }


    return null;

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

                "FieldMate API followed redirect:",

                request.url,

                "→",

                response.url

            );


            return response;

        }


        /* ==================================================
           NEVER CACHE LOGIN
        ================================================== */

        if (

            response.url &&

            new URL(
                response.url
            ).pathname === LOGIN_PATH

        ) {

            console.log(

                "FieldMate API authentication redirect:",
                request.url

            );


            return response;

        }


        /* ==================================================
           CACHE SUCCESSFUL RESPONSE
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


            /*
             * Also cache a base version where query strings
             * are present.
             */

            const url =
                new URL(
                    request.url
                );


            if (
                url.search
            ) {

                url.search = "";
                url.hash = "";


                await apiCache.put(

                    new Request(
                        url.toString(),
                        {
                            method:
                                "GET"
                        }
                    ),

                    response.clone()

                );

            }


            return response;

        }


        /* ==================================================
           SERVER ERROR — TRY CACHE
        ================================================== */

        console.warn(

            "FieldMate API returned:",
            response.status

        );


        const cached =
            await findAPICache(
                apiCache,
                request
            );


        if (
            cached
        ) {

            console.log(

                "Using cached FieldMate API:",
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
            await findAPICache(
                apiCache,
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

                success:
                    false,

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
        requestURL.pathname === LOGIN_PATH
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
           NEVER CACHE LOGIN
        ================================================== */

        if (

            response.url &&

            new URL(
                response.url
            ).pathname === LOGIN_PATH

        ) {

            console.log(

                "FieldMate authentication page not cached:",

                request.url

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


            /* ----------------------------------------------
               CACHE EXACT REQUEST
            ---------------------------------------------- */

            await cache.put(

                request,

                response.clone()

            );


            console.log(

                "FieldMate page cached:",
                request.url

            );


            /* ----------------------------------------------
               CACHE BASE PAGE
            ---------------------------------------------- */

            if (
                shouldCacheBaseNavigation(
                    requestURL.pathname
                )
            ) {

                const baseURL =
                    getBaseNavigationURL(
                        request
                    );


                await cache.put(

                    baseURL.pathname,

                    response.clone()

                );


                console.log(

                    "FieldMate base page cached:",
                    baseURL.pathname

                );

            }


            return response;

        }


        /* ==================================================
           SERVER ERROR — CACHE FALLBACK
        ================================================== */

        console.warn(

            "FieldMate navigation returned:",
            response.status

        );


        const cached =
            await findNavigationCache(
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


    /* ======================================================
       OFFLINE
    ====================================================== */

    catch (error) {

        console.warn(

            "FieldMate network unavailable:",
            request.url

        );


        const cached =
            await findNavigationCache(
                request
            );


        if (
            cached
        ) {

            console.log(

                "=================================================="
            );

            console.log(

                "OFFLINE PAGE CACHE HIT:",
                request.url

            );

            console.log(
                "=================================================="
            );


            return cached;

        }


        /*
         * No cached application page exists.
         */

        return offlinePageNotCached(
            request.url
        );

    }

}


/* ==========================================================
   FIND NAVIGATION CACHE
========================================================== */

async function findNavigationCache(
    request
) {

    const cache =
        await caches.open(
            CACHE_NAME
        );


    /* ======================================================
       TRY EXACT URL FIRST
    ====================================================== */

    const exact =
        await cache.match(
            request
        );


    if (
        exact
    ) {

        return exact;

    }


    const url =
        new URL(
            request.url
        );


    /* ======================================================
       BASE PAGE FALLBACK
    ====================================================== */

    if (
        shouldCacheBaseNavigation(
            url.pathname
        )
    ) {

        const baseURL =
            getBaseNavigationURL(
                request
            );


        const base =
            await cache.match(
                baseURL.pathname
            );


        if (
            base
        ) {

            console.log(

                "Navigation base-page cache hit:",
                baseURL.pathname

            );


            return base;

        }

    }


    return null;

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

                new Request(

                    request,

                    {
                        redirect:
                            "follow"
                    }

                )

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
           CACHE SUCCESSFUL RESOURCE
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

        }


        return response;

    }


    /* ======================================================
       OFFLINE
    ====================================================== */

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

                <p
                    style="
                        font-size:13px;
                        color:#666;
                        margin-top:20px;
                    "
                >
                    Requested page:
                    ${escapeHTML(requestedURL)}
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
                        cursor:pointer;
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
   ESCAPE HTML
========================================================== */

function escapeHTML(
    value
) {

    return String(
        value
    )

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
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
            !event.data
        ) {

            return;

        }


        /* ==================================================
           FORCE UPDATE
        ================================================== */

        if (

            event.data.type ===
            "SKIP_WAITING"

        ) {

            console.log(
                "FieldMate requested Service Worker update."
            );


            self.skipWaiting();

        }


        /* ==================================================
           CLEAR FIELDMATE CACHE
        ================================================== */

        if (

            event.data.type ===
            "CLEAR_FIELDMATE_CACHE"

        ) {

            console.log(
                "Clearing FieldMate caches..."
            );


            event.waitUntil(

                caches.keys()

                .then(

                    function(cacheNames) {

                        return Promise.all(

                            cacheNames.map(

                                function(cacheName) {

                                    if (

                                        cacheName.startsWith(
                                            "dcgl-fieldmate-v"
                                        )

                                        ||

                                        cacheName.startsWith(
                                            "dcgl-fieldmate-api-v"
                                        )

                                    ) {

                                        console.log(

                                            "Deleting cache:",
                                            cacheName

                                        );


                                        return caches.delete(
                                            cacheName
                                        );

                                    }


                                    return Promise.resolve(
                                        false
                                    );

                                }

                            )

                        );

                    }

                )

            );

        }

    }

);