/* ==========================================================
   DCGL FIELDMATE
   Survey Details
   Version 7.0

   OFFLINE-FIRST SUB-FIELD NUMBERING

   PURPOSE
   ----------------------------------------------------------
   1. Load survey information from DCGL server.
   2. Fall back to cached survey information when offline.
   3. Maintain persistent sub-field numbering on the device.
   4. Use the server only as a baseline when available.
   5. Never allow a stale server/cache response to move the
      local sequence backwards.
   6. Only "last_used" is advanced after a survey is actually
      saved successfully.
   7. Opening a survey does NOT consume a number.

   EXAMPLE
   ----------------------------------------------------------
       Parent       DG01000
       First        DG01001
       Next         DG01002
       Next         DG01003

   PERSISTENT STATE
   ----------------------------------------------------------
       server_next = last known server suggestion
       last_used   = highest sub-field actually saved

   NEXT NUMBER
   ----------------------------------------------------------
       max(
           last_used + 1,
           server_next
       )

========================================================== */


let surveyData = null;


/* ==========================================================
   LOCAL STORAGE KEYS
========================================================== */

const SURVEY_DATA_CACHE_KEY =
    "dcglFieldMateSurveyData";


const SUBFIELD_STATE_PREFIX =
    "dcglFieldMateSubfieldState_";


/*
 * Old version used:
 *
 * dcglFieldMateNextSubfield_
 *
 * It is deliberately NOT used anymore.
 *
 * It may remain in localStorage on existing phones, but it
 * cannot control numbering.
 */


/* ==========================================================
   NORMALIZE FIELD NAME
========================================================== */

function normalizeFieldName(value) {

    return String(
        value || ""
    )
        .trim()
        .toUpperCase();

}


/* ==========================================================
   GET NUMERIC PART OF FIELD
========================================================== */

function getFieldNumber(fieldName) {

    const field =
        normalizeFieldName(
            fieldName
        );


    const match =
        field.match(
            /(\d+)$/
        );


    if (
        !match
    ) {

        return null;

    }


    const number =
        parseInt(
            match[1],
            10
        );


    return Number.isFinite(
        number
    )
        ? number
        : null;

}


/* ==========================================================
   GET FIELD PREFIX
========================================================== */

function getFieldPrefix(fieldName) {

    const field =
        normalizeFieldName(
            fieldName
        );


    const match =
        field.match(
            /^(.*?)(\d+)$/
        );


    if (
        !match
    ) {

        return null;

    }


    return match[1];

}


/* ==========================================================
   GET NUMERIC WIDTH
========================================================== */

function getFieldNumberWidth(fieldName) {

    const field =
        normalizeFieldName(
            fieldName
        );


    const match =
        field.match(
            /(\d+)$/
        );


    if (
        !match
    ) {

        return 0;

    }


    return match[1].length;

}


/* ==========================================================
   BUILD FIELD NAME
========================================================== */

function buildFieldName(
    parent,
    number
) {

    const normalizedParent =
        normalizeFieldName(
            parent
        );


    const prefix =
        getFieldPrefix(
            normalizedParent
        );


    const width =
        getFieldNumberWidth(
            normalizedParent
        );


    if (
        !prefix ||
        !width ||
        !Number.isFinite(number)
    ) {

        return "";

    }


    return (

        prefix +

        String(
            number
        )
            .padStart(
                width,
                "0"
            )

    );

}


/* ==========================================================
   GET SUB-FIELD STATE KEY
========================================================== */

function getSubfieldStateKey(parent) {

    return (

        SUBFIELD_STATE_PREFIX +

        normalizeFieldName(
            parent
        )

    );

}


/* ==========================================================
   GET LOCAL SUB-FIELD STATE
========================================================== */

function getLocalSubfieldState(parent) {

    try {

        const normalizedParent =
            normalizeFieldName(
                parent
            );


        if (
            !normalizedParent
        ) {

            return null;

        }


        const raw =
            localStorage.getItem(
                getSubfieldStateKey(
                    normalizedParent
                )
            );


        if (
            !raw
        ) {

            return null;

        }


        const state =
            JSON.parse(
                raw
            );


        if (
            !state ||
            typeof state !== "object"
        ) {

            return null;

        }


        return state;

    }

    catch (error) {

        console.warn(
            "Unable to read local sub-field sequence:",
            error
        );


        return null;

    }

}


/* ==========================================================
   SAVE LOCAL SUB-FIELD STATE
========================================================== */

function saveLocalSubfieldState(
    parent,
    updates = {}
) {

    try {

        const normalizedParent =
            normalizeFieldName(
                parent
            );


        if (
            !normalizedParent
        ) {

            return false;

        }


        const existing =
            getLocalSubfieldState(
                normalizedParent
            ) || {};


        const state = {

            parent:
                normalizedParent,

            last_used:
                normalizeFieldName(
                    updates.last_used ??
                    existing.last_used ??
                    ""
                ),

            server_next:
                normalizeFieldName(
                    updates.server_next ??
                    existing.server_next ??
                    ""
                ),

            updated_at:
                new Date().toISOString()

        };


        localStorage.setItem(

            getSubfieldStateKey(
                normalizedParent
            ),

            JSON.stringify(
                state
            )

        );


        console.log(
            "Local sub-field state updated:",
            state
        );


        return true;

    }

    catch (error) {

        console.error(
            "Unable to save local sub-field state:",
            error
        );


        return false;

    }

}


/* ==========================================================
   RECORD USED SUB-FIELD
========================================================== */
/*
   IMPORTANT:
   This function is called AFTER a survey has been
   successfully saved.

   It advances last_used only forward.

   Example:
       DG01001 saved
       last_used = DG01001

       DG01002 saved
       last_used = DG01002

   It NEVER moves backwards.
========================================================== */

function recordUsedSubfield(
    parent,
    field
) {

    const normalizedParent =
        normalizeFieldName(
            parent
        );


    const normalizedField =
        normalizeFieldName(
            field
        );


    if (
        !normalizedParent ||
        !normalizedField
    ) {

        console.warn(
            "Cannot record sub-field. Parent or field is missing."
        );

        return false;

    }


    const parentPrefix =
        getFieldPrefix(
            normalizedParent
        );


    const fieldPrefix =
        getFieldPrefix(
            normalizedField
        );


    if (
        !parentPrefix ||
        !fieldPrefix ||
        parentPrefix !== fieldPrefix
    ) {

        console.warn(
            "Sub-field prefix mismatch:",
            normalizedParent,
            normalizedField
        );

        return false;

    }


    const parentNumber =
        getFieldNumber(
            normalizedParent
        );


    const fieldNumber =
        getFieldNumber(
            normalizedField
        );


    if (
        parentNumber === null ||
        fieldNumber === null
    ) {

        console.warn(
            "Invalid parent or sub-field number:",
            normalizedParent,
            normalizedField
        );

        return false;

    }


    /*
     * A sub-field must be greater than its parent.
     */

    if (
        fieldNumber <=
        parentNumber
    ) {

        console.warn(
            "Field is not a valid sub-field:",
            normalizedField
        );

        return false;

    }


    const existing =
        getLocalSubfieldState(
            normalizedParent
        ) || {};


    const existingNumber =
        existing.last_used
            ? getFieldNumber(
                existing.last_used
            )
            : null;


    /*
     * Never move last_used backwards.
     */

    if (
        existingNumber !== null &&
        existingNumber >= fieldNumber
    ) {

        console.log(
            "Local last_used is already ahead:",
            existing.last_used
        );

        return true;

    }


    const saved =
        saveLocalSubfieldState(

            normalizedParent,

            {

                last_used:
                    normalizedField

            }

        );


    if (
        saved
    ) {

        console.log(
            "✅ SAVED SUB-FIELD RECORDED"
        );

        console.log(
            "Parent:",
            normalizedParent
        );

        console.log(
            "Last used:",
            normalizedField
        );

    }


    return saved;

}


/* ==========================================================
   RECORD SERVER NEXT
========================================================== */
/*
   The server provides a suggested NEXT number.

   This does NOT mean the number has been used.

   Therefore we store it separately as server_next.

   Example:

       Server says DG01005

       server_next = DG01005
       last_used   = DG01003

       local next = DG01005

   The value is never placed into last_used merely because
   the survey screen was opened.
========================================================== */

function recordServerNextSubfield(
    parent,
    serverNext
) {

    const normalizedParent =
        normalizeFieldName(
            parent
        );


    const normalizedServerNext =
        normalizeFieldName(
            serverNext
        );


    if (
        !normalizedParent ||
        !normalizedServerNext
    ) {

        return false;

    }


    const parentNumber =
        getFieldNumber(
            normalizedParent
        );


    const serverNumber =
        getFieldNumber(
            normalizedServerNext
        );


    const parentPrefix =
        getFieldPrefix(
            normalizedParent
        );


    const serverPrefix =
        getFieldPrefix(
            normalizedServerNext
        );


    if (
        parentNumber === null ||
        serverNumber === null ||
        !parentPrefix ||
        !serverPrefix ||
        parentPrefix !== serverPrefix
    ) {

        return false;

    }


    /*
     * Server next must actually be a sub-field.
     */

    if (
        serverNumber <=
        parentNumber
    ) {

        return false;

    }


    const existing =
        getLocalSubfieldState(
            normalizedParent
        ) || {};


    const existingServerNumber =
        existing.server_next
            ? getFieldNumber(
                existing.server_next
            )
            : null;


    /*
     * Never move server_next backwards.
     */

    if (
        existingServerNumber !== null &&
        existingServerNumber >= serverNumber
    ) {

        return true;

    }


    /*
     * Also never let server_next be lower than the next
     * number implied by last_used.
     *
     * Example:
     *
     * last_used = DG01004
     * server says DG01003
     *
     * We keep the existing sequence.
     */

    const existingLastUsedNumber =
        existing.last_used
            ? getFieldNumber(
                existing.last_used
            )
            : null;


    if (
        existingLastUsedNumber !== null &&
        serverNumber <=
        existingLastUsedNumber
    ) {

        return true;

    }


    return saveLocalSubfieldState(

        normalizedParent,

        {

            server_next:
                normalizedServerNext

        }

    );

}


/* ==========================================================
   GET LOCAL NEXT SUB-FIELD
========================================================== */

function getLocalNextSubfield(parent) {

    const normalizedParent =
        normalizeFieldName(
            parent
        );


    if (
        !normalizedParent
    ) {

        return "";

    }


    const parentNumber =
        getFieldNumber(
            normalizedParent
        );


    if (
        parentNumber === null
    ) {

        return "";

    }


    const state =
        getLocalSubfieldState(
            normalizedParent
        );


    let lastUsedNumber =
        null;


    let serverNextNumber =
        null;


    //------------------------------------------------------
    // LAST USED
    //------------------------------------------------------

    if (
        state &&
        state.last_used
    ) {

        const number =
            getFieldNumber(
                state.last_used
            );


        if (
            number !== null &&
            number >
            parentNumber
        ) {

            lastUsedNumber =
                number;

        }

    }


    //------------------------------------------------------
    // SERVER NEXT
    //------------------------------------------------------

    if (
        state &&
        state.server_next
    ) {

        const number =
            getFieldNumber(
                state.server_next
            );


        if (
            number !== null &&
            number >
            parentNumber
        ) {

            serverNextNumber =
                number;

        }

    }


    //------------------------------------------------------
    // NO LOCAL INFORMATION
    //------------------------------------------------------

    if (
        lastUsedNumber === null &&
        serverNextNumber === null
    ) {

        return "";

    }


    //------------------------------------------------------
    // DETERMINE NEXT
    //------------------------------------------------------

    let nextNumber =
        parentNumber + 1;


    /*
     * last_used + 1
     */

    if (
        lastUsedNumber !== null
    ) {

        nextNumber =
            Math.max(

                nextNumber,

                lastUsedNumber + 1

            );

    }


    /*
     * server_next
     */

    if (
        serverNextNumber !== null
    ) {

        nextNumber =
            Math.max(

                nextNumber,

                serverNextNumber

            );

    }


    return buildFieldName(

        normalizedParent,

        nextNumber

    );

}


/* ==========================================================
   LOAD SURVEY INFORMATION
========================================================== */

async function loadSurveyData() {

    try {

        console.log(
            "Loading FieldMate survey information..."
        );


        const response =
            await fetch(

                "/mobile/survey_data",

                {

                    method:
                        "GET",

                    cache:
                        "no-store",

                    credentials:
                        "same-origin"

                }

            );


        if (
            !response.ok
        ) {

            throw new Error(
                "Server returned " +
                response.status
            );

        }


        const data =
            await response.json();


        if (
            !data ||
            !data.survey_types
        ) {

            throw new Error(
                "Invalid survey information received."
            );

        }


        surveyData =
            data;


        try {

            localStorage.setItem(

                SURVEY_DATA_CACHE_KEY,

                JSON.stringify(
                    surveyData
                )

            );

        }

        catch (storageError) {

            console.warn(
                "Could not save survey information locally:",
                storageError
            );

        }


        populateSurveyTypes();

        populateParentFields();

        loadSystemInformation();

        await generateFieldName();


        console.log(
            "FieldMate survey information loaded online."
        );

    }


    catch (error) {

        console.warn(
            "Online survey information unavailable:",
            error
        );


        try {

            const localData =
                localStorage.getItem(
                    SURVEY_DATA_CACHE_KEY
                );


            if (
                localData
            ) {

                surveyData =
                    JSON.parse(
                        localData
                    );


                console.log(
                    "=================================================="
                );

                console.log(
                    "OFFLINE: Using locally saved survey information."
                );

                console.log(
                    "=================================================="
                );


                populateSurveyTypes();

                populateParentFields();

                loadSystemInformation();

                await generateFieldName();


                return;

            }

        }

        catch (localError) {

            console.error(
                "Local survey data error:",
                localError
            );

        }


        showOfflineSurveyDataMessage();

    }

}


/* ==========================================================
   SURVEY TYPES
========================================================== */

function populateSurveyTypes() {

    const select =
        document.getElementById(
            "surveyType"
        );


    if (
        !select
    ) {

        return;

    }


    select.innerHTML =
        "";


    if (
        !surveyData ||
        !surveyData.survey_types
    ) {

        return;

    }


    surveyData.survey_types.forEach(

        type => {

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


/* ==========================================================
   PARENT FIELDS
========================================================== */

function populateParentFields() {

    const select =
        document.getElementById(
            "parentField"
        );


    if (
        !select
    ) {

        return;

    }


    select.innerHTML =
        "";


    if (
        !surveyData ||
        !surveyData.parent_fields
    ) {

        return;

    }


    surveyData.parent_fields.forEach(

        field => {

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


/* ==========================================================
   SYSTEM INFORMATION
========================================================== */

function loadSystemInformation() {

    if (
        !surveyData
    ) {

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


    if (
        season
    ) {

        season.value =
            surveyData.season || "";

    }


    if (
        surveyor
    ) {

        surveyor.value =
            surveyData.surveyor || "";

    }


    if (
        totalFields
    ) {

        totalFields.innerHTML =
            surveyData.total_fields || 0;

    }


    if (
        totalSubfields
    ) {

        totalSubfields.innerHTML =
            surveyData.total_subfields || 0;

    }

}


/* ==========================================================
   GENERATE FIELD NAME
========================================================== */

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
        normalizeFieldName(
            parentElement.value
        );


    /* ======================================================
       MAIN FIELD
    ====================================================== */

    if (
        surveyType ===
        "Main Field"
    ) {

        field.value =
            "";

        field.placeholder =
            "Enter New Main Field";

        field.readOnly =
            false;

        return;

    }


    /* ======================================================
       SUB-FIELD
    ====================================================== */

    if (
        surveyType ===
        "Sub-field"
    ) {

        field.readOnly =
            true;


        field.placeholder =
            "Calculating next sub-field...";


        /* ==================================================
           STEP 1
           CHECK PERSISTENT LOCAL SEQUENCE
        ================================================== */

        let localNext =
            getLocalNextSubfield(
                parent
            );


        /* ==================================================
           STEP 2
           SERVER BASELINE
        ================================================== */

        let serverNext =
            "";


        /*
         * Only use the server response to establish or
         * advance the baseline.
         *
         * The server response does NOT directly overwrite
         * last_used.
         */

        try {

            /*
             * Do not repeatedly call the server once a
             * persistent local sequence already exists.
             *
             * This is particularly important offline because
             * the service worker may return an old cached API
             * response.
             */

            if (
                !localNext
            ) {

                const response =
                    await fetch(

                        `/mobile/next_subfield/${encodeURIComponent(parent)}`,

                        {

                            method:
                                "GET",

                            cache:
                                "no-store",

                            credentials:
                                "same-origin"

                        }

                    );


                if (
                    response.ok
                ) {

                    const data =
                        await response.json();


                    if (
                        data &&
                        data.next
                    ) {

                        serverNext =
                            normalizeFieldName(
                                data.next
                            );


                        /*
                         * Store server baseline separately.
                         */

                        recordServerNextSubfield(

                            parent,

                            serverNext

                        );

                    }

                }

            }

        }

        catch (error) {

            console.log(
                "No live server numbering available."
            );

        }


        /* ==================================================
           RELOAD LOCAL STATE
        ================================================== */

        const persistentState =
            getLocalSubfieldState(
                parent
            );


        /* ==================================================
           USE LOCAL NEXT
        ================================================== */

        localNext =
            getLocalNextSubfield(
                parent
            );


        /*
         * If the server was freshly contacted but localNext
         * still does not exist, use serverNext as the initial
         * baseline.
         */

        if (
            !localNext &&
            serverNext
        ) {

            localNext =
                serverNext;

        }


        /* ==================================================
           NUMERIC VALIDATION
        ================================================== */

        const localNumber =
            getFieldNumber(
                localNext
            );


        const serverNumber =
            getFieldNumber(
                serverNext
            );


        const parentNumber =
            getFieldNumber(
                parent
            );


        if (
            parentNumber === null
        ) {

            field.value =
                "";

            field.placeholder =
                "Invalid parent field";

            field.readOnly =
                false;


            return;

        }


        /* ==================================================
           SELECT NEXT NUMBER
        ================================================== */

        let nextNumber =
            null;


        //--------------------------------------------------
        // LOCAL PERSISTENT NUMBER FIRST
        //--------------------------------------------------

        if (
            localNumber !== null
        ) {

            nextNumber =
                localNumber;

        }


        //--------------------------------------------------
        // SERVER NUMBER SECOND
        //--------------------------------------------------

        else if (
            serverNumber !== null
        ) {

            nextNumber =
                serverNumber;

        }


        //--------------------------------------------------
        // PARENT + 1 LAST FALLBACK
        //--------------------------------------------------

        else {

            nextNumber =
                parentNumber + 1;

        }


        /* ==================================================
           NEVER GO BELOW PARENT + 1
        ================================================== */

        if (
            nextNumber <=
            parentNumber
        ) {

            nextNumber =
                parentNumber + 1;

        }


        /* ==================================================
           BUILD FINAL FIELD
        ================================================== */

        const finalNext =
            buildFieldName(

                parent,

                nextNumber

            );


        if (
            !finalNext
        ) {

            field.value =
                "";

            field.placeholder =
                "Unable to generate sub-field";

            field.readOnly =
                false;


            return;

        }


        field.value =
            finalNext;


        field.readOnly =
            true;


        field.placeholder =
            "";


        /* ==================================================
           DEBUG
        ================================================== */

        const latestState =
            getLocalSubfieldState(
                parent
            );


        console.log(
            "=================================================="
        );

        console.log(
            "FIELDMATE SUB-FIELD NUMBERING"
        );

        console.log(
            "Parent:",
            parent
        );

        console.log(
            "Persistent state:",
            latestState || "None"
        );

        console.log(
            "Persistent local next:",
            localNext || "None"
        );

        console.log(
            "Server next:",
            serverNext || "Unavailable"
        );

        console.log(
            "Selected next:",
            finalNext
        );

        console.log(
            "=================================================="
        );


        return;

    }


    /* ======================================================
       UPDATE BOUNDARY
    ====================================================== */

    if (
        surveyType ===
        "Update Boundary"
    ) {

        field.readOnly =
            true;

        field.value =
            parent;

        field.placeholder =
            "";

        return;

    }

}


/* ==========================================================
   SAVE SURVEY SESSION
========================================================== */

function saveSurveySession() {

    const surveyType =
        document.getElementById(
            "surveyType"
        )?.value || "";


    const parent =
        document.getElementById(
            "parentField"
        )?.value || "";


    const field =
        document.getElementById(
            "generatedField"
        )?.value || "";


    const info = {

        survey_type:
            surveyType,

        parent:
            parent,

        field:
            field,

        season:
            document.getElementById(
                "season"
            )?.value || "",

        surveyor:
            document.getElementById(
                "surveyor"
            )?.value || ""

    };


    sessionStorage.setItem(

        "dcglSurvey",

        JSON.stringify(
            info
        )

    );


    console.log(
        "FieldMate survey session saved:",
        info
    );

}


/* ==========================================================
   OFFLINE DATA MESSAGE
========================================================== */

function showOfflineSurveyDataMessage() {

    const surveyType =
        document.getElementById(
            "surveyType"
        );


    const parentField =
        document.getElementById(
            "parentField"
        );


    if (
        surveyType
    ) {

        surveyType.innerHTML = `

            <option value="">
                No offline survey data available
            </option>

        `;

    }


    if (
        parentField
    ) {

        parentField.innerHTML = `

            <option value="">
                Connect to DCGL LAN first
            </option>

        `;

    }


    console.warn(
        "FieldMate survey information has not yet been cached."
    );

}


/* ==========================================================
   EVENTS
========================================================== */

document.addEventListener(

    "DOMContentLoaded",

    function() {

        const surveyTypeElement =
            document.getElementById(
                "surveyType"
            );


        if (
            surveyTypeElement
        ) {

            surveyTypeElement.addEventListener(

                "change",

                function() {

                    generateFieldName();

                }

            );

        }


        const parentFieldElement =
            document.getElementById(
                "parentField"
            );


        if (
            parentFieldElement
        ) {

            parentFieldElement.addEventListener(

                "change",

                function() {

                    generateFieldName();

                }

            );

        }


        const continueSurveyElement =
            document.getElementById(
                "continueSurvey"
            );


        if (
            continueSurveyElement
        ) {

            continueSurveyElement.addEventListener(

                "click",

                function() {

                    saveSurveySession();

                }

            );

        }

    }

);


/* ==========================================================
   START
========================================================== */

loadSurveyData();