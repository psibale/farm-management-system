"""
GIS Dashboard Statistics

Provides GIS KPIs for Farm Management Dashboard
"""

from .audit import GISAudit


class GISDashboard:


    @staticmethod
    def get_summary():

        from modules.gis_engine.audit import GISAudit

        results = GISAudit.run_audit()


        total_fields = len(results)


        valid_fields = sum(
            1 for r in results
            if r["valid"]
        )


        total_area = round(
            sum(
                r["gis_area"]
                for r in results
            ),
            2
        )


        average_quality = round(

            sum(
                r["quality"]
                for r in results
            )
            /
            total_fields,

            1

        ) if total_fields else 0


        review_fields = [

            r

            for r in results

            if r["quality"] < 100

        ]


        quality_distribution = {

            "100":

                sum(
                    1 for r in results
                    if r["quality"] == 100
                ),

            "95":

                sum(
                    1 for r in results
                    if r["quality"] == 95
                ),

            "90":

                sum(
                    1 for r in results
                    if r["quality"] == 90
                ),

            "below90":

                sum(
                    1 for r in results
                    if r["quality"] < 90
                )

        }


        largest_fields = sorted(

            results,

            key=lambda x: x["gis_area"],

            reverse=True

        )[:10]


        smallest_fields = sorted(

            results,

            key=lambda x: x["gis_area"]

        )[:10]


        return {

            "total_fields":
                total_fields,

            "valid_fields":
                valid_fields,

            "total_area_ha":
                total_area,

            "average_quality":
                average_quality,

            "review_count":
                len(review_fields),

            "fields_needing_review":
                [r["field"] for r in review_fields],

            "review_details":
                review_fields,

            "quality_distribution":
                quality_distribution,

            "largest_fields":
                largest_fields,

            "smallest_fields":
                smallest_fields

        }
