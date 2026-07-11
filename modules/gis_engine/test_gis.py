from modules.gis_engine.validator import GISValidator
from modules.gis_engine.calculations import Coordinate


field = [

    Coordinate(-12.9000, 34.3000),
    Coordinate(-12.9000, 34.3050),
    Coordinate(-12.9050, 34.3050),
    Coordinate(-12.9050, 34.3000),
    Coordinate(-12.9000, 34.3000)

]


report = GISValidator.create_report(
    field
)


data = report.to_dict()


print("GIS VALIDATION REPORT")
print("=====================")

print()

print("STATUS:")
print(data["valid"])

print()

print("AREA:")
print(
    data["field_area_ha"],
    "hectares"
)

print()

print("PERIMETER:")
print(
    data["perimeter_m"],
    "meters"
)

print()

print("POINTS:")
print(
    data["point_count"]
)

print()

print("COMPACTNESS:")
print(
    data["compactness"]
)

print()

print("QUALITY SCORE:")
print(
    data["quality_score"],
    "%"
)

print()

print("ERRORS:")
for error in data["errors"]:
    print("-", error)

print()

print("WARNINGS:")
for warning in data["warnings"]:
    print("-", warning)

print()

print("INFO:")
for info in data["info"]:
    print("-", info)