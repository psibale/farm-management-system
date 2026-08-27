/* ==========================================================
   DCGL FIELDMATE
   Survey Save Module
   Version 6.0
   LAN FIRST + OFFLINE FALLBACK
========================================================== */


// ==========================================================
// SAVE SURVEY
// ==========================================================

async function saveSurvey() {

    //------------------------------------------------------
    // RETRIEVE COMPLETED SURVEY
    //------------------------------------------------------

    const survey =
        JSON.parse(
            sessionStorage.getItem(
                "dcglSurvey"
            ) || "{}"
        );


    //------------------------------------------------------
    // CHECK SURVEY
    //------------------------------------------------------

    if (!survey.field) {

        alert(
            "No survey available."
        );

        return;

    }


    console.log(
        "=================================================="
    );

    console.log(
        "DCGL FIELDMATE - SAVE SURVEY"
    );

    console.log(
        "=================================================="
    );


    console.log(
        "Preparing survey for saving..."
    );

    console.log(
        "Survey:",
        survey
    );


    //------------------------------------------------------
    // CREATE UNIQUE SURVEY ID
    //------------------------------------------------------

    if (!survey.survey_id) {

        survey.survey_id =
            generateSurveyID();

    }


    //------------------------------------------------------
    // UPDATE SESSION STORAGE
    //------------------------------------------------------

    sessionStorage.setItem(

        "dcglSurvey",

        JSON.stringify(survey)

    );


    console.log(
        "Survey ID:",
        survey.survey_id
    );


    //------------------------------------------------------
    // CHECK DCGL SERVER
    //------------------------------------------------------

    const serverAvailable =
        await checkDCGLServer();


    // =====================================================
    // SERVER AVAILABLE
    // =====================================================

    if (serverAvailable) {

        console.log(
            "DCGL server available."
        );


        try {

            await saveSurveyOnline(
                survey
            );


            //------------------------------------------------
            // ONLINE SAVE COMPLETED
            //------------------------------------------------

            return;

        }

        catch (error) {

            console.error(
                "Online survey save failed:",
                error
            );


            //------------------------------------------------
            // IMPORTANT
            //
            // NEVER LOSE A COMPLETED SURVEY.
            //
            // If Flask is reachable but the save itself
            // fails, put the survey into IndexedDB.
            //------------------------------------------------

            console.warn(
                "Online save failed. " +
                "Switching to offline storage."
            );

        }

    }


    // =====================================================
    // SERVER UNAVAILABLE
    // =====================================================

    console.log(
        "DCGL server unavailable."
    );


    //------------------------------------------------------
    // SAVE TO OFFLINE DATABASE
    //------------------------------------------------------

    await saveSurveyOfflineMode(
        survey
    );

}


// ==========================================================
// CHECK DCGL SERVER
// ==========================================================

async function checkDCGLServer() {

    try {

        console.log(
            "Checking DCGL server..."
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


        //--------------------------------------------------
        // SERVER AVAILABLE
        //--------------------------------------------------

        if (
            response.ok
        ) {

            console.log(
                "DCGL server is reachable."
            );


            return true;

        }


        //--------------------------------------------------
        // SERVER RESPONDED WITH ERROR
        //--------------------------------------------------

        console.warn(
            "DCGL server returned HTTP status:",
            response.status
        );


        return false;

    }

    catch (error) {

        console.warn(
            "DCGL server is unreachable:",
            error
        );


        return false;

    }

}


// ==========================================================
// GENERATE UNIQUE SURVEY ID
// ==========================================================

function generateSurveyID() {

    return (

        "DCGL-" +

        Date.now() +

        "-" +

        Math.random()
            .toString(36)
            .substring(2, 10)
            .toUpperCase()

    );

}


// ==========================================================
// ONLINE SAVE
// ==========================================================

async function saveSurveyOnline(
    survey
) {

    console.log(
        "Saving survey to DCGL server..."
    );


    //------------------------------------------------------
    // SEND TO FLASK
    //------------------------------------------------------

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


    //------------------------------------------------------
    // READ SERVER RESPONSE
    //------------------------------------------------------

    let data;


    try {

        data =
            await response.json();

    }

    catch (error) {

        throw new Error(
            "Invalid server response."
        );

    }


    console.log(
        "Server response:",
        data
    );


    //------------------------------------------------------
    // SERVER REJECTED SURVEY
    //------------------------------------------------------

    if (
        !response.ok ||
        !data.success
    ) {

        throw new Error(

            data.message ||
            "Server rejected the survey."

        );

    }


    //------------------------------------------------------
    // SUCCESS
    //------------------------------------------------------

    console.log(
        "Survey saved successfully."
    );


    console.log(
        "Surveyor:",
        data.surveyor || "Server authenticated user"
    );


    //------------------------------------------------------
    // USER MESSAGE
    //------------------------------------------------------

    alert(

        "✅ Survey saved successfully.\n\n" +

        "Survey ID: " +
        survey.survey_id

    );


    //------------------------------------------------------
    // REMOVE CURRENT SURVEY
    //------------------------------------------------------

    sessionStorage.removeItem(
        "dcglSurvey"
    );


    //------------------------------------------------------
    // RETURN TO FIELDMATE HOME
    //------------------------------------------------------

    window.location.href =
        "/mobile";

}


// ==========================================================
// OFFLINE SAVE
// ==========================================================

async function saveSurveyOfflineMode(
    survey
) {

    console.log(
        "Saving survey to offline database..."
    );


    //------------------------------------------------------
    // CHECK OFFLINE DATABASE
    //------------------------------------------------------

    if (
        typeof saveSurveyOffline !==
        "function"
    ) {

        console.error(
            "saveSurveyOffline() is not available."
        );


        alert(

            "⚠️ Offline storage is not available.\n\n" +

            "Please reconnect to the DCGL server " +

            "before saving this survey."

        );


        return;

    }


    //------------------------------------------------------
    // SAVE TO INDEXEDDB
    //------------------------------------------------------

    try {

        const record =
            await saveSurveyOffline(
                survey
            );


        console.log(
            "=================================================="
        );

        console.log(
            "OFFLINE SURVEY SAVED"
        );

        console.log(
            "Survey ID:",
            record.survey_id
        );

        console.log(
            "Surveyor:",
            record.surveyor || "Unknown"
        );

        console.log(
            "Field:",
            record.field
        );

        console.log(
            "Sync status:",
            record.sync_status
        );

        console.log(
            "=================================================="
        );


        //--------------------------------------------------
        // USER MESSAGE
        //--------------------------------------------------

        alert(

            "📱 Survey saved offline.\n\n" +

            "The survey is safely stored on this device " +

            "and will automatically sync when the DCGL " +

            "LAN connection returns."

        );


        //--------------------------------------------------
        // REMOVE CURRENT SESSION
        //--------------------------------------------------

        sessionStorage.removeItem(
            "dcglSurvey"
        );


        //--------------------------------------------------
        // RETURN TO FIELDMATE HOME
        //--------------------------------------------------

        window.location.href =
            "/mobile";

    }

    catch (error) {

        console.error(
            "Offline survey save failed:",
            error
        );


        alert(

            "❌ Unable to save survey offline.\n\n" +

            "The survey has NOT been deleted.\n\n" +

            "Please try saving again."

        );

    }

}