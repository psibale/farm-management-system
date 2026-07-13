from modules.gis_engine.field_service import FieldService


points = FieldService.load_field_boundary(
    "DG01000"
)


print("POINT COUNT:")
print(
    len(points)
)


print()


for p in points[:3]:

    print(
        p.latitude,
        p.longitude
    )