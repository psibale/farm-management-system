/* ==========================================================
   DCGL FIELDMATE
   Survey Details
   Version 3.0

   OFFLINE-FIRST

   FEATURES
   ----------------------------------------------------------
   - Works online
   - Works offline
   - Saves survey metadata locally
   - Preserves logged-in surveyor
   - Never defaults surveyor to "admin"
   - Uses IndexedDB as offline source
   - Uses sessionStorage as secondary fallback
========================================================== */


let surveyData = null;


// ==========================================================
// LOAD SURVEY INFORMATION
// ==========================================================

async function loadSurveyData() {

    console.log(
        "=================================================="
    );

    console.log(
        "DCGL FieldMate Survey Details"
    );

    console.log(
        "Loading survey information..."
    );

    console.log(
        "Online status:",
        navigator.onLine
    );

    console.log(
        "=================================================="
    );


    // ======================================================
    // TRY SERVER FIRST WHEN ONLINE
    // ======================================================

    if (navigator.onLine) {

        try {

            const response =
                await fetch(
                    "/mobile/survey_data",
                    {
                        method: "GET",

                        cache: "no-store"
                    }
                );


            if (!response.ok) {

                throw new Error(
                    "Server returned HTTP " +
                    response.status
                );

            }


            const data =
                await response.json();


            // ------------------------------------------------
            // VALIDATE RESPONSE
            // ------------------------------------------------

            if (!data) {

                throw new Error(
                    "Empty survey data response."
                );

            }


            surveyData =
                data;


            console.log(
                "FIELDMATE SURVEY DATA:",
                surveyData.surveyor
            );


            // ==================================================
            // IMPORTANT
            // ==================================================
            //
            // Save the AUTHORITATIVE server information
            // locally for offline use.
            //
            // ==================================================

            await saveAppState(
                "surveyData",
                surveyData
            );


            // ------------------------------------------------
            // Save logged-in FieldMate identity separately
            // ------------------------------------------------

            if (
                surveyData.surveyor
            ) {

                await saveAppState(
                    "fieldmate_username",
                    surveyData.surveyor
                );

            }


            // ------------------------------------------------
            // Populate page
            // ------------------------------------------------

            populateSurveyTypes();

            populateParentFields();

            loadSystemInformation();

            await generateFieldName();


            console.log(
                "Survey information loaded ONLINE."
            );


            return;

        }

        catch (error) {

            console.warn(
                "Online survey data unavailable.",
                error
            );

            console.log(
                "Attempting OFFLINE survey data..."
            );

        }

    }


    // ======================================================
    // OFFLINE FALLBACK
    // ======================================================

    try {

        const cachedData =
            await getAppState(
                "surveyData"
            );


        if (
            cachedData
        ) {

            surveyData =
                cachedData;


            console.log(
                "FIELDMATE OFFLINE SURVEY DATA:",
                surveyData.surveyor
            );


            populateSurveyTypes();

            populateParentFields();

            loadSystemInformation();

            await generateFieldName();


            console.log(
                "Survey information loaded from OFFLINE DATABASE."
            );


            return;

        }

    }

    catch (error) {

        console.warn(
            "Unable to read offline survey data:",
            error
        );

    }


    // ======================================================
    // SESSION STORAGE FALLBACK
    // ======================================================

    try {

        const sessionData =
            sessionStorage.getItem(
                "dcglSurvey"
            );


        if (
            sessionData
        ) {

            const parsed =
                JSON.parse(
                    sessionData
                );


            surveyData = {

                survey_types: [

                    "Main Field",

                    "Sub-field",

                    "Update Boundary"

                ],

                parent_fields:

                    parsed.parent
                    ? [parsed.parent]
                    : [],

                total_fields:
                    0,

                total_subfields:
                    0,

                season:
                    parsed.season ||
                    "2026/27",

                surveyor:
                    parsed.surveyor ||
                    "Unknown"

            };


            populateSurveyTypes();

            populateParentFields();

            loadSystemInformation();

            await generateFieldName();


            console.log(
                "Survey information loaded from sessionStorage."
            );


            return;

        }

    }

    catch (error) {

        console.warn(
            "Session storage fallback failed:",
            error
        );

    }


    // ======================================================
    // FINAL FAILURE
    // ======================================================

    console.error(
        "No online or offline survey information available."
    );


    alert(
        "Survey information is not available. " +
        "Please connect to the DCGL network once before starting FieldMate offline."
    );

}


// ==========================================================
// SURVEY TYPES
// ==========================================================

function populateSurveyTypes() {

    const select =
        document.getElementById(
            "surveyType"
        );


    if (!select) {

        return;

    }


    select.innerHTML = "";


    if (
        !surveyData ||
        !Array.isArray(
            surveyData.survey_types
        )
    ) {

        return;

    }


    surveyData.survey_types.forEach(
        function(type) {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                type;


            option.textContent =
                type;


            select.appendChild(
                option
            );

        }
    );

}


// ==========================================================
// PARENT FIELDS
// ==========================================================

function populateParentFields() {

    const select =
        document.getElementById(
            "parentField"
        );


    if (!select) {

        return;

    }


    select.innerHTML = "";


    if (
        !surveyData ||
        !Array.isArray(
            surveyData.parent_fields
        )
    ) {

        return;

    }


    surveyData.parent_fields.forEach(
        function(field) {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                field;


            option.textContent =
                field;


            select.appendChild(
                option
            );

        }
    );

}


// ==========================================================
// SYSTEM INFORMATION
// ==========================================================

function loadSystemInformation() {

    if (!surveyData) {

        return;

    }


    const season =
        document.getElementById(
            "season"
        );


    const surveyor =
        document.getElementById(
            "surveyor"
        );


    const totalFields =
        document.getElementById(
            "totalFields"
        );


    const totalSubfields =
        document.getElementById(
            "totalSubfields"
        );


    if (season) {

        season.value =
            surveyData.season ||
            "2026/27";

    }


    // ======================================================
    // AUTHORITATIVE SURVEYOR
    // ======================================================

    if (surveyor) {

        surveyor.value =
            surveyData.surveyor ||
            "Unknown";

    }


    if (totalFields) {

        totalFields.innerHTML =
            surveyData.total_fields ??
            0;

    }


    if (totalSubfields) {

        totalSubfields.innerHTML =
            surveyData.total_subfields ??
            0;

    }


    console.log(
        "DISPLAYED SURVEYOR:",
        surveyData.surveyor
    );

}


// ==========================================================
// GENERATE FIELD NAME
// ==========================================================

async function generateFieldName() {

    const surveyTypeElement =
        document.getElementById(
            "surveyType"
        );


    const parentElement =
        document.getElementById(
            "parentField"
        );


    const field =
        document.getElementById(
            "generatedField"
        );


    if (
        !surveyTypeElement ||
        !parentElement ||
        !field
    ) {

        return;

    }


    const surveyType =
        surveyTypeElement.value;


    const parent =
        parentElement.value;


    // ======================================================
    // MAIN FIELD
    // ======================================================

    if (
        surveyType ===
        "Main Field"
    ) {

        field.value = "";

        field.placeholder =
            "Enter New Main Field";

        field.readOnly =
            false;

        return;

    }


    // ======================================================
    // SUB FIELD
    // ======================================================

    if (
        surveyType ===
        "Sub-field"
    ) {

        // --------------------------------------------------
        // ONLINE
        // --------------------------------------------------

        if (navigator.onLine) {

            try {

                const response =
                    await fetch(
                        `/mobile/next_subfield/${encodeURIComponent(parent)}`,
                        {
                            cache: "no-store"
                        }
                    );


                if (!response.ok) {

                    throw new Error(
                        "Unable to obtain next sub-field."
                    );

                }


                const data =
                    await response.json();


                field.readOnly =
                    true;


                field.value =
                    data.next;


                // ------------------------------------------------
                // Cache next subfield information
                // ------------------------------------------------

                await saveAppState(
                    "nextSubfield_" + parent,
                    data
                );


                return;

            }

            catch (error) {

                console.warn(
                    "Unable to obtain next sub-field online:",
                    error
                );

            }

        }


        // --------------------------------------------------
        // OFFLINE
        // --------------------------------------------------

        try {

            const cached =
                await getAppState(
                    "nextSubfield_" + parent
                );


            if (
                cached &&
                cached.next
            ) {

                field.readOnly =
                    true;


                field.value =
                    cached.next;


                console.log(
                    "Using cached next sub-field:",
                    cached.next
                );


                return;

            }

        }

        catch (error) {

            console.warn(
                "Offline sub-field lookup failed:",
                error
            );

        }


        // --------------------------------------------------
        // No cached number available
        // --------------------------------------------------

        field.readOnly =
            true;


        field.value = "";


        field.placeholder =
            "Connect to DCGL network to generate next sub-field";


        return;

    }


    // ======================================================
    // UPDATE EXISTING
    // ======================================================

    if (
        surveyType ===
        "Update Boundary"
    ) {

        field.readOnly =
            true;


        field.value =
            parent;

    }

}


// ==========================================================
// SAVE SURVEY SESSION
// ==========================================================

function saveSurveySession() {

    const surveyorElement =
        document.getElementById(
            "surveyor"
        );


    const info = {

        survey_type:
            document.getElementById(
                "surveyType"
            )?.value || "",


        parent:
            document.getElementById(
                "parentField"
            )?.value || "",


        field:
            document.getElementById(
                "generatedField"
            )?.value || "",


        season:
            document.getElementById(
                "season"
            )?.value || "2026/27",


        // ==================================================
        // IMPORTANT
        // ==================================================
        //
        // Use the displayed authenticated surveyor.
        //
        // Never put "admin" here as a default.
        //
        surveyor:
            surveyorElement?.value ||
            surveyData?.surveyor ||
            "Unknown"

    };


    sessionStorage.setItem(

        "dcglSurvey",

        JSON.stringify(
            info
        )

    );


    console.log(
        "FIELDMATE SURVEY SESSION SAVED:",
        info
    );

}


// ==========================================================
// EVENTS
// ==========================================================

document
    .getElementById(
        "surveyType"
    )
    ?.addEventListener(

        "change",

        generateFieldName

    );


document
    .getElementById(
        "parentField"
    )
    ?.addEventListener(

        "change",

        generateFieldName

    );


document
    .getElementById(
        "continueSurvey"
    )
    ?.addEventListener(

        "click",

        function() {

            saveSurveySession();

        }

    );


// ==========================================================
// ONLINE EVENT
// ==========================================================
//
// If the phone reconnects to LAN while this page is open,
// refresh the server data.
//
// ==========================================================

window.addEventListener(
    "online",
    async function() {

        console.log(
            "FieldMate network connection restored."
        );


        try {

            await loadSurveyData();

        }

        catch (error) {

            console.warn(
                "Unable to refresh survey data after reconnect:",
                error
            );

        }

    }
);


// ==========================================================
// START
// ==========================================================

loadSurveyData();