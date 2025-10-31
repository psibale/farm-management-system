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


# ✅ NEW FUNCTION: load_and_filter
def load_and_filter(filepath, start_date, end_date):
    """
    Load Excel file and filter by reporting period if 'Date' column exists.
    Returns an empty DataFrame if file missing or unreadable.
    """
    try:
        df = pd.read_excel(filepath)

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

        return df

    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return pd.DataFrame()

    except Exception as e:
        print(f"⚠️ Error loading {filepath}: {e}")
        return pd.DataFrame()
