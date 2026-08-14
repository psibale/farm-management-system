/* ==========================================================
   DCGL FIELDMATE
   Offline Survey Database
   Version 2.0
========================================================== */

const DCGL_OFFLINE_DB = "DCGL_FieldMate_DB";
const DCGL_OFFLINE_STORE = "surveyQueue";
const DCGL_OFFLINE_VERSION = 2;


// ==========================================================
// OPEN DATABASE
// ==========================================================

function openOfflineDatabase() {

    return new Promise((resolve, reject) => {

        const request = indexedDB.open(
            DCGL_OFFLINE_DB,
            DCGL_OFFLINE_VERSION
        );


        // --------------------------------------------------
        // DATABASE UPGRADE
        // --------------------------------------------------

        request.onupgradeneeded = function(event) {

            const db = event.target.result;

            let store;


            //------------------------------------------------
            // CREATE STORE
            //------------------------------------------------

            if (
                !db.objectStoreNames.contains(
                    DCGL_OFFLINE_STORE
                )
            ) {

                store =
                    db.createObjectStore(
                        DCGL_OFFLINE_STORE,
                        {
                            keyPath: "survey_id"
                        }
                    );

            }

            else {

                store =
                    event.target.transaction.objectStore(
                        DCGL_OFFLINE_STORE
                    );

            }


            //------------------------------------------------
            // INDEX: SYNC STATUS
            //------------------------------------------------

            if (
                !store.indexNames.contains(
                    "sync_status"
                )
            ) {

                store.createIndex(
                    "sync_status",
                    "sync_status",
                    {
                        unique: false
                    }
                );

            }


            //------------------------------------------------
            // INDEX: CREATED DATE
            //------------------------------------------------

            if (
                !store.indexNames.contains(
                    "created_at"
                )
            ) {

                store.createIndex(
                    "created_at",
                    "created_at",
                    {
                        unique: false
                    }
                );

            }


            //------------------------------------------------
            // INDEX: FIELD
            //------------------------------------------------

            if (
                !store.indexNames.contains(
                    "field"
                )
            ) {

                store.createIndex(
                    "field",
                    "field",
                    {
                        unique: false
                    }
                );

            }


            console.log(
                "DCGL FieldMate offline database upgraded."
            );

        };


        // --------------------------------------------------
        // SUCCESS
        // --------------------------------------------------

        request.onsuccess = function(event) {

            const db = event.target.result;


            //------------------------------------------------
            // HANDLE UNEXPECTED VERSION CHANGES
            //------------------------------------------------

            db.onversionchange = function() {

                db.close();

                console.warn(
                    "Offline database connection closed " +
                    "because another version was opened."
                );

            };


            resolve(db);

        };


        // --------------------------------------------------
        // ERROR
        // --------------------------------------------------

        request.onerror = function(event) {

            console.error(
                "Offline database error:",
                event.target.error
            );

            reject(
                event.target.error
            );

        };


        // --------------------------------------------------
        // BLOCKED
        // --------------------------------------------------

        request.onblocked = function() {

            console.warn(
                "Offline database upgrade is blocked. " +
                "Please close other FieldMate tabs."
            );

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
// PREPARE SURVEY RECORD
// ==========================================================

function prepareOfflineSurvey(survey) {

    const now =
        new Date().toISOString();


    const record = {

        //--------------------------------------------------
        // ORIGINAL SURVEY DATA
        //--------------------------------------------------

        ...survey,


        //--------------------------------------------------
        // UNIQUE ID
        //--------------------------------------------------

        survey_id:

            survey.survey_id ||

            generateSurveyID(),


        //--------------------------------------------------
        // CREATED DATE
        //--------------------------------------------------

        created_at:

            survey.created_at ||

            now,


        //--------------------------------------------------
        // LAST UPDATED
        //--------------------------------------------------

        updated_at:

            now,


        //--------------------------------------------------
        // SYNC INFORMATION
        //--------------------------------------------------

        sync_status:
            "pending",

        sync_attempts:

            Number(
                survey.sync_attempts || 0
            ),

        last_sync_attempt:
            survey.last_sync_attempt || null,

        last_sync_error:
            survey.last_sync_error || null,

        synced_at:
            survey.synced_at || null

    };


    return record;

}


// ==========================================================
// SAVE SURVEY OFFLINE
// ==========================================================

async function saveSurveyOffline(survey) {

    if (!survey) {

        throw new Error(
            "No survey supplied."
        );

    }


    const db =
        await openOfflineDatabase();


    const record =
        prepareOfflineSurvey(survey);


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


        //--------------------------------------------------
        // SAVE / UPDATE
        //--------------------------------------------------

        const request =
            store.put(record);


        request.onsuccess = function() {

            console.log(
                "Survey saved offline:",
                record.survey_id
            );

        };


        //--------------------------------------------------
        // TRANSACTION COMPLETE
        //--------------------------------------------------

        transaction.oncomplete = function() {

            db.close();

            resolve(record);

        };


        //--------------------------------------------------
        // TRANSACTION ERROR
        //--------------------------------------------------

        transaction.onerror = function(event) {

            db.close();

            console.error(
                "Offline save transaction failed:",
                event.target.error
            );

            reject(
                event.target.error
            );

        };


        transaction.onabort = function(event) {

            db.close();

            reject(
                event.target.error ||
                new Error(
                    "Offline save transaction aborted."
                )
            );

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

            reject(
                event.target.error
            );

        };


        transaction.oncomplete = function() {

            db.close();

        };


        transaction.onerror = function(event) {

            db.close();

            reject(
                event.target.error
            );

        };

    });

}


// ==========================================================
// GET ALL OFFLINE SURVEYS
// ==========================================================

async function getAllOfflineSurveys() {

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


        const request =
            store.getAll();


        request.onsuccess = function() {

            resolve(
                request.result || []
            );

        };


        request.onerror = function(event) {

            reject(
                event.target.error
            );

        };


        transaction.oncomplete = function() {

            db.close();

        };


        transaction.onerror = function(event) {

            db.close();

            reject(
                event.target.error
            );

        };

    });

}


// ==========================================================
// GET ONE SURVEY
// ==========================================================

async function getOfflineSurvey(surveyID) {

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


        const request =
            store.get(surveyID);


        request.onsuccess = function() {

            resolve(
                request.result || null
            );

        };


        request.onerror = function(event) {

            reject(
                event.target.error
            );

        };


        transaction.oncomplete = function() {

            db.close();

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

                return;

            }


            survey.sync_status =
                "synced";


            survey.synced_at =
                new Date().toISOString();


            survey.last_sync_error =
                null;


            store.put(survey);

        };


        request.onerror = function(event) {

            reject(
                event.target.error
            );

        };


        transaction.oncomplete = function() {

            db.close();

            resolve();

        };


        transaction.onerror = function(event) {

            db.close();

            reject(
                event.target.error
            );

        };

    });

}


// ==========================================================
// DELETE SYNCHRONIZED SURVEY
// ==========================================================

async function deleteOfflineSurvey(surveyID) {

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


        store.delete(surveyID);


        transaction.oncomplete = function() {

            db.close();

            console.log(
                "Offline survey removed:",
                surveyID
            );

            resolve();

        };


        transaction.onerror = function(event) {

            db.close();

            reject(
                event.target.error
            );

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

                return;

            }


            survey.sync_status =
                "pending";


            survey.sync_attempts =

                Number(
                    survey.sync_attempts || 0
                ) + 1;


            survey.last_sync_attempt =
                new Date().toISOString();


            survey.last_sync_error =
                String(
                    errorMessage ||
                    "Unknown synchronization error."
                );


            survey.updated_at =
                new Date().toISOString();


            store.put(survey);

        };


        request.onerror = function(event) {

            reject(
                event.target.error
            );

        };


        transaction.oncomplete = function() {

            db.close();

            resolve();

        };


        transaction.onerror = function(event) {

            db.close();

            reject(
                event.target.error
            );

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


// ==========================================================
// COUNT ALL OFFLINE SURVEYS
// ==========================================================

async function getOfflineSurveyCount() {

    const surveys =
        await getAllOfflineSurveys();

    return surveys.length;

}


// ==========================================================
// CLEAR SYNCHRONIZED SURVEYS
// ==========================================================

async function clearSyncedSurveys() {

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


        const index =
            store.index("sync_status");


        const request =
            index.openCursor("synced");


        request.onsuccess = function(event) {

            const cursor =
                event.target.result;


            if (!cursor) {

                return;

            }


            cursor.delete();

            cursor.continue();

        };


        request.onerror = function(event) {

            reject(
                event.target.error
            );

        };


        transaction.oncomplete = function() {

            db.close();

            resolve();

        };


        transaction.onerror = function(event) {

            db.close();

            reject(
                event.target.error
            );

        };

    });

}