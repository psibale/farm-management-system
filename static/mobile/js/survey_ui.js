/* ==========================================================
   DCGL FIELDMATE
   Survey User Interface
========================================================== */

function updateUI(engine){

    const gpsBtn =
        document.getElementById("startGPS");

    const surveyBtn =
        document.getElementById("startSurvey");

    const finishBtn =
        document.getElementById("finishSurvey");

    switch(engine.state){

        case "STOPPED":

            gpsBtn.innerHTML = "📡 Start GPS";

            surveyBtn.innerHTML = "▶ Start Survey";

            surveyBtn.disabled = true;

            finishBtn.disabled = true;

            break;

        case "SEARCHING":

            gpsBtn.innerHTML = "🛰 Searching...";

            surveyBtn.disabled = true;

            finishBtn.disabled = true;

            break;

        case "READY":

            gpsBtn.innerHTML = "🟢 GPS Ready";

            surveyBtn.innerHTML = "▶ Start Survey";

            surveyBtn.disabled = false;

            finishBtn.disabled = true;

            break;

        case "RECORDING":

            gpsBtn.innerHTML = "🟢 GPS Ready";

            surveyBtn.innerHTML = "🔴 Recording...";

            surveyBtn.disabled = true;

            finishBtn.disabled = false;

            break;

    }

}

function initialiseSurveyDashboard(){

    document.getElementById("surveyArea").innerHTML = "0.000";

    document.getElementById("surveyPerimeter").innerHTML = "0.0";

    document.getElementById("surveyPoints").innerHTML = "0";

    document.getElementById("surveyDistance").innerHTML = "0.0";

    document.getElementById("surveyTime").innerHTML = "00:00:00";

    document.getElementById("currentAccuracy").innerHTML = "0.0";

    document.getElementById("averageAccuracy").innerHTML = "0.0";

    document.getElementById("gpsQualityStatus").innerHTML = "★★★★★";

}