/* ==========================================================
   DCGL FIELDMATE
   Survey Review
   Version 3.0

   OFFLINE-FIRST SURVEY REVIEW

   FEATURES
   ----------------------------------------------------------
   - Loads survey from sessionStorage
   - Falls back to IndexedDB when available
   - Displays survey results offline
   - Displays cached parent-area information offline
   - Online parent-area refresh
   - Does NOT fail the survey review when LAN is unavailable
   - Survey validation
   - Survey quality scoring
   - Save / continue / discard
========================================================== */


let survey = {};

let reviewMap = null;

let parentAreaData = null;


/* ==========================================================
   LOAD SURVEY
========================================================== */

async function loadSurvey() {

    //------------------------------------------------------
    // FIRST: SESSION STORAGE
    //------------------------------------------------------

    const saved =
        sessionStorage.getItem("dcglSurvey");


    if (saved) {

        try {

            survey =
                JSON.parse(saved);

            console.log(
                "Survey loaded from sessionStorage."
            );

        }

        catch (error) {

            console.error(
                "Invalid survey data in sessionStorage:",
                error
            );

            survey = {};

        }

    }


    //------------------------------------------------------
    // SECOND: INDEXEDDB FALLBACK
    //------------------------------------------------------

    if (
        !survey ||
        Object.keys(survey).length === 0
    ) {

        try {

            if (
                typeof getOfflineSurvey === "function"
            ) {

                const offlineSurveys =
                    await getAllOfflineSurveys();


                if (
                    offlineSurveys &&
                    offlineSurveys.length > 0
                ) {

                    /*
                     * Use the most recently created survey.
                     */

                    offlineSurveys.sort(
                        (a, b) => {

                            return new Date(
                                b.created_at || 0
                            ) -
                            new Date(
                                a.created_at || 0
                            );

                        }
                    );


                    survey =
                        offlineSurveys[0];


                    console.log(
                        "Survey loaded from IndexedDB:",
                        survey.survey_id
                    );

                }

            }

        }

        catch (error) {

            console.warn(
                "Unable to load survey from IndexedDB:",
                error
            );

        }

    }


    //------------------------------------------------------
    // NO SURVEY
    //------------------------------------------------------

    if (
        !survey ||
        Object.keys(survey).length === 0
    ) {

        alert(
            "No survey found."
        );

        window.location.href =
            "/mobile";

        return;

    }


    //------------------------------------------------------
    // DISPLAY SURVEY
    //------------------------------------------------------

    displaySurveyInformation();


    //------------------------------------------------------
    // DRAW MAP
    //------------------------------------------------------

    drawPolygon();


    //------------------------------------------------------
    // VALIDATE SURVEY
    //------------------------------------------------------

    showValidationReport();


    //------------------------------------------------------
    // LOAD PARENT AREA
    //------------------------------------------------------

    await loadParentArea();


    //------------------------------------------------------
    // FINAL VALIDATION
    //------------------------------------------------------

    showValidationReport();

}


/* ==========================================================
   DISPLAY SURVEY INFORMATION
========================================================== */

function displaySurveyInformation() {

    //------------------------------------------------------
    // SURVEY INFORMATION
    //------------------------------------------------------

    const surveyType =
        document.getElementById(
            "reviewSurveyType"
        );

    const parent =
        document.getElementById(
            "reviewParent"
        );

    const field =
        document.getElementById(
            "reviewField"
        );

    const season =
        document.getElementById(
            "reviewSeason"
        );

    const surveyor =
        document.getElementById(
            "reviewSurveyor"
        );


    if (surveyType) {

        surveyType.innerHTML =
            survey.survey_type || "";

    }


    if (parent) {

        parent.innerHTML =
            survey.parent || "-";

    }


    if (field) {

        field.innerHTML =
            survey.field || "";

    }


    if (season) {

        season.innerHTML =
            survey.season || "";

    }


    if (surveyor) {

        surveyor.innerHTML =
            survey.surveyor || "";

    }


    //------------------------------------------------------
    // SURVEY RESULTS
    //------------------------------------------------------

    const area =
        document.getElementById(
            "reviewArea"
        );

    const perimeter =
        document.getElementById(
            "reviewPerimeter"
        );

    const distance =
        document.getElementById(
            "reviewDistance"
        );

    const points =
        document.getElementById(
            "reviewPoints"
        );

    const time =
        document.getElementById(
            "reviewTime"
        );

    const accuracy =
        document.getElementById(
            "reviewAccuracy"
        );


    if (area) {

        area.innerHTML =
            Number(
                survey.area || 0
            ).toFixed(3);

    }


    if (perimeter) {

        perimeter.innerHTML =
            Number(
                survey.perimeter || 0
            ).toFixed(1);

    }


    if (distance) {

        distance.innerHTML =
            Number(
                survey.distance || 0
            ).toFixed(1);

    }


    if (points) {

        points.innerHTML =
            survey.points || 0;

    }


    if (time) {

        time.innerHTML =
            survey.time ||
            "00:00:00";

    }


    if (accuracy) {

        accuracy.innerHTML =
            "±" +
            Number(
                survey.average_accuracy || 0
            ).toFixed(1);

    }

}


/* ==========================================================
   DRAW POLYGON
========================================================== */

function drawPolygon() {

    //------------------------------------------------------
    // NO GEOJSON
    //------------------------------------------------------

    if (!survey.geojson) {

        console.warn(
            "No GeoJSON available for survey."
        );

        return;

    }


    //------------------------------------------------------
    // PREVENT DUPLICATE MAP
    //------------------------------------------------------

    const mapElement =
        document.getElementById(
            "reviewMap"
        );


    if (!mapElement) {

        console.warn(
            "Review map element not found."
        );

        return;

    }


    if (reviewMap) {

        reviewMap.remove();

        reviewMap = null;

    }


    //------------------------------------------------------
    // CREATE MAP
    //------------------------------------------------------

    reviewMap =
        L.map(
            "reviewMap"
        );


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

    let polygon;


    try {

        polygon =
            L.geoJSON(

                survey.geojson,

                {

                    style: {

                        color:
                            "#198754",

                        weight:
                            4,

                        fillOpacity:
                            0.30

                    }

                }

            ).addTo(reviewMap);

    }

    catch (error) {

        console.error(
            "Unable to draw survey GeoJSON:",
            error
        );

        return;

    }


    //------------------------------------------------------
    // ZOOM TO SURVEY
    //------------------------------------------------------

    if (
        polygon &&
        polygon.getBounds().isValid()
    ) {

        reviewMap.fitBounds(

            polygon.getBounds(),

            {

                padding:
                    [20, 20]

            }

        );

    }

}


/* ==========================================================
   VALIDATION REPORT
========================================================== */

function showValidationReport() {

    //------------------------------------------------------
    // VALIDATOR CHECK
    //------------------------------------------------------

    if (
        typeof SurveyValidator ===
        "undefined"
    ) {

        console.error(
            "SurveyValidator is not loaded."
        );

        return;

    }


    //------------------------------------------------------
    // VALIDATE
    //------------------------------------------------------

    const result =
        SurveyValidator.validate(
            survey
        );


    console.log(
        "VALIDATION RESULT:",
        result
    );


    //------------------------------------------------------
    // BUILD REPORT
    //------------------------------------------------------

    let html = "";


    if (
        result.checks &&
        Array.isArray(result.checks)
    ) {

        result.checks.forEach(
            check => {

                let icon =
                    "🟢";

                let className =
                    "validation-pass";


                //--------------------------------------------------
                // FAILED CHECK
                //--------------------------------------------------

                if (
                    !check.passed
                ) {

                    icon =
                        "🔴";

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

                    icon =
                        "🟡";

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

            }
        );

    }


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

        Number(
            result.score || 0
        ),

        result.status || ""

    );

}


/* ==========================================================
   SURVEY QUALITY DISPLAY
========================================================== */

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
    // SCORE BOX
    //------------------------------------------------------

    if (box) {

        box.style.background =
            background;

    }

}


/* ==========================================================
   SAVE SURVEY
========================================================== */

const saveSurveyButton =
    document.getElementById(
        "saveSurvey"
    );


if (saveSurveyButton) {

    saveSurveyButton.onclick =
        async function () {

            //--------------------------------------------------
            // VALIDATOR
            //--------------------------------------------------

            if (
                typeof SurveyValidator ===
                "undefined"
            ) {

                console.error(
                    "SurveyValidator is not loaded."
                );

                alert(
                    "Survey validation module is not loaded."
                );

                return;

            }


            //--------------------------------------------------
            // VALIDATE
            //--------------------------------------------------

            const result =
                SurveyValidator.validate(
                    survey
                );


            console.log(
                "SURVEY SAVE VALIDATION:",
                result
            );


            //--------------------------------------------------
            // REVIEW REQUIRED
            //--------------------------------------------------

            if (
                result.score < 70
            ) {

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


            //--------------------------------------------------
            // ACCEPTABLE
            //--------------------------------------------------

            if (

                result.score >= 70 &&
                result.score < 80

            ) {

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


                if (!confirmed) {

                    return;

                }

            }


            //--------------------------------------------------
            // GOOD / EXCELLENT
            //--------------------------------------------------

            if (
                result.score >= 80
            ) {

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


                if (!confirmed) {

                    return;

                }

            }


            //--------------------------------------------------
            // SAVE MODULE
            //--------------------------------------------------

            if (
                typeof saveSurvey ===
                "function"
            ) {

                console.log(
                    "Survey validation passed. Saving survey..."
                );


                try {

                    await saveSurvey();

                }

                catch (error) {

                    console.error(
                        "Survey save error:",
                        error
                    );

                    alert(
                        "Unable to save the survey.\n\n" +
                        "The survey remains stored locally."
                    );

                }

            }

            else {

                console.error(
                    "saveSurvey() function not found."
                );

                alert(
                    "Survey save module is not loaded."
                );

            }

        };

}


/* ==========================================================
   CONTINUE SURVEY
========================================================== */

const continueSurveyButton =
    document.getElementById(
        "continueSurvey"
    );


if (continueSurveyButton) {

    continueSurveyButton.onclick =
        function () {

            window.history.back();

        };

}


/* ==========================================================
   DISCARD SURVEY
========================================================== */

const discardSurveyButton =
    document.getElementById(
        "discardSurvey"
    );


if (discardSurveyButton) {

    discardSurveyButton.onclick =
        function () {

            if (

                confirm(

                    "Discard this survey?\n\n" +

                    "All unsaved survey information will be removed."

                )

            ) {

                sessionStorage.removeItem(
                    "dcglSurvey"
                );


                window.location.href =
                    "/mobile";

            }

        };

}


/* ==========================================================
   LOAD PARENT AREA INFORMATION
========================================================== */

async function loadParentArea() {

    //------------------------------------------------------
    // ONLY REQUIRED FOR SUB-FIELDS
    //------------------------------------------------------

    if (
        survey.survey_type !==
        "Sub-field"
    ) {

        console.log(
            "Parent area not required."
        );

        return;

    }


    //------------------------------------------------------
    // NO PARENT
    //------------------------------------------------------

    if (!survey.parent) {

        console.warn(
            "Sub-field survey has no parent field."
        );

        return;

    }


    //------------------------------------------------------
    // FIRST: USE DATA ALREADY IN SURVEY
    //------------------------------------------------------

    if (

        survey.parent_area !==
        undefined &&

        survey.previously_surveyed !==
        undefined &&

        survey.remaining_area !==
        undefined

    ) {

        parentAreaData = {

            success:
                true,

            parent_area:
                survey.parent_area,

            surveyed_area:
                survey.previously_surveyed,

            remaining_area:
                survey.remaining_area

        };


        console.log(
            "Using parent-area information already stored in survey."
        );


        return;

    }


    //------------------------------------------------------
    // ONLINE CHECK
    //------------------------------------------------------

    if (
        !navigator.onLine
    ) {

        console.warn(
            "Phone is offline. Parent area cannot be refreshed."
        );

        return;

    }


    //------------------------------------------------------
    // REQUEST FLASK
    //------------------------------------------------------

    try {

        const response =
            await fetch(

                `/mobile/parent_area/${encodeURIComponent(
                    survey.parent
                )}`,

                {

                    method:
                        "GET",

                    cache:
                        "no-store",

                    credentials:
                        "same-origin"

                }

            );


        //--------------------------------------------------
        // HTTP ERROR
        //--------------------------------------------------

        if (
            !response.ok
        ) {

            throw new Error(
                "HTTP " +
                response.status
            );

        }


        //--------------------------------------------------
        // JSON
        //--------------------------------------------------

        const data =
            await response.json();


        //--------------------------------------------------
        // SERVER FAILURE
        //--------------------------------------------------

        if (
            !data.success
        ) {

            console.warn(
                "Parent area unavailable:",
                data.message
            );

            return;

        }


        //--------------------------------------------------
        // STORE DATA
        //--------------------------------------------------

        parentAreaData =
            data;


        survey.parent_area =
            data.parent_area;

        survey.previously_surveyed =
            data.surveyed_area;

        survey.remaining_area =
            data.remaining_area;


        //--------------------------------------------------
        // UPDATE SESSION STORAGE
        //--------------------------------------------------

        sessionStorage.setItem(

            "dcglSurvey",

            JSON.stringify(
                survey
            )

        );


        console.log(
            "Parent-area information refreshed from Flask."
        );


        //--------------------------------------------------
        // VALIDATE AGAIN
        //--------------------------------------------------

        showValidationReport();

    }


    catch (error) {

        /*
         * IMPORTANT:
         *
         * This is NOT a fatal survey error.
         *
         * The survey can still be reviewed offline.
         */

        console.warn(
            "Unable to refresh parent area. " +
            "Continuing with locally available survey information.",
            error
        );

    }

}


/* ==========================================================
   START
========================================================== */

loadSurvey();