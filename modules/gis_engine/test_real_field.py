from modules.gis_engine.field_service import FieldService
from modules.gis_engine.validator import GISValidator


field_name = "DG01000"


points = FieldService.load_field_boundary(
    field_name
)


report = GISValidator.create_report(
    points
)


print("REAL FIELD GIS REPORT")
print("====================")

print()

print("FIELD:")
print(field_name)

print()

print("AREA:")
print(
    report.field_area_ha,
    "ha"
)

print()

print("PERIMETER:")
print(
    report.perimeter_m,
    "m"
)

print()

print("POINTS:")
print(
    report.point_count
)

print()

print("COMPACTNESS:")
print(
    report.compactness
)

print()

print("QUALITY SCORE:")
print(
    report.quality_score,
    "%"
)

print()

print("ERRORS:")
print(
    report.errors
)

print()

print("WARNINGS:")
print(
    report.warnings
)