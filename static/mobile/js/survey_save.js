/* ==========================================================
   DCGL FIELDMATE
   Survey Save Module
   Version 3.0
========================================================== */

function saveSurvey(){

    //------------------------------------------------------
    // Retrieve completed survey
    //------------------------------------------------------

    const survey = JSON.parse(

        sessionStorage.getItem("dcglSurvey") || "{}"

    );

    if(!survey.field){

        alert("No survey available.");

        return;

    }

    console.log("Saving Survey...");

    console.log(survey);

    //------------------------------------------------------
    // Send to Flask
    //------------------------------------------------------

    fetch("/mobile/save_survey",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify(survey)

    })

    .then(response=>response.json())

    .then(data=>{

        alert(data.message);

        console.log(data);

        if(data.success){

            sessionStorage.removeItem("dcglSurvey");

            window.location.href="/mobile";

        }

    })

    .catch(error=>{

        console.error(error);

        alert("Unable to save survey.");

    });

}