/* ==========================================================
   DCGL AREA CALCULATOR
========================================================== */

class AreaCalculator {

    //------------------------------------------------------
    // Polygon Area (Shoelace Formula)
    //------------------------------------------------------

    static calculate(points){

        if(points.length < 3)
            return 0;

        let area = 0;

        const coords = points.map(p=>{

            return this.latLngToMeters(
                p.lat,
                p.lng
            );

        });

        for(let i=0;i<coords.length;i++){

            let j = (i+1)%coords.length;

            area +=
                coords[i].x*coords[j].y
                -
                coords[j].x*coords[i].y;

        }

        return Math.abs(area/2);

    }

    //------------------------------------------------------
    // Perimeter
    //------------------------------------------------------

    static perimeter(points){

        if(points.length<2)
            return 0;

        let p=0;

        for(let i=1;i<points.length;i++){

            p+=this.distance(

                points[i-1],

                points[i]

            );

        }

        return p;

    }

    //------------------------------------------------------
    // Haversine Distance
    //------------------------------------------------------

    static distance(a,b){

        const R=6378137;

        const dLat=(b.lat-a.lat)*Math.PI/180;

        const dLng=(b.lng-a.lng)*Math.PI/180;

        const sa=Math.sin(dLat/2);

        const sb=Math.sin(dLng/2);

        const h=

            sa*sa+

            Math.cos(a.lat*Math.PI/180)*

            Math.cos(b.lat*Math.PI/180)*

            sb*sb;

        return 2*R*Math.atan2(

            Math.sqrt(h),

            Math.sqrt(1-h)

        );

    }

    //------------------------------------------------------
    // Convert LatLng → Meters
    //------------------------------------------------------

    static latLngToMeters(lat,lng){

        const R=6378137;

        return{

            x:R*lng*Math.PI/180,

            y:R*Math.log(

                Math.tan(

                    Math.PI/4+

                    lat*Math.PI/360

                )

            )

        };

    }

}