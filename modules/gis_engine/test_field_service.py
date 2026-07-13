from modules.gis_engine.field_service import FieldService


fields = FieldService.load_fields()


print("TOTAL FIELDS:")
print(
    len(fields)
)


print()

print("COLUMNS:")
print(
    list(fields.columns)
)


print()

print("FIRST RECORD:")
print(
    fields.iloc[0].to_dict()
)