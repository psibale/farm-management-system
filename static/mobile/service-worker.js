/* ==========================================================
   DCGL FIELDMATE
   Progressive Web App
   Service Worker
   Version 2.0

   FEATURES
   ----------------------------------------------------------
   - Safe offline caching
   - Network first for application pages
   - Cache first for static assets
   - Never cache redirects
   - Never cache failed responses
   - Prevent redirect errors
   - Offline fallback
========================================================== */


// ==========================================================
// VERSION
// ==========================================================

const CACHE_NAME =
    "dcgl-fieldmate-v2";


// ==========================================================
// OFFLINE FALLBACK
// ==========================================================

const OFFLINE_PAGE =
    "/mobile/";


// ==========================================================
// INSTALL
// ==========================================================

self.addEventListener(
    "install",
    function(event) {

        console.log(
            "DCGL FieldMate Service Worker installing..."
        );


        event.waitUntil(

            caches.open(
                CACHE_NAME
            )

            .then(
                function(cache) {

                    /*
                     * IMPORTANT
                     *
                     * Do NOT pre-cache /mobile/
                     * here because the Flask route
                     * requires login and may redirect.
                     *
                     * We cache successful responses
                     * when the user actually visits them.
                     */

                    return cache.addAll([

                        "/static/mobile/manifest.json",

                        "/static/mobile/icons/icon-192.png",

                        "/static/mobile/icons/icon-512.png"

                    ]);

                }

            )

            .catch(
                function(error) {

                    console.warn(
                        "Some FieldMate assets could not be pre-cached:",
                        error
                    );

                }

            )

        );


        /*
         * Activate the new Service Worker
         * immediately.
         */

        self.skipWaiting();

    }

);


// ==========================================================
// ACTIVATE
// ==========================================================

self.addEventListener(
    "activate",
    function(event) {

        console.log(
            "DCGL FieldMate Service Worker activated."
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
                                        "Removing old cache:",
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


// ==========================================================
// FETCH
// ==========================================================

self.addEventListener(
    "fetch",
    function(event) {

        const request =
            event.request;


        /*
         * Only handle GET requests.
         *
         * POST requests such as:
         *
         * /mobile/save_survey
         *
         * must go directly to Flask.
         */

        if (
            request.method !==
            "GET"
        ) {

            return;

        }


        const url =
            new URL(
                request.url
            );


        /*
         * Only handle requests belonging
         * to this application.
         */

        if (
            url.origin !==
            self.location.origin
        ) {

            return;

        }


        // ==================================================
        // APPLICATION NAVIGATION
        // ==================================================

        if (
            request.mode ===
            "navigate"
        ) {

            event.respondWith(

                networkFirstNavigation(
                    request
                )

            );


            return;

        }


        // ==================================================
        // STATIC / OTHER GET REQUESTS
        // ==================================================

        event.respondWith(

            cacheFirstStatic(
                request
            )

        );

    }

);


// ==========================================================
// NETWORK FIRST NAVIGATION
// ==========================================================

async function networkFirstNavigation(
    request
) {

    try {

        console.log(
            "Network navigation:",
            request.url
        );


        /*
         * Explicitly use "follow".
         *
         * This allows Flask redirects to be
         * followed normally when online.
         */

        const response =
            await fetch(

                request,

                {

                    redirect:
                        "follow"

                }

            );


        // ==================================================
        // NEVER CACHE REDIRECT RESPONSES
        // ==================================================

        if (
            response.type ===
            "opaqueredirect"
        ) {

            console.warn(
                "Redirect response not cached:",
                request.url
            );


            return response;

        }


        if (
            response.redirected
        ) {

            console.warn(
                "Redirected navigation:",
                request.url,
                "→",
                response.url
            );


            /*
             * IMPORTANT:
             *
             * Do not put redirected authenticated
             * pages into the application cache.
             */

            if (
                response.ok &&
                response.status === 200
            ) {

                return response;

            }


            return response;

        }


        // ==================================================
        // CACHE ONLY SUCCESSFUL RESPONSES
        // ==================================================

        if (
            response.ok &&
            response.status === 200
        ) {

            const cache =
                await caches.open(
                    CACHE_NAME
                );


            /*
             * Clone before caching because a
             * Response body can only be consumed once.
             */

            const responseClone =
                response.clone();


            await cache.put(
                request,
                responseClone
            );

        }


        return response;

    }


    // ======================================================
    // NETWORK FAILED
    // ======================================================

    catch (error) {

        console.warn(
            "Network navigation failed:",
            request.url
        );


        /*
         * Try the exact requested page
         * from cache.
         */

        const cachedResponse =
            await caches.match(
                request
            );


        if (
            cachedResponse
        ) {

            console.log(
                "Serving cached page:",
                request.url
            );


            return cachedResponse;

        }


        /*
         * If the exact page isn't cached,
         * try the offline application page.
         */

        const offlineResponse =
            await caches.match(
                OFFLINE_PAGE
            );


        if (
            offlineResponse
        ) {

            console.log(
                "Serving FieldMate offline page."
            );


            return offlineResponse;

        }


        /*
         * Last resort.
         */

        return new Response(

            `
            <!DOCTYPE html>

            <html>

            <head>

                <meta charset="utf-8">

                <meta
                    name="viewport"
                    content="width=device-width, initial-scale=1"
                >

                <title>
                    DCGL FieldMate
                </title>

                <style>

                    body {

                        font-family: Arial, sans-serif;

                        text-align: center;

                        padding: 40px;

                        background: #f8f9fa;

                    }

                    h2 {

                        color: #198754;

                    }

                </style>

            </head>

            <body>

                <h2>
                    DCGL FieldMate
                </h2>

                <p>
                    FieldMate is currently offline.
                </p>

                <p>
                    Please reconnect to the DCGL
                    network and try again.
                </p>

            </body>

            </html>
            `,

            {

                status: 503,

                headers: {

                    "Content-Type":
                        "text/html; charset=utf-8"

                }

            }

        );

    }

}


// ==========================================================
// CACHE FIRST STATIC ASSETS
// ==========================================================

async function cacheFirstStatic(
    request
) {

    const cachedResponse =
        await caches.match(
            request
        );


    if (
        cachedResponse
    ) {

        return cachedResponse;

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


        // ==================================================
        // NEVER CACHE REDIRECTS
        // ==================================================

        if (
            response.redirected
        ) {

            console.warn(
                "Static redirect not cached:",
                request.url
            );


            return response;

        }


        // ==================================================
        // CACHE ONLY HTTP 200
        // ==================================================

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
            "Static resource unavailable:",
            request.url
        );


        /*
         * Let the browser handle the failure.
         */

        throw error;

    }

}


// ==========================================================
// SERVICE WORKER MESSAGE
// ==========================================================

self.addEventListener(
    "message",
    function(event) {

        if (
            event.data &&
            event.data.type ===
            "SKIP_WAITING"
        ) {

            self.skipWaiting();

        }

    }

);