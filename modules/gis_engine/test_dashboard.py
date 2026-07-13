from modules.gis_engine.dashboard import GISDashboard


summary = GISDashboard.get_summary()


print("GIS DASHBOARD SUMMARY")
print("=====================")


for key, value in summary.items():

    print(
        key,
        ":",
        value
    )