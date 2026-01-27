import pandas as pd

SEASONS_FILE = 'data/season_data.xlsx'

def get_season_for_date(date):
    seasons = pd.read_excel(SEASONS_FILE)

    date = pd.to_datetime(date)
    seasons['Start Date'] = pd.to_datetime(seasons['Start Date'])
    seasons['End Date'] = pd.to_datetime(seasons['End Date'])

    for _, row in seasons.iterrows():
        if row['Start Date'] <= date <= row['End Date']:
            return row['Season']

    return "Unknown"


def add_season_column(df, date_col='Date'):
    df[date_col] = pd.to_datetime(df[date_col])
    df['Season'] = df[date_col].apply(get_season_for_date)
    return df
