/* ==========================================================
   DCGL FIELDMATE
   Survey Save Module
   Version 4.0
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
    // CHECK CONNECTION
    //------------------------------------------------------

    if (!navigator.onLine) {

        console.log(
            "Device is offline."
        );


        await saveSurveyOfflineMode(
            survey
        );

        return;

    }


    //------------------------------------------------------
    // TRY ONLINE SAVE
    //------------------------------------------------------

    try {

        await saveSurveyOnline(
            survey
        );

    }

    catch (error) {

        console.error(
            "Online save failed:",
            error
        );


        //--------------------------------------------------
        // INTERNET MAY HAVE DROPPED
        //--------------------------------------------------

        if (!navigator.onLine) {

            console.log(
                "Connection lost. Saving offline..."
            );


            await saveSurveyOfflineMode(
                survey
            );

        }

        else {

            alert(
                "Unable to save survey.\n\n" +
                "The server could not save the survey."
            );

        }

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
        "Saving survey to server..."
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

            "⚠️ The device is offline, " +
            "but offline storage is not available.\n\n" +

            "Please reconnect before saving."

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

            "📱 Survey saved offline.\n\n" +

            "The survey is safely stored on this device " +
            "and will automatically sync when the connection returns."

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