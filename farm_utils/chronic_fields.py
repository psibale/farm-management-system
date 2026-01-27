# farm_utils/chronic_fields.py

import pandas as pd

PEST_DISEASE_FILE = "data/pest_disease_control.xlsx"


def get_chronic_fields(top_n=5):
    """
    Rank fields by long-term disease pressure (SMUT + YSA)
    """
    df = pd.read_excel(PEST_DISEASE_FILE)

    # Clean
    df["SMUT%"] = pd.to_numeric(df["SMUT%"], errors="coerce")
    df["YSA%"] = pd.to_numeric(df["YSA%"], errors="coerce")

    # Chronic score = combined disease pressure
    df["Chronic_Score"] = df["SMUT%"].fillna(0) + df["YSA%"].fillna(0)

    chronic = (
        df.groupby("Field")
          .agg(
              Avg_SMUT=("SMUT%", "mean"),
              Avg_YSA=("YSA%", "mean"),
              Avg_Chronic_Score=("Chronic_Score", "mean"),
              Events=("Field", "count"),
              Seasons=("Season", "nunique")
          )
          .reset_index()
    )

    # Rank worst first
    chronic = chronic.sort_values("Avg_Chronic_Score", ascending=False)

    # Round for UI
    chronic["Avg_SMUT"] = chronic["Avg_SMUT"].round(2)
    chronic["Avg_YSA"] = chronic["Avg_YSA"].round(2)
    chronic["Avg_Chronic_Score"] = chronic["Avg_Chronic_Score"].round(2)

    return chronic.head(top_n)
