/* ==========================================================
   DCGL FIELDMATE
   Survey Review
   Version 2.0
========================================================== */

let survey = {};

let reviewMap;

//----------------------------------------------------------
// LOAD SURVEY
//----------------------------------------------------------

function loadSurvey(){

    const saved = sessionStorage.getItem("dcglSurvey");

    if(!saved){

        alert("No survey found.");

        window.location.href="/mobile";

        return;

    }

    survey = JSON.parse(saved);

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
        "±" + Number(survey.average_accuracy || 0).toFixed(1);

    calculateSurveyScore();

    drawPolygon();

    showValidationReport();

}

//----------------------------------------------------------
// SURVEY SCORE
//----------------------------------------------------------

function calculateSurveyScore(){

    let score = 100;

    //--------------------------------------------------
    // Average Accuracy
    //--------------------------------------------------

    if(survey.average_accuracy > 5)
        score -= 10;

    if(survey.average_accuracy > 10)
        score -= 20;

    //--------------------------------------------------
    // GPS Points
    //--------------------------------------------------

    if(survey.points < 20)
        score -= 10;

    if(survey.points < 10)
        score -= 20;

    //--------------------------------------------------
    // Area
    //--------------------------------------------------

    if(survey.area <= 0)
        score -= 30;

    if(score < 0)
        score = 0;

    document.getElementById("surveyScore").innerHTML =
        score + "%";

}

//----------------------------------------------------------
// SAVE
//----------------------------------------------------------

document.getElementById("saveSurvey").onclick = function(){

    saveSurvey();

};

//----------------------------------------------------------
// CONTINUE SURVEY
//----------------------------------------------------------

document.getElementById("continueSurvey").onclick = function(){

    window.history.back();

};

//----------------------------------------------------------
// DISCARD
//----------------------------------------------------------

document.getElementById("discardSurvey").onclick = function(){

    if(confirm("Discard this survey?")){

        sessionStorage.removeItem("dcglSurvey");

        window.location.href="/mobile";

    }

};

//----------------------------------------------------------
// DRAW POLYGON
//----------------------------------------------------------

function drawPolygon(){

    if(!survey.geojson)
        return;

    reviewMap = L.map("reviewMap");

    L.tileLayer(

        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",

        {

            maxZoom:22,

            attribution:"© OpenStreetMap"

        }

    ).addTo(reviewMap);

    const polygon = L.geoJSON(

        survey.geojson,

        {

            style:{

                color:"#198754",

                weight:4,

                fillOpacity:0.30

            }

        }

    ).addTo(reviewMap);

    reviewMap.fitBounds(

        polygon.getBounds(),

        {

            padding:[20,20]

        }

    );

}

//----------------------------------------------------------
// VALIDATION REPORT
//----------------------------------------------------------

function showValidationReport() {

    const result = SurveyValidator.validate(survey);

    let html = "";

    result.checks.forEach(check => {

        const icon = check.passed
            ? "✅"
            : "⚠️";

        html += `

            <div class="d-flex justify-content-between border-bottom py-2">

                <div>

                    ${icon}
                    ${check.name}

                </div>

                <div class="text-muted">

                    ${check.message}

                </div>

            </div>

        `;

    });

    document.getElementById("validationReport").innerHTML =
        html;

    document.getElementById("surveyScore").innerHTML =
        result.score + "%";

}

//----------------------------------------------------------
// START
//----------------------------------------------------------

loadSurvey();
