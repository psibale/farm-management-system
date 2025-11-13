from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os

mill_months_bp = Blueprint('mill_months_bp', __name__, template_folder='../templates')

FILE_PATH = os.path.join('data', 'mill_reporting_months.xlsx')


@mill_months_bp.route('/mill-reporting-months', methods=['GET', 'POST'])
def mill_reporting_months():
    """View and update the Mill Reporting Months calendar"""
    # Ensure the Excel file exists
    if not os.path.exists(FILE_PATH):
        df = pd.DataFrame({
            'Month': list(range(1, 13)),
            'Start Date': pd.date_range('2025-01-01', periods=12, freq='MS').strftime('%Y-%m-%d'),
            'End Date': pd.date_range('2025-01-31', periods=12, freq='M').strftime('%Y-%m-%d')
        })
        df.to_excel(FILE_PATH, index=False)

    df = pd.read_excel(FILE_PATH)

    if request.method == 'POST':
        try:
            month = int(request.form['month'])
            start_date = request.form['start_date']
            end_date = request.form['end_date']

            df.loc[df['Month'] == month, ['Start Date', 'End Date']] = [start_date, end_date]
            df.to_excel(FILE_PATH, index=False)

            flash(f"Updated reporting range for month {month}.", "success")
            return redirect(url_for('mill_months_bp.mill_reporting_months'))
        except Exception as e:
            flash(f"Error updating file: {e}", "danger")

    df = df.sort_values('Month')
    return render_template(
        'mill_reporting_months_form.html',
        title="Mill Reporting Months",
        months=df.to_dict(orient='records')
    )
