/* ==========================================================
   DCGL FIELDMATE
   Offline Status Indicator
   Version 1.0
========================================================== */


// ==========================================================
// UPDATE OFFLINE STATUS
// ==========================================================

async function updateOfflineStatus() {

    const indicator =
        document.getElementById(
            "offlineStatus"
        );


    if (!indicator)
        return;


    //------------------------------------------------------
    // PENDING COUNT
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
    // OFFLINE
    //------------------------------------------------------

    if (!navigator.onLine) {

        indicator.className =
            "offline-status offline";

        indicator.innerHTML =

            '<i class="fa-solid fa-wifi-slash"></i> ' +

            'Offline' +

            (
                pending > 0
                    ? ' • ' +
                      pending +
                      ' pending'
                    : ''
            );

        return;

    }


    //------------------------------------------------------
    // ONLINE + PENDING
    //------------------------------------------------------

    if (pending > 0) {

        indicator.className =
            "offline-status pending";

        indicator.innerHTML =

            '<i class="fa-solid fa-cloud-arrow-up"></i> ' +

            pending +

            ' survey' +

            (pending === 1 ? '' : 's') +

            ' waiting to sync';

        return;

    }


    //------------------------------------------------------
    // ONLINE
    //------------------------------------------------------

    indicator.className =
        "offline-status online";

    indicator.innerHTML =

        '<i class="fa-solid fa-cloud-check"></i> ' +

        'Online';

}


// ==========================================================
// ONLINE / OFFLINE EVENTS
// ==========================================================

window.addEventListener(
    "online",
    updateOfflineStatus
);

window.addEventListener(
    "offline",
    updateOfflineStatus
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