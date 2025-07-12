import os
import pandas as pd
from flask import flash, redirect, render_template, request, url_for
from datetime import date


# Define the blueprint first
from flask import Blueprint
reporting_bp = Blueprint('reporting', __name__)

DATA_FILE = 'data/reporting_months.xlsx'
DEFAULT_MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

@reporting_bp.route('/reporting-months', methods=['GET', 'POST'])
def manage_reporting_months():
    if not os.path.exists(DATA_FILE):
        # Create default date ranges for example — you can adjust as needed
        default_start_dates = [
            '2024-12-26', '2025-01-25', '2025-02-25', '2025-03-27',
            '2025-04-26', '2025-05-27', '2025-06-26', '2025-07-26',
            '2025-08-26', '2025-09-25', '2025-10-25', '2025-11-25'
        ]
        default_end_dates = [
            '2025-01-24', '2025-02-24', '2025-03-26', '2025-04-25',
            '2025-05-26', '2025-06-25', '2025-07-25', '2025-08-25',
            '2025-09-24', '2025-10-24', '2025-11-24', '2025-12-24'
        ]

        df = pd.DataFrame({
            'Month': DEFAULT_MONTHS,
            'Start Date': default_start_dates,
            'End Date': default_end_dates
        })
        df.to_excel(DATA_FILE, index=False)

    df = pd.read_excel(DATA_FILE)

    if request.method == 'POST':
        for index in range(len(df)):
            start_date = request.form.get(f'start_date_{index}')
            end_date = request.form.get(f'end_date_{index}')
            # Basic validation could be added here

            df.at[index, 'Start Date'] = start_date
            df.at[index, 'End Date'] = end_date

        df.to_excel(DATA_FILE, index=False)
        flash("✅ Reporting month ranges updated successfully.")
        return redirect(url_for('reporting.manage_reporting_months'))

    # Convert dates to ISO string format if not already (for input value compatibility)
    df['Start Date'] = pd.to_datetime(df['Start Date']).dt.strftime('%Y-%m-%d')
    df['End Date'] = pd.to_datetime(df['End Date']).dt.strftime('%Y-%m-%d')

    return render_template('reporting_months_form.html', months=df.to_dict(orient='records'))
