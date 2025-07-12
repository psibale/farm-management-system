# modules/mill_return.py
from flask import Blueprint, render_template, request, redirect, url_for
import pandas as pd
from datetime import datetime, timedelta
import os

mill_bp = Blueprint('mill', __name__)

MILL_DATA_FILE = 'data/mill_return.xlsx'
REPORTING_FILE = 'data/reporting_months.xlsx'
COLUMNS = ['Date', 'Field', 'Variety', 'Bundles', 'Tons Delivered', 'Average Weight']

# Utility to get reporting date range
import calendar
import pandas as pd

def get_reporting_range(month):
    df = pd.read_excel("data/reporting_months.xlsx")
    df.columns = df.columns.str.strip()

    # Convert month number (e.g., 3) to name ("March")
    month_str = calendar.month_name[month].lower().strip()
    df['Start Month'] = df['Start Month'].astype(str).str.lower().str.strip()

    filtered = df[df['Start Month'] == month_str]

    if filtered.empty:
        raise ValueError(f"No reporting period found for Start Month='{month_str}'")

    row = filtered.iloc[0]
    return row['Start Date'], row['End Date']



@mill_bp.route('/mill-return', methods=['GET', 'POST'])
def mill_return_form():
    if request.method == 'POST':
        date = request.form['Date']
        field = request.form['Field']
        variety = request.form['Variety']
        bundles = float(request.form['Bundles'])
        tons = float(request.form['Tons Delivered'])
        avg_weight = round(tons / bundles, 3) if bundles > 0 else 0

        new_data = {
            'Date': date,
            'Field': field,
            'Variety': variety,
            'Bundles': bundles,
            'Tons Delivered': tons,
            'Average Weight': avg_weight
        }

        if os.path.exists(MILL_DATA_FILE):
            df = pd.read_excel(MILL_DATA_FILE)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])

        df.to_excel(MILL_DATA_FILE, index=False)
        return redirect(url_for('mill.mill_return_form'))

    return render_template('mill_return_form.html', columns=COLUMNS[:-1], title='DAILY MILL RETURN')


@mill_bp.route('/mill-return/view')
def mill_return_view():
    df = pd.read_excel(MILL_DATA_FILE) if os.path.exists(MILL_DATA_FILE) else pd.DataFrame(columns=COLUMNS)
    return render_template('mill_return_view.html', records=df.to_dict(orient='records'), title='Daily Mill Return Records')


@mill_bp.route('/mill-return/summary')
def mill_return_summary():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))

    df = pd.read_excel(MILL_DATA_FILE) if os.path.exists(MILL_DATA_FILE) else pd.DataFrame(columns=COLUMNS)
    df['Date'] = pd.to_datetime(df['Date'])

    start_date, end_date = get_reporting_range(month)
    df_filtered = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

    summary = {
        'Total Bundles': round(df_filtered['Bundles'].sum(), 2),
        'Total Tons Delivered': round(df_filtered['Tons Delivered'].sum(), 2),
        'Average Weight (Overall)': round(df_filtered['Tons Delivered'].sum() / df_filtered['Bundles'].sum(), 2) if df_filtered['Bundles'].sum() > 0 else 0
    }

    grouped = df_filtered.groupby(['Field', 'Variety'], as_index=False).agg({
        'Bundles': 'sum',
        'Tons Delivered': 'sum',
        'Average Weight': 'mean'
    })

    # Round grouped values
    grouped['Bundles'] = grouped['Bundles'].round(2)
    grouped['Tons Delivered'] = grouped['Tons Delivered'].round(2)
    grouped['Average Weight'] = grouped['Average Weight'].round(2)

    month_name = datetime(year, month, 1).strftime('%B %Y')
    return render_template(
        'mill_return_summary.html',
        title='Daily Mill Return Summary',
        summary=summary,
        grouped=grouped.to_dict(orient='records'),
        month_name=month_name,
        selected_month=month,
        selected_year=year,
        current_year=datetime.now().year,
        reporting_period = {'start': start_date, 'end': end_date}
    )
