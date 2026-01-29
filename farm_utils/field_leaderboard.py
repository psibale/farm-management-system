import pandas as pd

YIELD_FILE = "data/yield_data.xlsx"
HARVEST_FILE = "data/harvesting_records.xlsx"

def get_field_leaderboard():
    # Load files
    yield_df = pd.read_excel(YIELD_FILE)
    harvest_df = pd.read_excel(HARVEST_FILE)

    # Clean columns
    yield_df.columns = yield_df.columns.str.strip()
    harvest_df.columns = harvest_df.columns.str.strip()

    # Merge to get Area
    merged = yield_df.merge(
        harvest_df[["Field", "Harvested Area (ha)"]],
        on="Field",
        how="inner"
    )

    # Calculate TCH
    merged["TCH"] = merged["Yield (Tons)"] / merged["Harvested Area (ha)"]

    # Field leaderboard
    summary = (
        merged.groupby("Field")
              .agg(
                  Avg_Yield_TCH=("TCH", "mean")
              )
              .reset_index()
    )

    best_fields = summary.sort_values("Avg_Yield_TCH", ascending=False).head(5)
    worst_fields = summary.sort_values("Avg_Yield_TCH", ascending=True).head(5)

    return (
        best_fields.to_dict(orient="records"),
        worst_fields.to_dict(orient="records"),
        summary
    )
