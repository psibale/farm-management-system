import pandas as pd

YIELD_FILE = "data/yield_data.xlsx"
HARVEST_FILE = "data/harvesting_records.xlsx"

def get_yield_trends_by_season():
    yield_df = pd.read_excel(YIELD_FILE)
    harvest_df = pd.read_excel(HARVEST_FILE)

    # Clean columns
    yield_df.columns = yield_df.columns.str.strip()
    harvest_df.columns = harvest_df.columns.str.strip()

    # Safety checks
    required_yield_cols = {"Field", "Season", "Yield (Tons)"}
    required_harvest_cols = {"Field", "Harvested Area (ha)"}

    if not required_yield_cols.issubset(yield_df.columns):
        raise ValueError(f"yield_data.xlsx missing columns: {required_yield_cols - set(yield_df.columns)}")

    if not required_harvest_cols.issubset(harvest_df.columns):
        raise ValueError(f"harvesting_records.xlsx missing columns: {required_harvest_cols - set(harvest_df.columns)}")

    # Merge ONLY to get Area (ha)
    merged = yield_df.merge(
        harvest_df[["Field", "Harvested Area (ha)"]],
        on="Field",
        how="left"
    )

    # Calculate TCH safely
    merged["TCH"] = merged["Yield (Tons)"] / merged["Harvested Area (ha)"]

    # ===== SEASON TRENDS (SINGLE SOURCE OF YIELD) =====

    # Total Tons by Season (ONLY yield_data.xlsx)
    tons_trend = (
        merged
        .groupby("Season", as_index=False)
        .agg(Total_Tons=("Yield (Tons)", "sum"))
        .sort_values("Season")
    )

    # Avg TCH by Season
    tch_trend = (
        merged
        .dropna(subset=["TCH"])
        .groupby("Season", as_index=False)
        .agg(Avg_TCH=("TCH", "mean"))
        .sort_values("Season")
    )

    return (
        tons_trend.to_dict(orient="records"),
        tch_trend.to_dict(orient="records")
    )
