/* ==========================================================
   DCGL FIELDMATE
   Survey Review
   Version 2.1
========================================================== */

let survey = {};

let reviewMap;

let parentAreaData = null;

//----------------------------------------------------------
// LOAD SURVEY
//----------------------------------------------------------

function loadSurvey(){

    const saved =
        sessionStorage.getItem("dcglSurvey");

    if(!saved){

        alert("No survey found.");

        window.location.href = "/mobile";

        return;

    }

    try {

        survey = JSON.parse(saved);

    }

    catch(error){

        console.error("Invalid survey data:", error);

        alert("Survey data is invalid.");

        window.location.href = "/mobile";

        return;

    }


    //------------------------------------------------------
    // SURVEY INFORMATION
    //------------------------------------------------------

    document.getElementById("reviewSurveyType").innerHTML =
        survey.survey_type || "";

    document.getElementById("reviewParent").innerHTML =
        survey.parent || "-";

    document.getElementById("reviewField").innerHTML =
        survey.field || "";

    document.getElementById("reviewSeason").innerHTML =
        survey.season || "";

    document.getElementById("reviewSurveyor").innerHTML =
        survey.surveyor || "";


    //------------------------------------------------------
    // SURVEY RESULTS
    //------------------------------------------------------

    document.getElementById("reviewArea").innerHTML =
        Number(survey.area || 0).toFixed(3);

    document.getElementById("reviewPerimeter").innerHTML =
        Number(survey.perimeter || 0).toFixed(1);

    document.getElementById("reviewDistance").innerHTML =
        Number(survey.distance || 0).toFixed(1);

    document.getElementById("reviewPoints").innerHTML =
        survey.points || 0;

    document.getElementById("reviewTime").innerHTML =
        survey.time || "00:00:00";

    document.getElementById("reviewAccuracy").innerHTML =
        "±" +
        Number(
            survey.average_accuracy || 0
        ).toFixed(1);


    //------------------------------------------------------
    // DRAW MAP
    //------------------------------------------------------

    drawPolygon();


    //------------------------------------------------------
    // VALIDATE SURVEY
    //------------------------------------------------------

    showValidationReport();

    loadParentArea();

}


//----------------------------------------------------------
// DRAW POLYGON
//----------------------------------------------------------

function drawPolygon(){

    if(!survey.geojson){

        console.warn(
            "No GeoJSON available for survey."
        );

        return;

    }


    //------------------------------------------------------
    // CREATE MAP
    //------------------------------------------------------

    reviewMap =
        L.map("reviewMap");


    //------------------------------------------------------
    // BASE MAP
    //------------------------------------------------------

    L.tileLayer(

        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",

        {

            maxZoom: 22,

            attribution:
                "© OpenStreetMap"

        }

    ).addTo(reviewMap);


    //------------------------------------------------------
    // DRAW SURVEY POLYGON
    //------------------------------------------------------

    const polygon =
        L.geoJSON(

            survey.geojson,

            {

                style: {

                    color: "#198754",

                    weight: 4,

                    fillOpacity: 0.30

                }

            }

        ).addTo(reviewMap);


    //------------------------------------------------------
    // ZOOM TO SURVEY
    //------------------------------------------------------

    if(polygon.getBounds().isValid()){

        reviewMap.fitBounds(

            polygon.getBounds(),

            {

                padding: [20,20]

            }

        );

    }

}


//----------------------------------------------------------
// VALIDATION REPORT
//----------------------------------------------------------

function showValidationReport() {

    //------------------------------------------------------
    // Validate survey
    //------------------------------------------------------

    if (
        typeof SurveyValidator === "undefined"
    ) {

        console.error(
            "SurveyValidator is not loaded."
        );

        return;

    }


    const result =
        SurveyValidator.validate(survey);


    console.log(
        "VALIDATION RESULT:",
        result
    );


    //------------------------------------------------------
    // BUILD VALIDATION REPORT
    //------------------------------------------------------

    let html = "";


    result.checks.forEach(check => {

        let icon = "🟢";

        let className =
            "validation-pass";


        //--------------------------------------------------
        // FAILED CHECK
        //--------------------------------------------------

        if (!check.passed) {

            icon = "🔴";

            className =
                "validation-fail";

        }


        //--------------------------------------------------
        // WARNING
        //--------------------------------------------------

        else if (
            check.penalty &&
            check.penalty > 0
        ) {

            icon = "🟡";

            className =
                "validation-warning";

        }


        //--------------------------------------------------
        // REPORT ROW
        //--------------------------------------------------

        html += `

            <div class="
                validation-row
                ${className}
            ">

                <div class="validation-name">

                    <span class="validation-icon">

                        ${icon}

                    </span>

                    ${check.name}

                </div>

                <div class="validation-result">

                    ${check.message}

                </div>

            </div>

        `;

    });


    //------------------------------------------------------
    // DISPLAY REPORT
    //------------------------------------------------------

    const report =
        document.getElementById(
            "validationReport"
        );


    if (report) {

        report.innerHTML =
            html;

    }


    //------------------------------------------------------
    // UPDATE QUALITY
    //------------------------------------------------------

    updateSurveyQuality(
        result.score,
        result.status
    );

}


//----------------------------------------------------------
// SURVEY QUALITY DISPLAY
//----------------------------------------------------------

function updateSurveyQuality(
    score,
    status
) {

    //------------------------------------------------------
    // ELEMENTS
    //------------------------------------------------------

    const scoreElement =
        document.getElementById(
            "surveyScore"
        );

    const statusElement =
        document.getElementById(
            "surveyStatus"
        );

    const messageElement =
        document.getElementById(
            "surveyMessage"
        );

    const box =
        document.getElementById(
            "scoreBox"
        );


    //------------------------------------------------------
    // SCORE
    //------------------------------------------------------

    if (scoreElement) {

        scoreElement.innerHTML =
            score + "%";

    }


    //------------------------------------------------------
    // DEFAULT
    //------------------------------------------------------

    let stars =
        "★★★★★";

    let message =
        "Survey meets the recommended quality standard.";

    let background =
        "#198754";


    //------------------------------------------------------
    // EXCELLENT
    //------------------------------------------------------

    if (score >= 90) {

        stars =
            "★★★★★";

        status =
            "EXCELLENT SURVEY";

        message =
            "Survey quality is excellent.";

        background =
            "#198754";

    }


    //------------------------------------------------------
    // GOOD
    //------------------------------------------------------

    else if (score >= 80) {

        stars =
            "★★★★☆";

        status =
            "GOOD SURVEY";

        message =
            "Survey meets the recommended quality standard.";

        background =
            "#198754";

    }


    //------------------------------------------------------
    // ACCEPTABLE
    //------------------------------------------------------

    else if (score >= 70) {

        stars =
            "★★★☆☆";

        status =
            "ACCEPTABLE SURVEY";

        message =
            "Survey is acceptable but some items should be reviewed.";

        background =
            "#d39e00";

    }


    //------------------------------------------------------
    // REVIEW REQUIRED
    //------------------------------------------------------

    else {

        stars =
            "★★☆☆☆";

        status =
            "REVIEW REQUIRED";

        message =
            "Please review the highlighted survey issues.";

        background =
            "#dc3545";

    }


    //------------------------------------------------------
    // DISPLAY STATUS
    //------------------------------------------------------

    if (statusElement) {

        statusElement.innerHTML =
            stars +
            " " +
            status;

    }


    //------------------------------------------------------
    // DISPLAY MESSAGE
    //------------------------------------------------------

    if (messageElement) {

        messageElement.innerHTML =
            message;

    }


    //------------------------------------------------------
    // UPDATE SCORE BOX
    //------------------------------------------------------

    if (box) {

        box.style.background =
            background;

    }

}

//----------------------------------------------------------
// SAVE SURVEY
//----------------------------------------------------------

document.getElementById(
    "saveSurvey"
).onclick = function(){

    //------------------------------------------------------
    // VALIDATE BEFORE SAVING
    //------------------------------------------------------

    if(
        typeof SurveyValidator === "undefined"
    ){

        console.error(
            "SurveyValidator is not loaded."
        );

        alert(
            "Survey validation module is not loaded."
        );

        return;

    }


    //------------------------------------------------------
    // RUN VALIDATION
    //------------------------------------------------------

    const result =
        SurveyValidator.validate(survey);


    console.log(
        "SURVEY SAVE VALIDATION:",
        result
    );


    //------------------------------------------------------
    // REVIEW REQUIRED
    //------------------------------------------------------

    if(result.score < 70){

        alert(

            "SURVEY CANNOT BE SAVED\n\n" +

            "Quality Score: " +
            result.score +
            "%\n\n" +

            "Status: REVIEW REQUIRED\n\n" +

            "Please correct the survey problems " +
            "shown in the Validation Report before saving."

        );

        return;

    }


    //------------------------------------------------------
    // ACCEPTABLE SURVEY
    // 70–79%
    //------------------------------------------------------

    if(
        result.score >= 70 &&
        result.score < 80
    ){

        const confirmed =
            confirm(

                "SURVEY QUALITY WARNING\n\n" +

                "Quality Score: " +
                result.score +
                "%\n\n" +

                "Status: ACCEPTABLE\n\n" +

                "Some survey quality issues were detected.\n\n" +

                "Do you want to save this survey anyway?"

            );


        if(!confirmed){

            return;

        }

    }


    //------------------------------------------------------
    // GOOD / EXCELLENT
    // 80–100%
    //------------------------------------------------------

    if(result.score >= 80){

        const confirmed =
            confirm(

                "SURVEY READY TO SAVE\n\n" +

                "Quality Score: " +
                result.score +
                "%\n\n" +

                "Status: " +
                result.status +
                "\n\n" +

                "Do you want to save this survey?"

            );


        if(!confirmed){

            return;

        }

    }


    //------------------------------------------------------
    // SAVE MODULE
    //------------------------------------------------------

    if(
        typeof saveSurvey === "function"
    ){

        console.log(
            "Survey validation passed. Saving survey..."
        );

        saveSurvey();

    }

    else{

        console.error(
            "saveSurvey() function not found."
        );

        alert(
            "Survey save module is not loaded."
        );

    }

};


//----------------------------------------------------------
// CONTINUE SURVEY
//----------------------------------------------------------

document.getElementById(
    "continueSurvey"
).onclick = function(){

    window.history.back();

};


//----------------------------------------------------------
// DISCARD SURVEY
//----------------------------------------------------------

document.getElementById(
    "discardSurvey"
).onclick = function(){

    if(
        confirm(
            "Discard this survey?\n\n" +
            "All unsaved survey information will be removed."
        )
    ){

        sessionStorage.removeItem(
            "dcglSurvey"
        );

        window.location.href =
            "/mobile";

    }

};

//----------------------------------------------------------
// LOAD PARENT AREA INFORMATION
//----------------------------------------------------------

async function loadParentArea() {

    //------------------------------------------------------
    // Only required for Sub-fields
    //------------------------------------------------------

    if (survey.survey_type !== "Sub-field") {

        return;

    }

    if (!survey.parent) {

        return;

    }

    try {

        const response = await fetch(

            `/mobile/parent_area/${encodeURIComponent(
                survey.parent
            )}`

        );

        const data = await response.json();

        if (!data.success) {

            console.warn(
                "Parent area unavailable:",
                data.message
            );

            return;

        }

        parentAreaData = data;

        //--------------------------------------------------
        // Store inside survey object
        //--------------------------------------------------

        survey.parent_area =
            data.parent_area;

        survey.previously_surveyed =
            data.surveyed_area;

        survey.remaining_area =
            data.remaining_area;

        //--------------------------------------------------
        // Re-run validation
        //--------------------------------------------------

        showValidationReport();

    }

    catch (error) {

        console.error(
            "Unable to load parent area:",
            error
        );

    }

}

//----------------------------------------------------------
// START
//----------------------------------------------------------

loadSurvey();

