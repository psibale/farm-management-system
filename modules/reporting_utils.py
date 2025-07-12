from datetime import datetime
import pandas as pd
import os

DATA_FILE = 'data/reporting_months.xlsx'

def get_reporting_range(month: int):
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError("Reporting months config file not found.")

    df = pd.read_excel(DATA_FILE)

    MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]

    # Convert month number to month name
    month_name = MONTH_NAMES[month - 1]

    # Find the row matching the month name (strip spaces just in case)
    row = df[df['Start Month'].str.strip() == month_name].iloc[0]

    # Parse start and end dates from the row
    start_date = pd.to_datetime(row['Start Date'])
    end_date = pd.to_datetime(row['End Date'])

    return start_date, end_date
