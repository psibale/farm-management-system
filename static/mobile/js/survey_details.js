/* ==========================================================
   DCGL FIELDMATE
   Survey Details
   Version 2.0
========================================================== */

let surveyData = null;

//----------------------------------------------------------
// LOAD SURVEY INFORMATION
//----------------------------------------------------------

async function loadSurveyData() {

    try {

        const response = await fetch("/mobile/survey_data");

        surveyData = await response.json();

        populateSurveyTypes();

        populateParentFields();

        loadSystemInformation();

        generateFieldName();

    }

    catch (error) {

        console.error(error);

        alert("Unable to load survey information.");

    }

}

//----------------------------------------------------------
// SURVEY TYPES
//----------------------------------------------------------

function populateSurveyTypes() {

    const select = document.getElementById("surveyType");

    select.innerHTML = "";

    surveyData.survey_types.forEach(type => {

        select.innerHTML += `

            <option value="${type}">
                ${type}
            </option>

        `;

    });

}

//----------------------------------------------------------
// PARENT FIELDS
//----------------------------------------------------------

function populateParentFields() {

    const select = document.getElementById("parentField");

    select.innerHTML = "";

    surveyData.parent_fields.forEach(field => {

        select.innerHTML += `

            <option value="${field}">
                ${field}
            </option>

        `;

    });

}

//----------------------------------------------------------
// SYSTEM INFORMATION
//----------------------------------------------------------

function loadSystemInformation() {

    document.getElementById("season").value =
        surveyData.season;

    document.getElementById("surveyor").value =
        surveyData.surveyor;

    document.getElementById("totalFields").innerHTML =
        surveyData.total_fields;

    document.getElementById("totalSubfields").innerHTML =
        surveyData.total_subfields;

}

//----------------------------------------------------------
// GENERATE FIELD NAME
//----------------------------------------------------------

async function generateFieldName() {

    const surveyType =
        document.getElementById("surveyType").value;

    const parent =
        document.getElementById("parentField").value;

    const field =
        document.getElementById("generatedField");

    //------------------------------------------------------
    // MAIN FIELD
    //------------------------------------------------------

    if (surveyType === "Main Field") {

        field.value = "";

        field.placeholder = "Enter New Main Field";

        field.readOnly = false;

        return;

    }

    //------------------------------------------------------
    // SUB FIELD
    //------------------------------------------------------

    if (surveyType === "Sub-field") {

        const response = await fetch(
            `/mobile/next_subfield/${parent}`
        );

        const data = await response.json();

        field.readOnly = true;

        field.value = data.next;

        return;

    }

    //------------------------------------------------------
    // UPDATE EXISTING
    //------------------------------------------------------

    if (surveyType === "Update Boundary") {

        field.readOnly = true;

        field.value = parent;

    }

}

//----------------------------------------------------------
// SAVE INFORMATION
//----------------------------------------------------------

function saveSurveySession() {

    const info = {

        survey_type:
            document.getElementById("surveyType").value,

        parent:
            document.getElementById("parentField").value,

        field:
            document.getElementById("generatedField").value,

        season:
            document.getElementById("season").value,

        surveyor:
            document.getElementById("surveyor").value

    };

    sessionStorage.setItem(

        "dcglSurvey",

        JSON.stringify(info)

    );

}

//----------------------------------------------------------
// EVENTS
//----------------------------------------------------------

document.getElementById("surveyType")
.addEventListener(

    "change",

    generateFieldName

);

document.getElementById("parentField")
.addEventListener(

    "change",

    generateFieldName

);

document.getElementById("continueSurvey")
.addEventListener(

    "click",

    function () {

        saveSurveySession();

    }

);

//----------------------------------------------------------
// START
//----------------------------------------------------------

loadSurveyData();