/* ==========================================================
   DCGL FIELDMATE
   Survey Save Module
   Version 5.0
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
        "Preparing survey for saving..."
    );

    console.log(
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
    // SAVE ID BACK TO CURRENT SURVEY
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


    //------------------------------------------------------
    // SERVER AVAILABLE
    //------------------------------------------------------

    if (serverAvailable) {

        console.log(
            "DCGL server available."
        );


        try {

            await saveSurveyOnline(
                survey
            );

            return;

        }

        catch (error) {

            console.error(
                "Server save failed:",
                error
            );


            //--------------------------------------------------
            // IMPORTANT:
            // Do NOT lose the survey.
            //--------------------------------------------------

            console.log(
                "Server save failed. " +
                "Switching to offline storage."
            );

        }

    }


    //------------------------------------------------------
    // SERVER UNAVAILABLE
    //------------------------------------------------------

    console.log(
        "DCGL server unavailable."
    );


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

                () => {

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


        if (
            response.ok
        ) {

            console.log(
                "DCGL server is reachable."
            );


            return true;

        }


        console.warn(
            "DCGL server returned:",
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
    // READ RESPONSE
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
    // SERVER ERROR
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


    alert(
        "✅ Survey saved successfully."
    );


    //------------------------------------------------------
    // REMOVE CURRENT SURVEY
    //------------------------------------------------------

    sessionStorage.removeItem(
        "dcglSurvey"
    );


    //------------------------------------------------------
    // RETURN TO MOBILE HOME
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
            "Offline survey saved:",
            record
        );


        //--------------------------------------------------
        // USER MESSAGE
        //--------------------------------------------------

        alert(

            "📱 SURVEY SAVED ON PHONE\n\n" +

            "The DCGL server is currently unavailable.\n\n" +

            "Survey ID: " +
            record.survey_id +
            "\n\n" +

            "The survey will automatically " +
            "synchronise when the DCGL LAN connection returns."

        );


        //--------------------------------------------------
        // REMOVE CURRENT SESSION
        //--------------------------------------------------

        sessionStorage.removeItem(
            "dcglSurvey"
        );


        //--------------------------------------------------
        // RETURN TO MOBILE HOME
        //--------------------------------------------------

        window.location.href =
            "/mobile";

    }

    catch (error) {

        console.error(
            "Offline save failed:",
            error
        );


        alert(

            "❌ Unable to save survey offline.\n\n" +

            "Please try again."

        );

    }

}