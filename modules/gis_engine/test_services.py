from modules.gis_engine.calculations import Coordinate
from modules.gis_engine.services import GISService



field = [

    Coordinate(-12.9000,34.3000),

    Coordinate(-12.9000,34.3050),

    Coordinate(-12.9050,34.3050),

    Coordinate(-12.9050,34.3000)

]


field_data = {

    "field_name":
        "DG01000",

    "estate":
        "Dwangwa Main Estate",

    "crop":
        "Sugarcane",

    "season":
        "2026/27"

}



result = GISService.process_field_boundary(

    field,

    field_data

)



print("GIS SERVICE TEST")
print("================")


print()

print("SUCCESS:")
print(
    result["success"]
)


print()

print("REPORT:")
print(
    result["report"]
)


print()

print("GEOJSON:")
print(
    result["geojson"]
)