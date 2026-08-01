let map;

let marker;

function startGPS(){

    if(!navigator.geolocation){

        alert("GPS not supported");

        return;

    }

    navigator.geolocation.watchPosition(

        updatePosition,

        gpsError,

        {

            enableHighAccuracy:true,

            maximumAge:0,

            timeout:10000

        }

    );

}

function updatePosition(position){

    const lat = position.coords.latitude;

    const lng = position.coords.longitude;

    const acc = position.coords.accuracy;

    document.getElementById("lat").innerHTML =
        lat.toFixed(6);

    document.getElementById("lng").innerHTML =
        lng.toFixed(6);

    document.getElementById("accuracy").innerHTML =
        acc.toFixed(1) + " m";

    if(!map){

        map = L.map('map').setView([lat,lng],18);

        L.tileLayer(

            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',

            {

                maxZoom:22

            }

        ).addTo(map);

        marker = L.marker([lat,lng]).addTo(map);

    }

    else{

        marker.setLatLng([lat,lng]);

        map.panTo([lat,lng]);

    }

}

function gpsError(error){

    alert(error.message);

}