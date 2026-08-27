/* ==========================================================
   DCGL FIELDMATE
   Offline Survey Synchronisation
   Version 4.0

   CLEAN PWA SYNC ENGINE

   Features:
   - Prevent duplicate sync requests
   - Automatic sync when internet returns
   - Manual synchronisation
   - Initial sync when FieldMate opens
   - No unnecessary periodic server polling
   - LAN/server availability check
   - Sequential survey upload
========================================================== */


// ==========================================================
// SYNC CONTROL
// ==========================================================

let dcglSyncRunning = false;

let dcglSyncQueued = false;

let dcglOnlineTimer = null;

let dcglLastSyncTime = 0;


// Minimum time between automatic sync attempts
// Prevents multiple online events from hammering server.

const DCGL_SYNC_COOLDOWN = 5000;


// Delay after connection is restored

const DCGL_ONLINE_DELAY = 1500;


// ==========================================================
// CHECK ACTUAL FLASK SERVER
// ==========================================================

async function isFieldMateServerAvailable() {

    try {

        console.log(
            "Checking DCGL Flask server..."
        );


        const controller =
            new AbortController();


        const timeout =
            setTimeout(

                function() {

                    controller.abort();

                },

                3000

            );


        const response =
            await fetch(

                "/mobile/survey_data",

                {

                    method: "GET",

                    cache: "no-store",

                    signal:
                        controller.signal

                }

            );


        clearTimeout(
            timeout
        );


        if (!response.ok) {

            console.warn(
                "DCGL server returned:",
                response.status
            );

            return false;

        }


        let data;


        try {

            data =
                await response.json();

        }

        catch (error) {

            console.warn(
                "DCGL server returned invalid JSON."
            );

            return false;

        }


        if (
            data &&
            data.system !== undefined
        ) {

            console.log(
                "DCGL Flask server is available."
            );


            return true;

        }


        console.warn(
            "DCGL server response was not recognised."
        );


        return false;

    }

    catch (error) {

        console.log(
            "DCGL Flask server unavailable."
        );


        return false;

    }

}


// ==========================================================
// SYNC ALL PENDING SURVEYS
// ==========================================================

async function syncOfflineSurveys() {


    // ======================================================
    // PREVENT DUPLICATE SYNCS
    // ======================================================

    if (dcglSyncRunning) {

        console.log(
            "Offline synchronisation already running."
        );


        // Remember that another request was made.
        // We don't start another sync simultaneously.

        dcglSyncQueued = true;


        return;

    }


    // ======================================================
    // INTERNET CHECK
    // ======================================================

    if (!navigator.onLine) {

        console.log(
            "Device is offline. Synchronisation skipped."
        );


        if (
            typeof updateOfflineStatus ===
            "function"
        ) {

            updateOfflineStatus();

        }


        return;

    }


    // ======================================================
    // COOLDOWN
    // ======================================================

    const now =
        Date.now();


    if (
        now - dcglLastSyncTime <
        DCGL_SYNC_COOLDOWN
    ) {

        console.log(
            "Synchronisation request ignored " +
            "because another sync was recently attempted."
        );


        return;

    }


    // ======================================================
    // RECORD SYNC TIME
    // ======================================================

    dcglLastSyncTime =
        now;


    // ======================================================
    // LOCK
    // ======================================================

    dcglSyncRunning =
        true;


    dcglSyncQueued =
        false;


    console.log(
        "=================================================="
    );

    console.log(
        "DCGL FIELDMATE OFFLINE SYNCHRONISATION"
    );

    console.log(
        "==================================================");


    try {


        // ==================================================
        // CHECK ACTUAL FLASK SERVER
        // ==================================================

        const serverAvailable =
            await isFieldMateServerAvailable();


        if (!serverAvailable) {

            console.log(
                "DCGL Flask server unavailable. " +
                "Synchronisation skipped."
            );


            return;

        }


        // ==================================================
        // GET PENDING QUEUE
        // ==================================================

        let surveys;


        try {

            surveys =
                await getPendingSurveys();

        }

        catch (error) {

            console.error(
                "Unable to read offline queue:",
                error
            );


            return;

        }


        // ==================================================
        // NOTHING TO SYNC
        // ==================================================

        if (
            !surveys ||
            !surveys.length
        ) {

            console.log(
                "No offline surveys waiting for sync."
            );


            return;

        }


        console.log(
            "Offline surveys waiting:",
            surveys.length
        );


        // ==================================================
        // SYNC ONE BY ONE
        // ==================================================

        for (
            const survey of surveys
        ) {


            // =================================================
            // CHECK DEVICE CONNECTION
            // =================================================

            if (!navigator.onLine) {

                console.warn(
                    "Internet connection lost. " +
                    "Synchronisation stopped."
                );


                break;

            }


            // =================================================
            // VALID SURVEY ID
            // =================================================

            if (!survey.survey_id) {

                console.error(
                    "Survey has no survey_id:",
                    survey
                );


                continue;

            }


            console.log(
                "Synchronising survey:",
                survey.survey_id
            );


            // =================================================
            // RECORD SYNC ATTEMPT
            // =================================================

            if (
                typeof markSurveySyncAttempt ===
                "function"
            ) {

                try {

                    await markSurveySyncAttempt(
                        survey.survey_id
                    );

                }

                catch (error) {

                    console.warn(
                        "Unable to record sync attempt:",
                        error
                    );

                }

            }


            try {


                // =============================================
                // SEND TO FLASK
                // =============================================

                const response =
                    await fetch(

                        "/mobile/save_survey",

                        {

                            method: "POST",

                            headers: {

                                "Content-Type":
                                    "application/json"

                            },

                            body:
                                JSON.stringify(
                                    survey
                                )

                        }

                    );


                // =============================================
                // READ SERVER RESPONSE
                // =============================================

                let result;


                try {

                    result =
                        await response.json();

                }

                catch (jsonError) {

                    throw new Error(
                        "Server returned an invalid response."
                    );

                }


                console.log(
                    "Server response:",
                    result
                );


                // =============================================
                // SUCCESS
                // =============================================

                if (
                    response.ok &&
                    result.success
                ) {

                    console.log(
                        "Survey uploaded successfully:",
                        survey.survey_id
                    );


                    // -----------------------------------------
                    // MARK AS SYNCED
                    // -----------------------------------------

                    if (
                        typeof markSurveySynced ===
                        "function"
                    ) {

                        await markSurveySynced(
                            survey.survey_id
                        );

                    }


                    console.log(
                        "Survey marked as synced:",
                        survey.survey_id
                    );

                }


                // =============================================
                // SERVER REJECTED SURVEY
                // =============================================

                else {

                    const message =
                        result.message ||
                        "Server rejected survey.";


                    console.error(
                        "Survey sync failed:",
                        survey.survey_id,
                        message
                    );


                    if (
                        typeof markSurveyFailed ===
                        "function"
                    ) {

                        await markSurveyFailed(

                            survey.survey_id,

                            message

                        );

                    }

                }

            }


            // =================================================
            // NETWORK / FETCH ERROR
            // =================================================

            catch (error) {

                console.error(
                    "Survey synchronisation error:",
                    survey.survey_id,
                    error
                );


                // ---------------------------------------------
                // KEEP SURVEY IN OFFLINE QUEUE
                // ---------------------------------------------

                try {

                    if (
                        typeof markSurveyFailed ===
                        "function"
                    ) {

                        await markSurveyFailed(

                            survey.survey_id,

                            error.message ||
                            "Network error."

                        );

                    }

                }

                catch (dbError) {

                    console.error(
                        "Unable to update failed survey:",
                        dbError
                    );

                }


                // ---------------------------------------------
                // STOP IF CONNECTION DISAPPEARED
                // ---------------------------------------------

                if (!navigator.onLine) {

                    console.warn(
                        "Internet connection lost. " +
                        "Stopping synchronisation."
                    );


                    break;

                }


                // ---------------------------------------------
                // Do not continue hammering a server that
                // appears to have become unreachable.
                // ---------------------------------------------

                const serverStillAvailable =
                    await isFieldMateServerAvailable();


                if (!serverStillAvailable) {

                    console.warn(
                        "DCGL Flask server unavailable. " +
                        "Stopping synchronisation."
                    );


                    break;

                }

            }

        }

    }

    finally {


        // ==================================================
        // RELEASE LOCK
        // ==================================================

        dcglSyncRunning =
            false;


        // ==================================================
        // UPDATE OFFLINE STATUS
        // ==================================================

        if (
            typeof updateOfflineStatus ===
            "function"
        ) {

            updateOfflineStatus();

        }


        console.log(
            "Offline synchronisation finished."
        );


        // ==================================================
        // HANDLE QUEUED REQUEST
        // ==================================================

        if (dcglSyncQueued) {

            console.log(
                "A synchronisation request was queued. " +
                "Checking again."
            );


            dcglSyncQueued =
                false;


            setTimeout(

                function() {

                    syncOfflineSurveys();

                },

                DCGL_SYNC_COOLDOWN

            );

        }

    }

}


// ==========================================================
// AUTOMATIC SYNC WHEN NETWORK RETURNS
// ==========================================================

window.addEventListener(

    "online",

    function() {

        console.log(
            "DCGL FieldMate network connection restored."
        );


        // -----------------------------------------------
        // Cancel an existing scheduled online sync
        // -----------------------------------------------

        if (dcglOnlineTimer) {

            clearTimeout(
                dcglOnlineTimer
            );

        }


        // -----------------------------------------------
        // Wait for network/LAN to stabilise
        // -----------------------------------------------

        dcglOnlineTimer =
            setTimeout(

                function() {

                    dcglOnlineTimer =
                        null;


                    console.log(
                        "Starting automatic offline survey sync..."
                    );


                    syncOfflineSurveys();

                },

                DCGL_ONLINE_DELAY

            );

    }

);


// ==========================================================
// MANUAL SYNC EVENT
// ==========================================================

window.addEventListener(

    "dcglManualSync",

    function() {

        console.log(
            "Manual DCGL synchronisation requested."
        );


        syncOfflineSurveys();

    }

);


// ==========================================================
// START AUTOMATIC SYNC
// ==========================================================

document.addEventListener(

    "DOMContentLoaded",

    function() {

        console.log(
            "DCGL FieldMate offline sync engine started."
        );


        // -----------------------------------------------
        // Initial check
        // -----------------------------------------------

        setTimeout(

            function() {

                syncOfflineSurveys();

            },

            DCGL_ONLINE_DELAY

        );

    }

);