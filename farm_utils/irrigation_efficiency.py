import pandas as pd

YIELD_FILE = "data/yield_data.xlsx"
HARVEST_FILE = "data/harvesting_records.xlsx"
IRRIGATION_FILE = "data/irrigation_records.xlsx"  # adjust if needed

def get_yield_vs_irrigation_efficiency():
    # Load
    yield_df = pd.read_excel(YIELD_FILE)
    harvest_df = pd.read_excel(HARVEST_FILE)
    irrig_df = pd.read_excel(IRRIGATION_FILE)

    # Clean column names
    for df in [yield_df, harvest_df, irrig_df]:
        df.columns = df.columns.str.strip()

    # Merge on Field ONLY
    merged = yield_df.merge(
        harvest_df[["Field", "Harvested Area (ha)"]],
        on="Field",
        how="inner"
    )

    # 🔑 Create MainField AFTER merge (bulletproof)
    merged["MainField"] = merged["Field"].astype(str).str[:6] + "000"

    # Calculate TCH at sub-field
    merged["TCH"] = merged["Yield (Tons)"] / merged["Harvested Area (ha)"]

    # Aggregate to Main Field
    main_field_summary = (
        merged
        .groupby("MainField", as_index=False)
        .agg(
            Avg_TCH=("TCH", "mean"),
            Total_Tons=("Yield (Tons)", "sum"),
            Total_Area=("Harvested Area (ha)", "sum")
        )
    )

    # Irrigation summary (already main field)
    irrig_summary = (
        irrig_df
        .groupby("Field", as_index=False)
        .agg(Irrigation_mm=("Irrigation Applied", "sum"))
        .rename(columns={"Field": "MainField"})
    )

    # Merge irrigation
    final = main_field_summary.merge(
        irrig_summary,
        on="MainField",
        how="left"
    )

    # Drop blocks with no irrigation
    final = final[final["Irrigation_mm"].notna()]
    final = final[final["Irrigation_mm"] > 0]

    # Efficiency Index
    final["Efficiency_Index"] = final["Total_Tons"] / final["Irrigation_mm"]

    final = final.sort_values("Efficiency_Index", ascending=False)

    return final.to_dict(orient="records")

