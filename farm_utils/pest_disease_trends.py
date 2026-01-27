# farm_utils/pest_disease_trends.py

import pandas as pd

PEST_DISEASE_FILE = "data/pest_disease_control.xlsx"


def get_smut_ysa_trend():
    """
    Returns season-wise average SMUT and YSA for trend analysis
    """
    df = pd.read_excel(PEST_DISEASE_FILE)

    # Clean + standardize
    df["Season"] = df["Season"].astype(str)
    df["SMUT%"] = pd.to_numeric(df["SMUT%"], errors="coerce")
    df["YSA%"] = pd.to_numeric(df["YSA%"], errors="coerce")

    trend = (
        df.groupby("Season")
          .agg(
              Avg_SMUT=("SMUT%", "mean"),
              Avg_YSA=("YSA%", "mean"),
              Events=("Field", "count")
          )
          .reset_index()
          .sort_values("Season")
    )

    # Round for UI
    trend["Avg_SMUT"] = trend["Avg_SMUT"].round(2)
    trend["Avg_YSA"] = trend["Avg_YSA"].round(2)

    return trend
