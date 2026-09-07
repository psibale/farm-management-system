/* ==========================================================
   DCGL FIELDMATE
   Survey Save Module
   Version 8.0
   LAN FIRST + OFFLINE FALLBACK
   PERSISTENT SUB-FIELD NUMBERING

   PURPOSE
   ----------------------------------------------------------
   1. Retrieve completed survey from sessionStorage
   2. Generate a unique Survey ID
   3. Attempt LAN/server save first
   4. If LAN is unavailable, save to IndexedDB
   5. If LAN save fails, protect the survey by saving offline
   6. Update persistent sub-field numbering AFTER save
   7. Remove sessionStorage ONLY after successful save
========================================================== */


// ==========================================================
// SAVE SURVEY
// ==========================================================

async function saveSurvey() {

    //------------------------------------------------------
    // RETRIEVE COMPLETED SURVEY
    //------------------------------------------------------

    let survey = {};

    try {

        survey =
            JSON.parse(
                sessionStorage.getItem(
                    "dcglSurvey"
                ) || "{}"
            );

    }

    catch (error) {

        console.error(
            "Unable to read survey from sessionStorage:",
            error
        );

        alert(
            "❌ The completed survey could not be read.\n\n" +
            "Please return to the survey and try again."
        );

        return;

    }


    //------------------------------------------------------
    // CHECK SURVEY
    //------------------------------------------------------

    if (!survey || !survey.field) {

        alert(
            "⚠️ No completed survey is available."
        );

        return;

    }


    //------------------------------------------------------
    // DEBUG HEADER
    //------------------------------------------------------

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


    // =====================================================
    // CREATE SURVEY ID
    // =====================================================

    if (!survey.survey_id) {

        if (
            typeof generateSurveyID === "function"
        ) {

            survey.survey_id =
                generateSurveyID();

        }

        else {

            survey.survey_id =

                "DCGL-" +

                Date.now() +

                "-" +

                Math.random()
                    .toString(36)
                    .substring(2, 10)
                    .toUpperCase();

        }

    }


    //------------------------------------------------------
    // UPDATE SESSION STORAGE
    //------------------------------------------------------

    sessionStorage.setItem(

        "dcglSurvey",

        JSON.stringify(
            survey
        )

    );


    console.log(
        "Survey ID:",
        survey.survey_id
    );


    // =====================================================
    // STEP 1
    // CHECK DCGL LAN SERVER
    // =====================================================

    console.log(
        "Checking DCGL LAN server..."
    );


    const serverAvailable =
        await checkDCGLServer();


    // =====================================================
    // STEP 2
    // SERVER AVAILABLE
    // =====================================================

    if (serverAvailable) {

        console.log(
            "✅ DCGL LAN server is available."
        );


        try {

            await saveSurveyOnline(
                survey
            );


            //------------------------------------------------
            // ONLINE SAVE SUCCESSFUL
            //------------------------------------------------

            console.log(
                "✅ Survey successfully saved to DCGL server."
            );


            //------------------------------------------------
            // UPDATE PERSISTENT SUB-FIELD SEQUENCE
            //------------------------------------------------
            //
            // This MUST happen only after the server has
            // successfully accepted the survey.
            //
            // It prevents the next offline survey from
            // receiving the same sub-field number.
            //------------------------------------------------

            recordSavedSubfieldNumber(
                survey
            );


            return;

        }

        catch (error) {

            console.error(
                "❌ Online survey save failed:",
                error
            );


            //------------------------------------------------
            // IMPORTANT
            //
            // Never lose a completed survey.
            //------------------------------------------------

            console.warn(
                "Online save failed. " +
                "Moving survey to IndexedDB."
            );

        }

    }

    else {

        console.warn(
            "DCGL LAN server is unavailable."
        );

    }


    // =====================================================
    // STEP 3
    // OFFLINE FALLBACK
    // =====================================================

    await saveSurveyOfflineMode(
        survey
    );

}


// ==========================================================
// RECORD SAVED SUB-FIELD NUMBER
// ==========================================================
//
// Updates the persistent local sequence ONLY when a survey
// has actually been saved successfully.
//
// survey_details.js provides:
//     recordUsedSubfield(parent, field)
//
// Example:
//
// DG01000
//   ↓
// DG01001 saved
//   ↓
// local last_used = DG01001
//   ↓
// next = DG01002
//
// This works for both online and offline saves.
// ==========================================================

function recordSavedSubfieldNumber(
    survey
) {

    try {

        //--------------------------------------------------
        // Only Sub-field surveys use this numbering system.
        //--------------------------------------------------

        if (
            !survey ||
            survey.survey_type !== "Sub-field"
        ) {

            return;

        }


        //--------------------------------------------------
        // Check required values
        //--------------------------------------------------

        if (
            !survey.parent ||
            !survey.field
        ) {

            console.warn(
                "Sub-field sequence was not updated because " +
                "parent or field is missing.",
                survey
            );

            return;

        }


        //--------------------------------------------------
        // Check numbering function
        //--------------------------------------------------

        if (
            typeof recordUsedSubfield !==
            "function"
        ) {

            console.warn(
                "recordUsedSubfield() is not available. " +
                "Persistent sub-field numbering was not updated."
            );

            return;

        }


        //--------------------------------------------------
        // UPDATE LOCAL PERSISTENT SEQUENCE
        //--------------------------------------------------

        recordUsedSubfield(
            survey.parent,
            survey.field
        );


        console.log(
            "✅ Persistent sub-field sequence updated."
        );

        console.log(
            "Parent:",
            survey.parent
        );

        console.log(
            "Saved sub-field:",
            survey.field
        );


    }

    catch (error) {

        //--------------------------------------------------
        // Do NOT allow numbering failure to invalidate
        // an already successful survey save.
        //--------------------------------------------------

        console.error(
            "Unable to update persistent sub-field numbering:",
            error
        );

    }

}


// ==========================================================
// CHECK DCGL LAN SERVER
// ==========================================================

async function checkDCGLServer() {

    let controller = null;

    let timeout = null;


    try {

        console.log(
            "Checking DCGL server..."
        );


        //--------------------------------------------------
        // ABORT CONTROLLER
        //--------------------------------------------------

        controller =
            new AbortController();


        //--------------------------------------------------
        // SERVER CHECK TIMEOUT
        //--------------------------------------------------

        timeout =
            setTimeout(

                function() {

                    controller.abort();

                },

                3000

            );


        //--------------------------------------------------
        // REQUEST
        //--------------------------------------------------

        const response =
            await fetch(

                "/mobile/survey_data",

                {

                    method:
                        "GET",

                    cache:
                        "no-store",

                    credentials:
                        "same-origin",

                    signal:
                        controller.signal

                }

            );


        //--------------------------------------------------
        // CLEAR TIMEOUT
        //--------------------------------------------------

        clearTimeout(
            timeout
        );


        //--------------------------------------------------
        // SERVER AVAILABLE
        //--------------------------------------------------

        if (response.ok) {

            console.log(
                "✅ DCGL server is reachable."
            );

            return true;

        }


        //--------------------------------------------------
        // SERVER RESPONDED BUT WITH ERROR
        //--------------------------------------------------

        console.warn(
            "DCGL server returned HTTP status:",
            response.status
        );


        return false;

    }

    catch (error) {

        if (
            error &&
            error.name === "AbortError"
        ) {

            console.warn(
                "DCGL server check timed out."
            );

        }

        else {

            console.warn(
                "DCGL server is unreachable:",
                error
            );

        }


        return false;

    }

    finally {

        if (timeout) {

            clearTimeout(
                timeout
            );

        }

    }

}


// ==========================================================
// ONLINE SAVE
// ==========================================================

async function saveSurveyOnline(
    survey
) {

    if (!survey) {

        throw new Error(
            "No survey supplied for online save."
        );

    }


    console.log(
        "=================================================="
    );

    console.log(
        "ONLINE SURVEY SAVE"
    );

    console.log(
        "=================================================="
    );


    console.log(
        "Sending survey to DCGL server..."
    );


    //------------------------------------------------------
    // SEND TO FLASK
    //------------------------------------------------------

    const response =
        await fetch(

            "/mobile/save_survey",

            {

                method:
                    "POST",

                headers: {

                    "Content-Type":
                        "application/json",

                    "Accept":
                        "application/json"

                },

                credentials:
                    "same-origin",

                body:
                    JSON.stringify(
                        survey
                    )

            }

        );


    //------------------------------------------------------
    // READ SERVER RESPONSE
    //------------------------------------------------------

    let data = null;


    try {

        data =
            await response.json();

    }

    catch (error) {

        console.error(
            "Unable to read server JSON response:",
            error
        );


        throw new Error(
            "DCGL server returned an invalid response."
        );

    }


    console.log(
        "DCGL server response:",
        data
    );


    //------------------------------------------------------
    // SERVER REJECTED SURVEY
    //------------------------------------------------------

    if (
        !response.ok ||
        !data ||
        !data.success
    ) {

        throw new Error(

            (
                data &&
                data.message
            )

            ||

            "DCGL server rejected the survey."

        );

    }


    //------------------------------------------------------
    // ONLINE SAVE SUCCESS
    //------------------------------------------------------

    console.log(
        "=================================================="
    );

    console.log(
        "✅ ONLINE SURVEY SAVE SUCCESSFUL"
    );

    console.log(
        "Survey ID:",
        survey.survey_id
    );

    console.log(
        "Surveyor:",
        data.surveyor ||
        survey.surveyor ||
        "Server authenticated user"
    );

    console.log(
        "=================================================="
    );


    //------------------------------------------------------
    // UPDATE PERSISTENT SUB-FIELD SEQUENCE
    //------------------------------------------------------

    if (
        survey.survey_type === "Sub-field" &&
        typeof recordUsedSubfield === "function"
    ) {

        recordUsedSubfield(
            survey.parent,
            survey.field
        );

    }


    //------------------------------------------------------
    // USER MESSAGE
    //------------------------------------------------------

    alert(

        "✅ Survey saved successfully.\n\n" +

        "Survey ID: " +
        survey.survey_id

    );


    //------------------------------------------------------
    // ONLY NOW REMOVE SESSION SURVEY
    //------------------------------------------------------

    sessionStorage.removeItem(
        "dcglSurvey"
    );


    //------------------------------------------------------
    // RETURN TO FIELDMATE
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
        "=================================================="
    );

    console.log(
        "OFFLINE SURVEY SAVE"
    );

    console.log(
        "=================================================="
    );


    //------------------------------------------------------
    // CHECK INDEXEDDB MODULE
    //------------------------------------------------------

    if (
        typeof saveSurveyOffline !==
        "function"
    ) {

        console.error(
            "saveSurveyOffline() is not available."
        );


        alert(

            "❌ Offline storage is not available.\n\n" +

            "The completed survey has NOT been deleted.\n\n" +

            "Please reconnect to the DCGL LAN and " +

            "try saving again."

        );


        return false;

    }


    //------------------------------------------------------
    // SAVE TO INDEXEDDB
    //------------------------------------------------------

    try {

        const record =
            await saveSurveyOffline(
                survey
            );


        //--------------------------------------------------
        // VERIFY RECORD
        //--------------------------------------------------

        if (
            !record ||
            !record.survey_id
        ) {

            throw new Error(
                "Offline database did not return a valid survey record."
            );

        }


        //--------------------------------------------------
        // LOG
        //--------------------------------------------------

        console.log(
            "=================================================="
        );

        console.log(
            "📱 OFFLINE SURVEY SAVED"
        );

        console.log(
            "=================================================="
        );

        console.log(
            "Survey ID:",
            record.survey_id
        );

        console.log(
            "Surveyor:",
            record.surveyor ||
            "Unknown"
        );

        console.log(
            "Field:",
            record.field ||
            "Unknown"
        );

        console.log(
            "Survey type:",
            record.survey_type ||
            "Unknown"
        );

        console.log(
            "Parent:",
            record.parent ||
            "None"
        );

        console.log(
            "Season:",
            record.season ||
            "Unknown"
        );

        console.log(
            "Sync status:",
            record.sync_status ||
            "Pending"
        );

        console.log(
            "=================================================="
        );


        //--------------------------------------------------
        // UPDATE PERSISTENT SUB-FIELD SEQUENCE
        //--------------------------------------------------
        //
        // IMPORTANT:
        //
        // This happens AFTER IndexedDB successfully returns
        // a valid survey record.
        //
        // Therefore:
        //
        // DG01001 is displayed
        //        ↓
        // User saves
        //        ↓
        // IndexedDB save succeeds
        //        ↓
        // last_used = DG01001
        //        ↓
        // Next = DG01002
        //
        // A failed save does NOT consume the number.
        //--------------------------------------------------

        if (
            record.survey_type === "Sub-field" &&
            record.parent &&
            record.field
        ) {

            if (
                typeof recordUsedSubfield ===
                "function"
            ) {

                const sequenceUpdated =
                    recordUsedSubfield(
                        record.parent,
                        record.field
                    );


                console.log(
                    "Sub-field sequence update result:",
                    sequenceUpdated
                );

            }

            else {

                console.warn(
                    "recordUsedSubfield() is not available. " +
                    "Survey was saved, but local sub-field " +
                    "sequence could not be updated."
                );

            }

        }


        //--------------------------------------------------
        // USER MESSAGE
        //--------------------------------------------------

        alert(

            "📱 Survey saved offline.\n\n" +

            "Survey ID: " +
            record.survey_id +
            "\n\n" +

            "The survey is safely stored on this device.\n\n" +

            "It will be synchronized with the DCGL " +
            "server when the LAN connection returns."

        );


        //--------------------------------------------------
        // ONLY NOW REMOVE SESSION SURVEY
        //--------------------------------------------------

        sessionStorage.removeItem(
            "dcglSurvey"
        );


        //--------------------------------------------------
        // RETURN TO FIELDMATE HOME
        //--------------------------------------------------

        window.location.href =
            "/mobile";


        return true;

    }

    catch (error) {

        //--------------------------------------------------
        // CRITICAL FAILURE
        //--------------------------------------------------

        console.error(
            "❌ Offline survey save failed:",
            error
        );


        //--------------------------------------------------
        // DO NOT DELETE SESSION DATA
        //--------------------------------------------------

        alert(

            "❌ Unable to save the survey offline.\n\n" +

            "The completed survey has NOT been deleted.\n\n" +

            "Please try saving again."

        );


        return false;

    }

}

// ==========================================================
// RETRY SURVEY SAVE
// ==========================================================

async function retrySurveySave() {

    console.log(
        "Retrying FieldMate survey save..."
    );


    await saveSurvey();

}


// ==========================================================
// GET CURRENT SURVEY ID
// ==========================================================

function getCurrentSurveyID() {

    try {

        const survey =
            JSON.parse(

                sessionStorage.getItem(
                    "dcglSurvey"
                ) || "{}"

            );


        return survey.survey_id || null;

    }

    catch (error) {

        console.error(
            "Unable to retrieve current Survey ID:",
            error
        );

        return null;

    }

}