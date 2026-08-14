/* ==========================================================
   DCGL FIELDMATE
   Offline Survey Synchronisation
   Version 2.0
========================================================== */


// ==========================================================
// SYNC LOCK
// ==========================================================

let dcglSyncRunning = false;


// ==========================================================
// SYNC ALL PENDING SURVEYS
// ==========================================================

async function syncOfflineSurveys() {

    //------------------------------------------------------
    // PREVENT TWO SYNCS RUNNING AT ONCE
    //------------------------------------------------------

    if (dcglSyncRunning) {

        console.log(
            "Offline synchronisation already running."
        );

        return;

    }


    //------------------------------------------------------
    // INTERNET CHECK
    //------------------------------------------------------

    if (!navigator.onLine) {

        console.log(
            "Offline. Synchronisation skipped."
        );

        if (
            typeof updateOfflineStatus === "function"
        ) {

            updateOfflineStatus();

        }

        return;

    }


    //------------------------------------------------------
    // LOCK
    //------------------------------------------------------

    dcglSyncRunning = true;


    console.log(
        "=================================================="
    );

    console.log(
        "DCGL FIELDMATE OFFLINE SYNCHRONISATION"
    );

    console.log(
        "=================================================="
    );


    try {

        //--------------------------------------------------
        // GET PENDING QUEUE
        //--------------------------------------------------

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


        //--------------------------------------------------
        // NOTHING TO SYNC
        //--------------------------------------------------

        if (!surveys.length) {

            console.log(
                "No offline surveys waiting for sync."
            );

            return;

        }


        console.log(
            "Offline surveys waiting:",
            surveys.length
        );


        //--------------------------------------------------
        // SYNC ONE BY ONE
        //--------------------------------------------------

        for (
            const survey of surveys
        ) {


            //------------------------------------------------
            // CHECK CONNECTION BEFORE EACH SURVEY
            //------------------------------------------------

            if (!navigator.onLine) {

                console.warn(
                    "Internet connection lost. " +
                    "Synchronisation stopped."
                );

                break;

            }


            //------------------------------------------------
            // VALID SURVEY ID
            //------------------------------------------------

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


            try {

                //------------------------------------------------
                // SEND TO FLASK
                //------------------------------------------------

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


                //------------------------------------------------
                // READ SERVER RESPONSE
                //------------------------------------------------

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


                //------------------------------------------------
                // SUCCESS
                //------------------------------------------------

                if (
                    response.ok &&
                    result.success
                ) {

                    console.log(
                        "Survey uploaded successfully:",
                        survey.survey_id
                    );


                    //------------------------------------------------
                    // MARK AS SYNCED
                    //------------------------------------------------

                    await markSurveySynced(
                        survey.survey_id
                    );


                    //------------------------------------------------
                    // REMOVE FROM OFFLINE QUEUE
                    //------------------------------------------------

                    await deleteOfflineSurvey(
                        survey.survey_id
                    );


                    console.log(
                        "Survey removed from offline queue:",
                        survey.survey_id
                    );

                }


                //------------------------------------------------
                // SERVER REJECTED SURVEY
                //------------------------------------------------

                else {

                    const message =
                        result.message ||
                        "Server rejected survey.";


                    await markSurveyFailed(
                        survey.survey_id,
                        message
                    );


                    console.error(
                        "Survey sync failed:",
                        survey.survey_id,
                        message
                    );

                }

            }


            //------------------------------------------------
            // NETWORK / FETCH ERROR
            //------------------------------------------------

            catch (error) {

                console.error(
                    "Survey synchronisation error:",
                    survey.survey_id,
                    error
                );


                //------------------------------------------------
                // KEEP SURVEY IN QUEUE
                //------------------------------------------------

                try {

                    await markSurveyFailed(
                        survey.survey_id,
                        error.message
                    );

                }

                catch (dbError) {

                    console.error(
                        "Unable to update failed survey:",
                        dbError
                    );

                }


                //------------------------------------------------
                // STOP IF CONNECTION IS GONE
                //------------------------------------------------

                if (!navigator.onLine) {

                    console.warn(
                        "Internet connection lost. " +
                        "Stopping synchronisation."
                    );

                    break;

                }

            }

        }

    }

    finally {

        //------------------------------------------------------
        // RELEASE LOCK
        //------------------------------------------------------

        dcglSyncRunning = false;


        //------------------------------------------------------
        // UPDATE STATUS INDICATOR
        //------------------------------------------------------

        if (
            typeof updateOfflineStatus === "function"
        ) {

            updateOfflineStatus();

        }


        console.log(
            "Offline synchronisation finished."
        );

    }

}


// ==========================================================
// AUTOMATIC SYNC WHEN INTERNET RETURNS
// ==========================================================

window.addEventListener(
    "online",
    function() {

        console.log(
            "Internet connection restored."
        );


        //--------------------------------------------------
        // Give browser/network a moment to stabilize
        //--------------------------------------------------

        setTimeout(
            function() {

                syncOfflineSurveys();

            },
            1500
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

        setTimeout(
            function() {

                syncOfflineSurveys();

            },
            1500
        );

    }
);