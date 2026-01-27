import pandas as pd

PEST_FILE = 'data/pest_disease_control.xlsx'

def get_pest_disease_season_summary():
    df = pd.read_excel(PEST_FILE)

    # Clean column names
    df.columns = df.columns.str.strip()

    # Ensure numeric
    for col in ['SMUT%', 'YSA%', 'Black Beetles (ha)', 'Hectares']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    summary = df.groupby('Season').agg(
        Events=('Date', 'count'),
        Fields=('Field', 'nunique'),
        Avg_SMUT=('SMUT%', 'mean'),
        Avg_YSA=('YSA%', 'mean'),
        BlackBeetle_ha=('Black Beetles (ha)', 'sum'),
        Total_Hectares=('Hectares', 'sum')
    ).reset_index()

    # Determine Top Issue per season
    def top_issue(row):
        values = {
            'SMUT': row['Avg_SMUT'],
            'YSA': row['Avg_YSA'],
            'Black Beetle': row['BlackBeetle_ha']
        }
        return max(values, key=values.get)

    summary['Top_Issue'] = summary.apply(top_issue, axis=1)

    # Sort seasons
    summary = summary.sort_values('Season')

    # % Change vs previous season
    summary['Events_Change_Pct'] = summary['Events'].pct_change() * 100
    summary['SMUT_Change_Pct'] = summary['Avg_SMUT'].pct_change() * 100
    summary['YSA_Change_Pct'] = summary['Avg_YSA'].pct_change() * 100

    return summary
