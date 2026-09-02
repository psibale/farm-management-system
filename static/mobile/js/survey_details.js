/* ==========================================================
   DCGL FIELDMATE
   Survey Details
   Version 3.0

   OFFLINE CAPABLE
========================================================== */


let surveyData = null;


/* ==========================================================
   LOCAL STORAGE KEY
========================================================== */

const SURVEY_DATA_CACHE_KEY =
    "dcglFieldMateSurveyData";


/* ==========================================================
   LOAD SURVEY INFORMATION
========================================================== */

async function loadSurveyData() {

    try {

        console.log(
            "Loading FieldMate survey information..."
        );


        /* ==================================================
           TRY SERVER FIRST
        ================================================== */

        const response =
            await fetch(
                "/mobile/survey_data"
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


        /* ==================================================
           MAKE SURE VALID DATA WAS RECEIVED
        ================================================== */

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


        /* ==================================================
           SAVE LOCAL COPY
        ================================================== */

        try {

            localStorage.setItem(

                SURVEY_DATA_CACHE_KEY,

                JSON.stringify(
                    surveyData
                )

            );


            console.log(
                "Survey information saved locally."
            );

        }

        catch (storageError) {

            console.warn(
                "Could not save survey information locally:",
                storageError
            );

        }


        /* ==================================================
           DISPLAY INFORMATION
        ================================================== */

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


        /* ==================================================
           TRY LOCAL COPY
        ================================================== */

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


        /* ==================================================
           NO LOCAL DATA
        ================================================== */

        console.error(
            "No offline survey information available."
        );


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

            select.innerHTML += `

                <option value="${type}">
                    ${type}
                </option>

            `;

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

            select.innerHTML += `

                <option value="${field}">
                    ${field}
                </option>

            `;

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
        parentElement.value;


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
       SUB FIELD
    ====================================================== */

    if (
        surveyType ===
        "Sub-field"
    ) {

        try {

            const response =
                await fetch(

                    `/mobile/next_subfield/${parent}`

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
                data.next
            ) {

                field.readOnly =
                    true;

                field.value =
                    data.next;


                /* ------------------------------------------
                   Save locally
                ------------------------------------------ */

                const key =
                    "dcglFieldMateNextSubfield_" +
                    parent;


                localStorage.setItem(

                    key,

                    JSON.stringify(
                        data
                    )

                );


                console.log(
                    "Next subfield saved locally:",
                    parent,
                    data.next
                );


                return;

            }

        }

        catch (error) {

            console.warn(
                "Unable to obtain next subfield online:",
                error
            );


            /* ----------------------------------------------
               Try local copy
            ---------------------------------------------- */

            try {

                const key =
                    "dcglFieldMateNextSubfield_" +
                    parent;


                const localData =
                    localStorage.getItem(
                        key
                    );


                if (
                    localData
                ) {

                    const data =
                        JSON.parse(
                            localData
                        );


                    field.readOnly =
                        true;

                    field.value =
                        data.next || "";


                    console.log(
                        "OFFLINE: Using saved next subfield:",
                        data.next
                    );


                    return;

                }

            }

            catch (localError) {

                console.warn(
                    "Offline next-subfield data unavailable:",
                    localError
                );

            }

        }


        /*
         * If there is no previously cached value,
         * leave the field usable rather than breaking
         * the entire page.
         */

        field.readOnly =
            false;

        field.placeholder =
            "Connect to LAN to generate sub-field";

        field.value =
            "";

        return;

    }


    /* ======================================================
       UPDATE EXISTING
    ====================================================== */

    if (
        surveyType ===
        "Update Boundary"
    ) {

        field.readOnly =
            true;

        field.value =
            parent;

        return;

    }

}


/* ==========================================================
   SAVE SURVEY SESSION
========================================================== */

function saveSurveySession() {

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
        "FieldMate survey session saved."
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

const surveyTypeElement =
    document.getElementById(
        "surveyType"
    );


if (
    surveyTypeElement
) {

    surveyTypeElement.addEventListener(

        "change",

        generateFieldName

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

        generateFieldName

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


/* ==========================================================
   START
========================================================== */

loadSurveyData();