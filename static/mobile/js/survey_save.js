/* ==========================================================
   DCGL FIELDMATE
   Survey Save Module
   Version 2.0
========================================================== */

function saveSurvey(area, perimeter, polygon){

    //------------------------------------------------------
    // Retrieve Survey Details saved by survey_details.js
    //------------------------------------------------------

    const details = JSON.parse(

        sessionStorage.getItem("dcglSurvey") || "{}"

    );

    //------------------------------------------------------
    // Build Survey Object
    //------------------------------------------------------

    const survey = {

        survey_type: details.survey_type,

        parent: details.parent,

        field: details.field,

        crop: details.crop,

        soil: details.soil,

        season: details.season,

        surveyor: details.surveyor,

        area: area / 10000,

        perimeter: perimeter,

        geojson: polygon.exportGeoJSON()

    };

    console.log("Saving Survey...");

    console.log(survey);

    //------------------------------------------------------
    // Send to Flask
    //------------------------------------------------------

    fetch("/mobile/save_survey", {

        method: "POST",

        headers: {

            "Content-Type": "application/json"

        },

        body: JSON.stringify(survey)

    })

    .then(response => response.json())

    .then(data => {

        alert(data.message);

        console.log(data);

    })

    .catch(error => {

        console.error(error);

        alert("Unable to save survey.");

    });

}