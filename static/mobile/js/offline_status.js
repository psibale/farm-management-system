/* ==========================================================
   DCGL FIELDMATE
   LAN / Offline Status Indicator
   Version 2.0
========================================================== */


// ==========================================================
// SERVER HEALTH CHECK
// ==========================================================

async function checkFieldMateServer() {

    try {

        const controller =
            new AbortController();

        const timeout =
            setTimeout(
                () => controller.abort(),
                3000
            );


        const response =
            await fetch(
                "/mobile/survey_data",
                {
                    method: "GET",
                    cache: "no-store",
                    signal: controller.signal
                }
            );


        clearTimeout(timeout);


        if (!response.ok) {

            return false;

        }


        const data =
            await response.json();


        return (
            data &&
            data.system !== undefined
        );

    }

    catch (error) {

        console.log(
            "FieldMate server unavailable."
        );

        return false;

    }

}


// ==========================================================
// UPDATE STATUS
// ==========================================================

async function updateOfflineStatus() {

    const indicator =
        document.getElementById(
            "offlineStatus"
        );


    if (!indicator) {

        return;

    }


    //------------------------------------------------------
    // GET PENDING SURVEYS
    //------------------------------------------------------

    let pending = 0;


    try {

        pending =
            await getPendingSurveyCount();

    }

    catch (error) {

        console.error(
            "Unable to read offline survey count:",
            error
        );

    }


    //------------------------------------------------------
    // CHECK ACTUAL FLASK SERVER
    //------------------------------------------------------

    const serverOnline =
        await checkFieldMateServer();


    //------------------------------------------------------
    // SERVER OFFLINE
    //------------------------------------------------------

    if (!serverOnline) {

        indicator.className =
            "offline-status offline";


        indicator.innerHTML =

            '<i class="fa-solid fa-wifi-slash"></i> ' +

            'LAN Disconnected' +

            (
                pending > 0
                    ? ' • ' +
                      pending +
                      ' saved locally'
                    : ''
            );


        return;

    }


    //------------------------------------------------------
    // SERVER ONLINE + PENDING
    //------------------------------------------------------

    if (pending > 0) {

        indicator.className =
            "offline-status pending";


        indicator.innerHTML =

            '<i class="fa-solid fa-cloud-arrow-up"></i> ' +

            'LAN Connected • ' +

            pending +

            ' waiting to sync';


        return;

    }


    //------------------------------------------------------
    // SERVER ONLINE + NOTHING PENDING
    //------------------------------------------------------

    indicator.className =
        "offline-status online";


    indicator.innerHTML =

        '<i class="fa-solid fa-cloud-check"></i> ' +

        'LAN Connected • Synced';

}


// ==========================================================
// NETWORK EVENTS
// ==========================================================

window.addEventListener(
    "online",
    function() {

        console.log(
            "Network connection detected."
        );


        updateOfflineStatus();

    }
);


window.addEventListener(
    "offline",
    function() {

        console.log(
            "Network connection lost."
        );


        updateOfflineStatus();

    }
);


// ==========================================================
// PERIODIC SERVER CHECK
// ==========================================================

setInterval(

    function() {

        updateOfflineStatus();

    },

    10000

);


// ==========================================================
// INITIAL STATUS
// ==========================================================

document.addEventListener(

    "DOMContentLoaded",

    function() {

        updateOfflineStatus();

    }

);