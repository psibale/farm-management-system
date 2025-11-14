from flask import Blueprint, render_template, request, flash
import pandas as pd
import os
from datetime import datetime

mill_bp = Blueprint('mill_bp', __name__, template_folder='../templates')

# Define paths
YIELD_FILE = os.path.join('data', 'yield_data.xlsx')
CALENDAR_FILE = os.path.join('data', 'mill_reporting_months.xlsx')


@mill_bp.route('/monthly-summary')
def mill_monthly_summary():
    try:
        # --- Selected mill month (default = Mill Month 1) ---
        month = int(request.args.get('month', 1))

        # --- Load mill reporting months file ---
        if not os.path.exists(CALENDAR_FILE):
            flash("Missing file: mill_reporting_months.xlsx in /data folder.", "danger")
            return render_template('mill_monthly_summary.html', title="Mill Monthly Summary")

        calendar = pd.read_excel(CALENDAR_FILE)

        # Ensure columns exist
        required_calendar_cols = ['Month', 'Start Date', 'End Date']
        if not all(col in calendar.columns for col in required_calendar_cols):
            flash("Missing required columns in mill_reporting_months.xlsx (must include Month, Start Date, End Date).", "danger")
            return render_template('mill_monthly_summary.html', title="Mill Monthly Summary")

        # Find date range for selected month
        row = calendar.loc[calendar['Month'] == month]
        if row.empty:
            flash(f"No calendar entry found for mill month {month}.", "warning")
            return render_template('mill_monthly_summary.html', title="Mill Monthly Summary")

        start_date = pd.to_datetime(row.iloc[0]['Start Date'])
        end_date = pd.to_datetime(row.iloc[0]['End Date'])

        # --- Load yield data ---
        if not os.path.exists(YIELD_FILE):
            flash("Missing file: yield_data.xlsx in /data folder.", "danger")
            return render_template('mill_monthly_summary.html', title="Mill Monthly Summary")

        df = pd.read_excel(YIELD_FILE)
        required_cols = ['Date', 'Field', 'Bundles', 'Yield (Tons)']
        for col in required_cols:
            if col not in df.columns:
                flash(f"Missing column '{col}' in yield_data.xlsx", "danger")
                return render_template('mill_monthly_summary.html', title="Mill Monthly Summary")

        # --- Filter by mill reporting month ---
        df['Date'] = pd.to_datetime(df['Date'])
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        df_filtered = df.loc[mask]

        if df_filtered.empty:
            flash(f"No yield data found between {start_date.date()} and {end_date.date()}.", "warning")
            return render_template('mill_monthly_summary.html', title="Mill Monthly Summary")

        # --- Summarize per field ---
        summary = df_filtered.groupby('Field', as_index=False).agg({
            'Bundles': 'sum',
            'Yield (Tons)': 'sum'
        })
        summary['Average Weight (T/B)'] = (summary['Yield (Tons)'] / summary['Bundles']).round(3)

        # --- Totals ---
        total_bundles = summary['Bundles'].sum()
        total_tons = summary['Yield (Tons)'].sum()
        avg_weight = round(total_tons / total_bundles, 3) if total_bundles > 0 else 0

        totals = {
            'Bundles': total_bundles,
            'Yield (Tons)': total_tons,
            'Average Weight (T/B)': avg_weight
        }

        # --- Mill Calendar Month Name ---
        month_name = f"Mill Month {month}"

        # --- Render page ---
        return render_template(
            'mill_monthly_summary.html',
            title="Mill Monthly Summary",
            summary=summary.to_dict(orient='records'),
            totals=totals,
            month_name=month_name,
            current_month=month,
            start_date=start_date.date(),
            end_date=end_date.date()
        )

    except Exception as e:
        flash(f"Error generating mill summary: {e}", "danger")
        return render_template('mill_monthly_summary.html', title="Mill Monthly Summary")
