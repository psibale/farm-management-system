import pandas as pd

YIELD_FILE = 'data/yield_data.xlsx'
HARVEST_FILE = 'data/harvesting_records.xlsx'

def get_yield_season_summary():
    # -----------------------------
    # LOAD FILES
    # -----------------------------
    yield_df = pd.read_excel(YIELD_FILE)
    harvest_df = pd.read_excel(HARVEST_FILE)

    # Clean column names
    yield_df.columns = yield_df.columns.str.strip()
    harvest_df.columns = harvest_df.columns.str.strip()

    # -----------------------------
    # STANDARDIZE COLUMN NAMES
    # -----------------------------
    yield_df = yield_df.rename(columns={
        'Yield (Tons)': 'Tons'
    })

    harvest_df = harvest_df.rename(columns={
        'Harvested Area (ha)': 'Area',
        'Yield (Tons)': 'Tons'
    })

    # -----------------------------
    # VALIDATE REQUIRED COLUMNS
    # -----------------------------
    for col in ['Field', 'Season', 'Tons']:
        if col not in yield_df.columns:
            raise ValueError(f"Missing {col} in yield_data.xlsx")

    for col in ['Field', 'Season', 'Area']:
        if col not in harvest_df.columns:
            raise ValueError(f"Missing {col} in harvesting_records.xlsx")

    # -----------------------------
    # AGGREGATE PER FIELD + SEASON
    # -----------------------------
    yield_field_season = yield_df.groupby(
        ['Field', 'Season']
    ).agg(
        Total_Tons=('Tons', 'sum')
    ).reset_index()

    area_field_season = harvest_df.groupby(
        ['Field', 'Season']
    ).agg(
        Total_Area=('Area', 'sum')
    ).reset_index()

    # -----------------------------
    # MERGE YIELD + AREA
    # -----------------------------
    merged = pd.merge(
        yield_field_season,
        area_field_season,
        on=['Field', 'Season'],
        how='inner'
    )

    # Remove bad data
    merged = merged[merged['Total_Area'] > 0]

    # -----------------------------
    # SEASON SUMMARY (MANAGEMENT GRADE)
    # -----------------------------
    summary = merged.groupby('Season').agg(
        Total_Tons=('Total_Tons', 'sum'),
        Total_Area=('Total_Area', 'sum'),
        Fields=('Field', 'nunique')
    ).reset_index()

    # TRUE WEIGHTED SEASON TCH
    summary['Season_TCH'] = summary['Total_Tons'] / summary['Total_Area']

    # Sort seasons
    summary = summary.sort_values('Season')

    # % Change vs previous season
    summary['Tons_Change_%'] = summary['Total_Tons'].pct_change() * 100
    summary['TCH_Change_%'] = summary['Season_TCH'].pct_change() * 100

    # Presentation rounding
    summary['Total_Tons'] = summary['Total_Tons'].round(0)
    summary['Total_Area'] = summary['Total_Area'].round(1)
    summary['Season_TCH'] = summary['Season_TCH'].round(1)
    summary['Tons_Change_%'] = summary['Tons_Change_%'].round(1)
    summary['TCH_Change_%'] = summary['TCH_Change_%'].round(1)

    return summary
