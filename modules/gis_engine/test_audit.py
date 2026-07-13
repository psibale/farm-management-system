from modules.gis_engine.audit import GISAudit


results = GISAudit.run_audit()


print("GIS FARM AUDIT")
print("================")


print()

print("TOTAL FIELDS:")
print(
    len(results)
)


print()


for field in results:

    print(
        field["field"],
        "-",
        field["gis_area"],
        "ha",
        "- Quality:",
        field["quality"]
    )