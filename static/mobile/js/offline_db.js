/* ==========================================================
   DCGL FIELDMATE
   Offline Survey Database
   Version 1.0
========================================================== */

const DCGL_OFFLINE_DB = "DCGL_FieldMate_DB";
const DCGL_OFFLINE_STORE = "surveyQueue";
const DCGL_OFFLINE_VERSION = 1;


// ==========================================================
// OPEN DATABASE
// ==========================================================

function openOfflineDatabase() {

    return new Promise((resolve, reject) => {

        const request = indexedDB.open(
            DCGL_OFFLINE_DB,
            DCGL_OFFLINE_VERSION
        );


        //------------------------------------------------------
        // CREATE DATABASE
        //------------------------------------------------------

        request.onupgradeneeded = function(event) {

            const db = event.target.result;


            if (!db.objectStoreNames.contains(DCGL_OFFLINE_STORE)) {

                const store =
                    db.createObjectStore(
                        DCGL_OFFLINE_STORE,
                        {
                            keyPath: "survey_id"
                        }
                    );


                store.createIndex(
                    "sync_status",
                    "sync_status",
                    {
                        unique: false
                    }
                );


                store.createIndex(
                    "created_at",
                    "created_at",
                    {
                        unique: false
                    }
                );

            }

        };


        //------------------------------------------------------
        // SUCCESS
        //------------------------------------------------------

        request.onsuccess = function(event) {

            resolve(event.target.result);

        };


        //------------------------------------------------------
        // ERROR
        //------------------------------------------------------

        request.onerror = function(event) {

            console.error(
                "Offline database error:",
                event.target.error
            );

            reject(event.target.error);

        };

    });

}


// ==========================================================
// CREATE UNIQUE SURVEY ID
// ==========================================================

function generateSurveyID() {

    return (
        "DCGL-" +
        Date.now() +
        "-" +
        Math.random()
            .toString(36)
            .substring(2, 10)
            .toUpperCase()
    );

}


// ==========================================================
// SAVE SURVEY OFFLINE
// ==========================================================

async function saveSurveyOffline(survey) {

    const db =
        await openOfflineDatabase();


    //------------------------------------------------------
    // MAKE A COPY
    //------------------------------------------------------

    const record = {

        ...survey,

        survey_id:
            survey.survey_id ||
            generateSurveyID(),

        created_at:
            survey.created_at ||
            new Date().toISOString(),

        sync_status: "pending",

        sync_attempts:
            Number(survey.sync_attempts || 0),

        last_sync_attempt: null,

        last_sync_error: null

    };


    //------------------------------------------------------
    // SAVE
    //------------------------------------------------------

    return new Promise((resolve, reject) => {

        const transaction =
            db.transaction(
                [DCGL_OFFLINE_STORE],
                "readwrite"
            );


        const store =
            transaction.objectStore(
                DCGL_OFFLINE_STORE
            );


        const request =
            store.put(record);


        request.onsuccess = function() {

            console.log(
                "Survey saved offline:",
                record.survey_id
            );

            resolve(record);

        };


        request.onerror = function(event) {

            console.error(
                "Unable to save survey offline:",
                event.target.error
            );

            reject(event.target.error);

        };

    });

}


// ==========================================================
// GET ALL PENDING SURVEYS
// ==========================================================

async function getPendingSurveys() {

    const db =
        await openOfflineDatabase();


    return new Promise((resolve, reject) => {

        const transaction =
            db.transaction(
                [DCGL_OFFLINE_STORE],
                "readonly"
            );


        const store =
            transaction.objectStore(
                DCGL_OFFLINE_STORE
            );


        const index =
            store.index("sync_status");


        const request =
            index.getAll("pending");


        request.onsuccess = function() {

            resolve(
                request.result || []
            );

        };


        request.onerror = function(event) {

            reject(event.target.error);

        };

    });

}


// ==========================================================
// MARK SURVEY AS SYNCED
// ==========================================================

async function markSurveySynced(surveyID) {

    const db =
        await openOfflineDatabase();


    return new Promise((resolve, reject) => {

        const transaction =
            db.transaction(
                [DCGL_OFFLINE_STORE],
                "readwrite"
            );


        const store =
            transaction.objectStore(
                DCGL_OFFLINE_STORE
            );


        const request =
            store.get(surveyID);


        request.onsuccess = function() {

            const survey =
                request.result;


            if (!survey) {

                resolve();

                return;

            }


            survey.sync_status = "synced";

            survey.synced_at =
                new Date().toISOString();


            store.put(survey);


            resolve();

        };


        request.onerror = function(event) {

            reject(event.target.error);

        };

    });

}


// ==========================================================
// MARK SURVEY AS FAILED
// ==========================================================

async function markSurveyFailed(
    surveyID,
    errorMessage
) {

    const db =
        await openOfflineDatabase();


    return new Promise((resolve, reject) => {

        const transaction =
            db.transaction(
                [DCGL_OFFLINE_STORE],
                "readwrite"
            );


        const store =
            transaction.objectStore(
                DCGL_OFFLINE_STORE
            );


        const request =
            store.get(surveyID);


        request.onsuccess = function() {

            const survey =
                request.result;


            if (!survey) {

                resolve();

                return;

            }


            survey.sync_status = "pending";

            survey.sync_attempts =
                Number(
                    survey.sync_attempts || 0
                ) + 1;

            survey.last_sync_attempt =
                new Date().toISOString();

            survey.last_sync_error =
                String(errorMessage || "Unknown error");


            store.put(survey);


            resolve();

        };


        request.onerror = function(event) {

            reject(event.target.error);

        };

    });

}


// ==========================================================
// COUNT PENDING SURVEYS
// ==========================================================

async function getPendingSurveyCount() {

    const surveys =
        await getPendingSurveys();

    return surveys.length;

}