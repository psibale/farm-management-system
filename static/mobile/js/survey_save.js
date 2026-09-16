/* ==========================================================
   DCGL FIELDMATE
   Survey Save Module
   Version 9.0

   LAN FIRST + OFFLINE FALLBACK
   PERSISTENT SUB-FIELD NUMBERING

   PURPOSE
   ----------------------------------------------------------
   1. Retrieve completed survey from sessionStorage
   2. Generate a unique Survey ID
   3. Attempt LAN/server save first
   4. If LAN is unavailable, save to IndexedDB
   5. If LAN save fails, protect the survey by saving offline
   6. Update persistent sub-field numbering ONLY after a
      confirmed successful save
   7. Remove sessionStorage ONLY after successful save
   8. Keep redirect logic in ONE place
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

        return false;

    }


    //------------------------------------------------------
    // CHECK SURVEY
    //------------------------------------------------------

    if (
        !survey ||
        !survey.field
    ) {

        alert(
            "⚠️ No completed survey is available."
        );

        return false;

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
        "VERSION 9.0"
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

    if (
        !survey.survey_id
    ) {

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
    // TRY ONLINE SAVE
    // =====================================================

    if (
        serverAvailable
    ) {

        console.log(
            "✅ DCGL LAN server is available."
        );


        try {

            await saveSurveyOnline(
                survey
            );


            //------------------------------------------------
            // ONLINE SAVE SUCCESS
            //------------------------------------------------

            console.log(
                "✅ Survey successfully saved to DCGL server."
            );


            //------------------------------------------------
            // USER MESSAGE
            //------------------------------------------------

            alert(

                "✅ Survey saved successfully.\n\n" +

                "Survey ID: " +
                survey.survey_id

            );


            //------------------------------------------------
            // REMOVE SESSION DATA
            //------------------------------------------------

            sessionStorage.removeItem(
                "dcglSurvey"
            );


            //------------------------------------------------
            // RETURN HOME
            //------------------------------------------------

            window.location.href =
                "/mobile";


            return true;

        }

        catch (error) {

            console.error(
                "❌ Online survey save failed:",
                error
            );


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

    return await saveSurveyOfflineMode(
        survey
    );

}


// ==========================================================
// UPDATE PERSISTENT SUB-FIELD SEQUENCE
// ==========================================================
//
// This is the ONLY function in this file that updates
// last_used.
//
// It is called only after a confirmed successful save.
//
// survey_details.js provides:
//
//     recordUsedSubfield(parent, field)
//
// ==========================================================

function recordSavedSubfieldNumber(
    survey
) {

    try {

        //--------------------------------------------------
        // CHECK SURVEY
        //--------------------------------------------------

        if (
            !survey
        ) {

            console.warn(
                "No survey supplied for sub-field sequence update."
            );

            return false;

        }


        //--------------------------------------------------
        // NORMALIZE SURVEY TYPE
        //--------------------------------------------------

        const surveyType =
            String(
                survey.survey_type || ""
            )
                .trim()
                .toLowerCase();


        //--------------------------------------------------
        // ONLY SUB-FIELDS
        //--------------------------------------------------

        if (
            surveyType !==
            "sub-field"
        ) {

            return true;

        }


        //--------------------------------------------------
        // REQUIRED DATA
        //--------------------------------------------------

        const parent =
            String(
                survey.parent || ""
            )
                .trim()
                .toUpperCase();


        const field =
            String(
                survey.field || ""
            )
                .trim()
                .toUpperCase();


        if (
            !parent ||
            !field
        ) {

            console.warn(
                "❌ Sub-field sequence NOT updated.",
                {
                    parent: parent,
                    field: field
                }
            );

            return false;

        }


        //--------------------------------------------------
        // REQUIRED FUNCTION
        //--------------------------------------------------

        if (
            typeof recordUsedSubfield !==
            "function"
        ) {

            console.error(
                "❌ recordUsedSubfield() is not available."
            );

            return false;

        }


        //--------------------------------------------------
        // CURRENT STATE BEFORE UPDATE
        //--------------------------------------------------

        let beforeState =
            null;


        try {

            const stateKey =
                "dcglFieldMateSubfieldState_" +
                parent;


            const raw =
                localStorage.getItem(
                    stateKey
                );


            if (
                raw
            ) {

                beforeState =
                    JSON.parse(
                        raw
                    );

            }

        }

        catch (stateError) {

            console.warn(
                "Could not read sequence state before update:",
                stateError
            );

        }


        console.log(
            "=================================================="
        );

        console.log(
            "UPDATING PERSISTENT SUB-FIELD SEQUENCE"
        );

        console.log(
            "Parent:",
            parent
        );

        console.log(
            "Saved field:",
            field
        );

        console.log(
            "State before:",
            beforeState
        );


        //--------------------------------------------------
        // UPDATE
        //--------------------------------------------------

        const result =
            recordUsedSubfield(
                parent,
                field
            );


        //--------------------------------------------------
        // VERIFY
        //--------------------------------------------------

        let afterState =
            null;


        try {

            const stateKey =
                "dcglFieldMateSubfieldState_" +
                parent;


            const raw =
                localStorage.getItem(
                    stateKey
                );


            if (
                raw
            ) {

                afterState =
                    JSON.parse(
                        raw
                    );

            }

        }

        catch (stateError) {

            console.warn(
                "Could not read sequence state after update:",
                stateError
            );

        }


        console.log(
            "recordUsedSubfield() result:",
            result
        );

        console.log(
            "State after:",
            afterState
        );


        if (
            afterState &&
            afterState.last_used ===
            field
        ) {

            console.log(
                "✅ Persistent last_used confirmed:",
                afterState.last_used
            );

        }

        else {

            console.warn(
                "⚠️ Persistent last_used was not updated as expected."
            );

        }


        console.log(
            "=================================================="
        );


        return (
            result !== false
        );

    }

    catch (error) {

        console.error(
            "Unable to update persistent sub-field numbering:",
            error
        );


        return false;

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

        if (
            response.ok
        ) {

            console.log(
                "✅ DCGL server is reachable."
            );

            return true;

        }


        //--------------------------------------------------
        // SERVER ERROR
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

        if (
            timeout
        ) {

            clearTimeout(
                timeout
            );

        }

    }

}


// ==========================================================
// ONLINE SAVE
// ==========================================================
//
// IMPORTANT:
// This function ONLY performs the server save.
//
// It does NOT:
// - remove sessionStorage
// - show the final success alert
// - redirect to /mobile
//
// The main saveSurvey() function handles those actions.
//
// ==========================================================

async function saveSurveyOnline(
    survey
) {

    if (
        !survey
    ) {

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
    // READ RESPONSE
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
    // SERVER SAVE CONFIRMED
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
        "Survey type:",
        survey.survey_type
    );

    console.log(
        "Parent:",
        survey.parent
    );

    console.log(
        "Field:",
        survey.field
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

    const sequenceUpdated =
        recordSavedSubfieldNumber(
            survey
        );


    if (
        survey.survey_type ===
        "Sub-field"
    ) {

        console.log(
            "Online sub-field sequence updated:",
            sequenceUpdated
        );

    }


    //------------------------------------------------------
    // IMPORTANT
    //
    // Return only after the sequence has been updated.
    //------------------------------------------------------

    return data;

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
            survey.surveyor ||
            record.surveyor ||
            "Unknown"
        );

        console.log(
            "Field:",
            survey.field ||
            record.field ||
            "Unknown"
        );

        console.log(
            "Survey type:",
            survey.survey_type ||
            record.survey_type ||
            "Unknown"
        );

        console.log(
            "Parent:",
            survey.parent ||
            record.parent ||
            "None"
        );

        console.log(
            "Season:",
            survey.season ||
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
        // IMPORTANT:
        //
        // USE THE ORIGINAL SURVEY OBJECT FOR SEQUENCE
        //
        // This avoids depending on IndexedDB returning
        // parent / field / survey_type exactly as expected.
        //--------------------------------------------------

        const sequenceUpdated =
            recordSavedSubfieldNumber(
                survey
            );


        if (
            survey.survey_type ===
            "Sub-field"
        ) {

            console.log(
                "Offline sub-field sequence updated:",
                sequenceUpdated
            );

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


    return await saveSurvey();

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