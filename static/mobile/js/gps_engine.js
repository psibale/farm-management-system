/* ===========================================================
   DCGL GPS ENGINE
   Enterprise GPS Module
   Version: 1.0
=========================================================== */

class GpsEngine {

    constructor() {

        this.watchId = null;

        this.state = "STOPPED";

        this.current = null;

        this.points = [];

        this.statistics = {

            startTime: null,
            elapsedSeconds: 0,

            distance: 0,

            bestAccuracy: null,
            worstAccuracy: null,
            averageAccuracy: 0,

            pointCount: 0

        };

        this.callbacks = [];

    }

    //--------------------------------------------------------
    // Subscribe to GPS updates
    //--------------------------------------------------------

    onUpdate(callback){

        this.callbacks.push(callback);

    }

    //--------------------------------------------------------
    // Notify listeners
    //--------------------------------------------------------

    notify(){

        this.callbacks.forEach(cb=>{

            cb(this);

        });

    }

    //--------------------------------------------------------
    // Start GPS
    //--------------------------------------------------------

    start(){

        if(!navigator.geolocation){

            alert("GPS not supported.");

            return;

        }

        this.state="SEARCHING";

        this.notify();

        this.watchId=navigator.geolocation.watchPosition(

            this.positionSuccess.bind(this),

            this.positionError.bind(this),

            {

                enableHighAccuracy:true,

                timeout:10000,

                maximumAge:0

            }

        );

    }

    //--------------------------------------------------------
    // Stop GPS
    //--------------------------------------------------------

    stop(){

        if(this.watchId){

            navigator.geolocation.clearWatch(this.watchId);

            this.watchId=null;

        }

        this.state="STOPPED";

        this.notify();

    }

    //--------------------------------------------------------
    // Successful GPS Fix
    //--------------------------------------------------------

    positionSuccess(position){

        const c=position.coords;

        this.current={

            latitude:c.latitude,

            longitude:c.longitude,

            accuracy:c.accuracy,

            altitude:c.altitude,

            heading:c.heading,

            speed:c.speed,

            timestamp:position.timestamp

        };

        //----------------------------------------------------
        // GPS Ready
        //----------------------------------------------------

        if(this.state==="SEARCHING"){

            this.state="READY";

            this.statistics.startTime=Date.now();

        }

        //----------------------------------------------------
        // Accuracy Statistics
        //----------------------------------------------------

        const a=c.accuracy;

        if(this.statistics.bestAccuracy===null || a<this.statistics.bestAccuracy)

            this.statistics.bestAccuracy=a;

        if(this.statistics.worstAccuracy===null || a>this.statistics.worstAccuracy)

            this.statistics.worstAccuracy=a;

        //----------------------------------------------------
        // Recording
        //----------------------------------------------------

        if(this.state==="RECORDING"){

            this.recordPoint();

        }

        //----------------------------------------------------
        // Elapsed Time
        //----------------------------------------------------

        if(this.statistics.startTime){

            this.statistics.elapsedSeconds=

                Math.floor(

                    (Date.now()-this.statistics.startTime)/1000

                );

        }

        this.notify();

    }

    //--------------------------------------------------------
    // GPS Error
    //--------------------------------------------------------

    positionError(error){

        console.log(error);

        this.state="ERROR";

        this.notify();

    }

    //--------------------------------------------------------
    // Begin Survey
    //--------------------------------------------------------

    startRecording(){

        this.points=[];

        this.statistics.distance=0;

        this.statistics.pointCount=0;

        this.state="RECORDING";

        this.notify();

    }

    //--------------------------------------------------------
    // Pause Survey
    //--------------------------------------------------------

    pause(){

        this.state="READY";

        this.notify();

    }

    //--------------------------------------------------------
    // Record GPS Point
    //--------------------------------------------------------

    recordPoint(){

        if(!this.current) return;

        const p={...this.current};

        //----------------------------------------------------
        // Distance
        //----------------------------------------------------

        if(this.points.length>0){

            const prev=this.points[this.points.length-1];

            const d=this.calculateDistance(

                prev.latitude,

                prev.longitude,

                p.latitude,

                p.longitude

            );

            this.statistics.distance+=d;

        }

        this.points.push(p);

        this.statistics.pointCount=this.points.length;

        //----------------------------------------------------
        // Average Accuracy
        //----------------------------------------------------

        const total=this.points.reduce(

            (sum,x)=>sum+x.accuracy,

            0

        );

        this.statistics.averageAccuracy=

            total/this.points.length;

    }

    //--------------------------------------------------------
    // Haversine Distance
    //--------------------------------------------------------

    calculateDistance(lat1,lon1,lat2,lon2){

        const R=6371000;

        const dLat=(lat2-lat1)*Math.PI/180;

        const dLon=(lon2-lon1)*Math.PI/180;

        const a=

            Math.sin(dLat/2)**2+

            Math.cos(lat1*Math.PI/180)*

            Math.cos(lat2*Math.PI/180)*

            Math.sin(dLon/2)**2;

        return R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));

    }

    //--------------------------------------------------------
    // GPS Quality
    //--------------------------------------------------------

    quality(){

        if(!this.current) return "Unknown";

        const a=this.current.accuracy;

        if(a<=2) return "★★★★★ Excellent";

        if(a<=5) return "★★★★ Good";

        if(a<=10) return "★★★ Fair";

        if(a<=20) return "★★ Poor";

        return "★ Very Poor";

    }

}