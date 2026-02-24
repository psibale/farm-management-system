import pandas as pd
from datetime import datetime
import os

SEASON_FILE = "data/season_data.xlsx"


def get_reporting_range(season: str, month: int):

    if not season:
        raise ValueError("Season cannot be None.")

    if not os.path.exists(SEASON_FILE):
        raise FileNotFoundError("season_data.xlsx not found.")

    df = pd.read_excel(SEASON_FILE)

    df["Start Date"] = pd.to_datetime(df["Start Date"])
    df["End Date"] = pd.to_datetime(df["End Date"])

    row = df[df["Season Name"] == season]

    if row.empty:
        raise ValueError(f"Season {season} not found.")

    season_start = row.iloc[0]["Start Date"]
    season_end = row.iloc[0]["End Date"]

    # Determine correct year inside season
    if month >= season_start.month:
        year = season_start.year
    else:
        year = season_end.year

    from datetime import datetime
    import calendar

    start_date = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = datetime(year, month, last_day)

    return start_date, end_date

# ✅ Season-Safe Loader
def load_and_filter(filepath, start_date, end_date, season=None):
    """
    Load Excel file and filter by:
    - Season (if provided)
    - Reporting period
    Returns empty DataFrame safely if errors occur.
    """

    try:
        if not os.path.exists(filepath):
            return pd.DataFrame()

        df = pd.read_excel(filepath)

        # Filter by Season first (critical)
        if season and "Season" in df.columns:
            df = df[df["Season"] == season]

        # Filter by Date range
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df[
                (df['Date'] >= start_date) &
                (df['Date'] <= end_date)
            ]

        return df

    except Exception as e:
        print(f"⚠️ Error loading {filepath}: {e}")
        return pd.DataFrame()