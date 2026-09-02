/* ==========================================================
   DCGL FIELDMATE
   Offline Survey Synchronisation
   Version 5.0

   CLEAN PWA SYNC ENGINE

   Features:
   - Prevent duplicate sync requests
   - Automatic sync when internet returns
   - Manual synchronisation
   - Initial sync when FieldMate opens
   - No unnecessary periodic server polling
   - LAN / Flask server availability check
   - Sequential survey upload
   - Clear sync trigger logging
   - Failed surveys remain safely in IndexedDB
   - Successfully uploaded surveys are removed
========================================================== */


// ==========================================================
// SYNC CONTROL
// ==========================================================

let dcglSyncRunning = false;

let dcglSyncQueued = false;

let dcglOnlineTimer = null;

let dcglLastSyncTime = 0;


// ==========================================================
// SETTINGS
// ==========================================================

// Minimum time between automatic sync attempts.

const DCGL_SYNC_COOLDOWN = 5000;


// Delay after LAN/internet connection returns.

const DCGL_ONLINE_DELAY = 1500;


// Flask server check timeout.

const DCGL_SERVER_TIMEOUT = 3000;


// ==========================================================
// CHECK ACTUAL FIELDMATE SERVER
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

                DCGL_SERVER_TIMEOUT

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
                "DCGL Flask server returned:",
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
                "DCGL Flask server returned invalid JSON."
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
            "DCGL Flask server response was not recognised."
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

async function syncOfflineSurveys(
    trigger = "UNKNOWN"
) {


    // ======================================================
    // PREVENT DUPLICATE SYNCS
    // ======================================================

    if (dcglSyncRunning) {

        console.log(
            "Offline synchronisation already running."
        );


        console.log(
            "Additional sync request queued."
        );


        dcglSyncQueued =
            true;


        return;

    }


    // ======================================================
    // DEVICE OFFLINE
    // ======================================================

    if (!navigator.onLine) {

        console.log(
            "Device is offline."
        );


        console.log(
            "Synchronisation skipped."
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
            "Synchronisation request ignored."
        );


        console.log(
            "Another sync was attempted recently."
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


    // ======================================================
    // SYNC HEADER
    // ======================================================

    console.log(
        "=================================================="
    );


    console.log(
        "DCGL FIELDMATE OFFLINE SYNCHRONISATION"
    );


    console.log(
        "Trigger:",
        trigger
    );


    console.log(
        "=================================================="
    );


    try {


        // ==================================================
        // CHECK FLASK SERVER
        // ==================================================

        const serverAvailable =
            await isFieldMateServerAvailable();


        if (!serverAvailable) {

            console.log(
                "DCGL Flask server unavailable."
            );


            console.log(
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
                    "Internet/LAN connection lost."
                );


                console.warn(
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
                "--------------------------------------------------"
            );


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
                // SEND SURVEY TO FLASK
                // =============================================

                console.log(
                    "Sending survey to DCGL Flask server..."
                );


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

                        try {

                            await markSurveySynced(
                                survey.survey_id
                            );


                            console.log(
                                "Survey marked as synced:",
                                survey.survey_id
                            );

                        }

                        catch (error) {

                            console.warn(
                                "Unable to mark survey as synced:",
                                error
                            );

                        }

                    }


                    // -----------------------------------------
                    // REMOVE FROM OFFLINE QUEUE
                    // -----------------------------------------

                    if (
                        typeof deleteOfflineSurvey ===
                        "function"
                    ) {

                        try {

                            await deleteOfflineSurvey(
                                survey.survey_id
                            );


                            console.log(
                                "Survey removed from offline queue:",
                                survey.survey_id
                            );

                        }

                        catch (error) {

                            console.error(
                                "Survey uploaded but could not be removed " +
                                "from offline queue:",
                                survey.survey_id,
                                error
                            );

                        }

                    }

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

                        try {

                            await markSurveyFailed(

                                survey.survey_id,

                                message

                            );

                        }

                        catch (error) {

                            console.error(
                                "Unable to record failed survey:",
                                error
                            );

                        }

                    }


                    // -----------------------------------------
                    // Do not immediately retry this survey.
                    // Continue to the next one.
                    // -----------------------------------------

                    continue;

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

                if (
                    typeof markSurveyFailed ===
                    "function"
                ) {

                    try {

                        await markSurveyFailed(

                            survey.survey_id,

                            error.message ||
                            "Network error."

                        );

                    }

                    catch (dbError) {

                        console.error(
                            "Unable to update failed survey:",
                            dbError
                        );

                    }

                }


                // ---------------------------------------------
                // CHECK CONNECTION
                // ---------------------------------------------

                if (!navigator.onLine) {

                    console.warn(
                        "Internet/LAN connection lost."
                    );


                    console.warn(
                        "Stopping synchronisation."
                    );


                    break;

                }


                // ---------------------------------------------
                // Check Flask server once.
                //
                // Do NOT repeatedly poll after every failure.
                // ---------------------------------------------

                const serverStillAvailable =
                    await isFieldMateServerAvailable();


                if (!serverStillAvailable) {

                    console.warn(
                        "DCGL Flask server became unavailable."
                    );


                    console.warn(
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
        // UPDATE STATUS
        // ==================================================

        if (
            typeof updateOfflineStatus ===
            "function"
        ) {

            updateOfflineStatus();

        }


        console.log(
            "=================================================="
        );


        console.log(
            "Offline synchronisation finished."
        );


        console.log(
            "=================================================="
        );


        // ==================================================
        // HANDLE QUEUED REQUEST
        // ==================================================

        if (dcglSyncQueued) {

            console.log(
                "Another synchronisation request was queued."
            );


            console.log(
                "A new sync check will run shortly."
            );


            dcglSyncQueued =
                false;


            setTimeout(

                function() {

                    syncOfflineSurveys(
                        "QUEUED"
                    );

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
            "=================================================="
        );


        console.log(
            "DCGL FieldMate network connection restored."
        );


        console.log(
            "Waiting for LAN/network to stabilise..."
        );


        console.log(
            "=================================================="
        );


        // -----------------------------------------------
        // Cancel existing scheduled online sync
        // -----------------------------------------------

        if (dcglOnlineTimer) {

            clearTimeout(
                dcglOnlineTimer
            );

        }


        // -----------------------------------------------
        // Schedule ONE automatic sync
        // -----------------------------------------------

        dcglOnlineTimer =
            setTimeout(

                function() {

                    dcglOnlineTimer =
                        null;


                    console.log(
                        "Starting automatic offline survey sync..."
                    );


                    syncOfflineSurveys(
                        "INTERNET RESTORED"
                    );

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


        syncOfflineSurveys(
            "MANUAL"
        );

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
        // Initial sync check
        // -----------------------------------------------

        setTimeout(

            function() {

                syncOfflineSurveys(
                    "STARTUP"
                );

            },

            DCGL_ONLINE_DELAY

        );

    }

);
