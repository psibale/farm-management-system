# farm_utils/chemical_effectiveness.py

import pandas as pd

PEST_DISEASE_FILE = "data/pest_disease_control.xlsx"


def get_chemical_effectiveness():
    df = pd.read_excel(PEST_DISEASE_FILE)

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce",
        format="mixed",
        dayfirst=False
    )
    df = df.dropna(subset=["Date"])
    df["SMUT%"] = pd.to_numeric(df["SMUT%"], errors="coerce")
    df["YSA%"] = pd.to_numeric(df["YSA%"], errors="coerce")
    df["Liters"] = pd.to_numeric(df["Liters"], errors="coerce").fillna(0)

    # Only records with pesticide used
    treated = df[df["Pesticide Used"].notna() & (df["Pesticide Used"] != "")].copy()

    results = []

    for chemical, g in treated.groupby("Pesticide Used"):
        g = g.sort_values("Date")

        before = g[["SMUT%", "YSA%"]].shift(1)
        after = g[["SMUT%", "YSA%"]]

        smut_change = (before["SMUT%"] - after["SMUT%"]).mean()
        ysa_change = (before["YSA%"] - after["YSA%"]).mean()

        avg_liters = g["Liters"].mean()
        applications = len(g)

        results.append({
            "Chemical": chemical,
            "Applications": applications,
            "Avg_Liters": round(avg_liters, 1),
            "Avg_SMUT_Reduction": round(smut_change, 2),
            "Avg_YSA_Reduction": round(ysa_change, 2),
            "Effectiveness_Score": round(
                (smut_change if pd.notna(smut_change) else 0) +
                (ysa_change if pd.notna(ysa_change) else 0), 2
            )
        })

    if not results:
        return pd.DataFrame(columns=[
            "Pesticide",
            "Avg_Before",
            "Avg_After",
            "Improvement",
            "Effectiveness_Score"
        ])

    df_out = pd.DataFrame(results)

    if "Effectiveness_Score" in df_out.columns:
        df_out = df_out.sort_values("Effectiveness_Score", ascending=False)

    return df_out

