from modules.gis_engine.calculations import Coordinate
from modules.gis_engine.geojson_utils import GeoJSONUtils


# Sample DG field boundary
field = [

    Coordinate(-12.9000, 34.3000),

    Coordinate(-12.9000, 34.3050),

    Coordinate(-12.9050, 34.3050),

    Coordinate(-12.9050, 34.3000)

]


field_data = {

    "field_name": "DG01000",

    "estate": "Dwangwa Main Estate",

    "crop": "Sugarcane",

    "season": "2026/27",

    "area_ha": 30.13,

    "irrigation": "Centre Pivot",

    "soil_type": "Clay Loam",

    "quality_score": 95

}


geojson = GeoJSONUtils.create_field_feature(
    field,
    field_data
)


print(geojson)