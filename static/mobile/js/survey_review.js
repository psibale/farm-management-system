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

function showValidationReport(){

    //------------------------------------------------------
    // MAKE SURE VALIDATOR EXISTS
    //------------------------------------------------------

    if(
        typeof SurveyValidator === "undefined"
    ){

        console.error(
            "SurveyValidator is not loaded."
        );

        document.getElementById(
            "validationReport"
        ).innerHTML = `

            <div class="alert alert-danger mb-0">

                <strong>Validation unavailable.</strong><br>

                Survey Validator module was not loaded.

            </div>

        `;

        return;

    }


    //------------------------------------------------------
    // RUN VALIDATION
    //------------------------------------------------------

    const result =
        SurveyValidator.validate(survey);


    //------------------------------------------------------
    // VALIDATION SUMMARY
    //------------------------------------------------------

    let html = "";


    //------------------------------------------------------
    // OVERALL STATUS
    //------------------------------------------------------

    if(result.passed){

        html += `

            <div class="alert alert-success">

                <strong>
                    ✅ Survey Passed Validation
                </strong>

                <br>

                Survey quality is acceptable.

            </div>

        `;

    }

    else{

        html += `

            <div class="alert alert-warning">

                <strong>
                    ⚠️ Survey Requires Review
                </strong>

                <br>

                One or more survey quality checks
                require attention.

            </div>

        `;

    }


    //------------------------------------------------------
    // INDIVIDUAL CHECKS
    //------------------------------------------------------

    result.checks.forEach(check => {

        const icon =
            check.passed
                ? "✅"
                : "⚠️";


        const rowClass =
            check.passed
                ? "text-success"
                : "text-danger";


        html += `

            <div class="d-flex
                        justify-content-between
                        align-items-center
                        border-bottom
                        py-2">

                <div>

                    <strong class="${rowClass}">

                        ${icon}
                        ${check.name}

                    </strong>

                </div>

                <div class="text-muted text-end">

                    ${check.message}

                </div>

            </div>

        `;

    });


    //------------------------------------------------------
    // DISPLAY REPORT
    //------------------------------------------------------

    document.getElementById(
        "validationReport"
    ).innerHTML = html;


    //------------------------------------------------------
    // DISPLAY FINAL SCORE
    //------------------------------------------------------

    document.getElementById(
        "surveyScore"
    ).innerHTML =
        result.score + "%";


    //------------------------------------------------------
    // UPDATE SCORE DESCRIPTION
    //------------------------------------------------------

    updateScoreDescription(result.score);

}


//----------------------------------------------------------
// SCORE DESCRIPTION
//----------------------------------------------------------

function updateScoreDescription(score){

    const scoreBox =
        document.querySelector(".score-box");


    if(!scoreBox)
        return;


    const description =
        scoreBox.querySelector("div:last-child");


    if(!description)
        return;


    //------------------------------------------------------
    // EXCELLENT
    //------------------------------------------------------

    if(score >= 90){

        description.innerHTML =
            "★★★★★ Excellent Survey";

        return;

    }


    //------------------------------------------------------
    // GOOD
    //------------------------------------------------------

    if(score >= 80){

        description.innerHTML =
            "★★★★☆ Good Survey";

        return;

    }


    //------------------------------------------------------
    // ACCEPTABLE
    //------------------------------------------------------

    if(score >= 70){

        description.innerHTML =
            "★★★☆☆ Acceptable Survey";

        return;

    }


    //------------------------------------------------------
    // NEEDS REVIEW
    //------------------------------------------------------

    if(score >= 50){

        description.innerHTML =
            "★★☆☆☆ Survey Needs Review";

        return;

    }


    //------------------------------------------------------
    // POOR
    //------------------------------------------------------

    description.innerHTML =
        "★☆☆☆☆ Poor Survey";

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
        typeof SurveyValidator !== "undefined"
    ){

        const result =
            SurveyValidator.validate(survey);


        //--------------------------------------------------
        // BLOCK VERY POOR SURVEYS
        //--------------------------------------------------

        if(result.score < 50){

            alert(
                "This survey has a very low quality score (" +
                result.score +
                "%).\n\n" +
                "Please review the survey before saving."
            );

            return;

        }

    }


    //------------------------------------------------------
    // SAVE MODULE
    //------------------------------------------------------

    if(typeof saveSurvey === "function"){

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

