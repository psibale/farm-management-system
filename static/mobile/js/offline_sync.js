/* ==========================================================
   DCGL FIELDMATE
   Offline Survey Synchronisation
   Version 1.0
========================================================== */


// ==========================================================
// SYNC ALL PENDING SURVEYS
// ==========================================================

async function syncOfflineSurveys() {

    //------------------------------------------------------
    // INTERNET CHECK
    //------------------------------------------------------

    if (!navigator.onLine) {

        console.log(
            "Offline. Synchronisation skipped."
        );

        updateOfflineStatus();

        return;

    }


    //------------------------------------------------------
    // GET QUEUE
    //------------------------------------------------------

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


    if (!surveys.length) {

        console.log(
            "No offline surveys waiting for sync."
        );

        updateOfflineStatus();

        return;

    }


    console.log(
        "Offline surveys waiting:",
        surveys.length
    );


    //------------------------------------------------------
    // SYNC ONE BY ONE
    //------------------------------------------------------

    for (const survey of surveys) {

        try {

            console.log(
                "Synchronising:",
                survey.survey_id
            );


            //--------------------------------------------------
            // SEND TO EXISTING FLASK API
            //--------------------------------------------------

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


            //--------------------------------------------------
            // SERVER RESPONSE
            //--------------------------------------------------

            const result =
                await response.json();


            //--------------------------------------------------
            // SUCCESS
            //--------------------------------------------------

            if (
                response.ok &&
                result.success
            ) {

                await markSurveySynced(
                    survey.survey_id
                );


                console.log(
                    "Survey synchronised:",
                    survey.survey_id
                );

            }

            //--------------------------------------------------
            // SERVER REJECTED SURVEY
            //--------------------------------------------------

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

        //------------------------------------------------------
        // NETWORK ERROR
        //------------------------------------------------------

        catch (error) {

            await markSurveyFailed(
                survey.survey_id,
                error.message
            );


            console.error(
                "Survey sync network error:",
                error
            );


            //--------------------------------------------------
            // Stop here.
            // If network disappeared, don't hammer server.
            //--------------------------------------------------

            if (!navigator.onLine) {

                break;

            }

        }

    }


    //------------------------------------------------------
    // UPDATE UI
    //------------------------------------------------------

    updateOfflineStatus();

}


// ==========================================================
// AUTOMATIC SYNC WHEN CONNECTION RETURNS
// ==========================================================

window.addEventListener(
    "online",
    function() {

        console.log(
            "Internet connection restored."
        );


        setTimeout(
            syncOfflineSurveys,
            1000
        );

    }
);


// ==========================================================
// MANUAL SYNC EVENT
// ==========================================================

window.addEventListener(
    "dcglManualSync",
    function() {

        syncOfflineSurveys();

    }
);


// ==========================================================
// START SYNC
// ==========================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        setTimeout(
            syncOfflineSurveys,
            1500
        );

    }
);