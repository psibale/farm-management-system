# modules/mill_return.py
from flask import Blueprint, render_template, request, redirect, url_for, current_app
import pandas as pd
from datetime import datetime
import os
import calendar

mill_bp = Blueprint("mill", __name__)

# ---------------- PATHS ----------------
MILL_DATA_FILE = os.path.join("data", "mill_return.xlsx")
REPORTING_FILE = os.path.join("data", "reporting_months.xlsx")

COLUMNS = ["Date", "Field", "Variety", "Bundles", "Tons Delivered", "Average Weight"]

# ---------------- REPORTING RANGE (SEASON BASED) ----------------
def get_reporting_range(season, month_number):

    df = pd.read_excel(REPORTING_FILE)
    df.columns = df.columns.str.strip()

    # Convert month number (1-12) to month name
    month_name = calendar.month_name[month_number].strip()

    # Filter by Season AND Month
    filtered = df[
        (df["Season"] == season) &
        (df["Month"] == month_name)
    ]

    if filtered.empty:
        raise ValueError(f"No reporting period found for {season} - {month_name}")

    row = filtered.iloc[0]

    return (
        pd.to_datetime(row["Start Date"]),
        pd.to_datetime(row["End Date"])
    )

# ---------------- FORM ----------------
@mill_bp.route("/mill-return", methods=["GET", "POST"])
def mill_return_form():

    # Read active season
    season_file = os.path.join("data", "active_season.txt")
    season = open(season_file).read().strip() if os.path.exists(season_file) else "Unknown"

    if request.method == "POST":
        bundles = float(request.form["Bundles"])
        tons = float(request.form["Tons Delivered"])

        new_data = {
            "Season": season,
            "Date": request.form["Date"],
            "Field": request.form["Field"],
            "Variety": request.form["Variety"],
            "Bundles": bundles,
            "Tons Delivered": tons,
            "Average Weight": round(tons / bundles, 3) if bundles > 0 else 0,
        }

        if os.path.exists(MILL_DATA_FILE):
            df = pd.read_excel(MILL_DATA_FILE)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])

        df.to_excel(MILL_DATA_FILE, index=False)
        return redirect(url_for("mill.mill_return_form"))

    return render_template("mill_return_form.html", columns=COLUMNS[1:-1], title="DAILY MILL RETURN")

# ---------------- VIEW (SEASON BASED) ----------------
@mill_bp.route("/mill-return/view")
def mill_return_view():

    # -------- GET ACTIVE SEASON --------
    season_file = os.path.join("data", "active_season.txt")
    season = open(season_file).read().strip() if os.path.exists(season_file) else None

    # -------- LOAD DATA --------
    if os.path.exists(MILL_DATA_FILE):
        df = pd.read_excel(MILL_DATA_FILE)
    else:
        df = pd.DataFrame(columns=COLUMNS)

    if df.empty:
        return render_template(
            "mill_return_view.html",
            records=[],
            season=season
        )

    df.columns = df.columns.str.strip()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # -------- ENSURE SEASON COLUMN EXISTS --------
    if "Season" not in df.columns:
        df["Season"] = season  # For older records

    # -------- FILTER BY ACTIVE SEASON --------
    if season:
        df = df[df["Season"] == season]

    # -------- SORT BY DATE (LATEST FIRST) --------
    df = df.sort_values(by="Date", ascending=False)

    return render_template(
        "mill_return_view.html",
        records=df.to_dict(orient="records"),
        season=season
    )
# ---------------- SUMMARY (FULLY SEASON BASED) ----------------
@mill_bp.route("/mill-return/summary")
def mill_return_summary():

    # -------- GET ACTIVE SEASON --------
    season_file = os.path.join("data", "active_season.txt")
    season = open(season_file).read().strip() if os.path.exists(season_file) else None

    # -------- GET SELECTED REPORTING MONTH --------
    month = int(request.args.get("month", datetime.now().month))

    # -------- LOAD DATA --------
    if os.path.exists(MILL_DATA_FILE):
        df = pd.read_excel(MILL_DATA_FILE)
    else:
        df = pd.DataFrame(columns=COLUMNS)

    # -------- HANDLE EMPTY FILE --------
    if df.empty:
        return render_template(
            "mill_return_summary.html",
            summary=None,
            grouped=[],
            month_label=None,
            reporting_period=None,
            season=season
        )

    df.columns = df.columns.str.strip()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # -------- ENSURE SEASON COLUMN EXISTS --------
    if "Season" not in df.columns:
        df["Season"] = season

    # -------- FILTER BY ACTIVE SEASON --------
    if season:
        df = df[df["Season"] == season]

    # -------- GET REPORTING PERIOD --------
    start_date, end_date = get_reporting_range(season, month)

    df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

    # -------- SUMMARY CALCULATIONS --------
    total_bundles = df["Bundles"].sum()
    total_tons = df["Tons Delivered"].sum()

    summary = {
        "Total Bundles": round(total_bundles, 2),
        "Total Tons Delivered": round(total_tons, 2),
        "Average Weight": round(total_tons / total_bundles, 3)
        if total_bundles > 0 else 0,
    }

    # -------- GROUPED BY FIELD + VARIETY --------
    grouped = (
        df.groupby(["Field", "Variety"], as_index=False)
        .agg({
            "Bundles": "sum",
            "Tons Delivered": "sum",
        })
    )

    if not grouped.empty:
        grouped["Average Weight"] = (
            grouped["Tons Delivered"] / grouped["Bundles"]
        ).round(3)

    grouped = grouped.round(2)

    # -------- CLEAN REPORTING LABEL --------
    month_label = f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}"

    return render_template(
        "mill_return_summary.html",
        summary=summary,
        grouped=grouped.to_dict(orient="records"),
        month_label=month_label,
        reporting_period={"start": start_date, "end": end_date},
        season=season
    )
# ---------------- TONNAGE GRAPH (FULLY SEASON BASED) ----------------
@mill_bp.route("/mill/tonnage-graph")
def mill_return_tonnage_graph():

    # -------- GET ACTIVE SEASON --------
    season_file = os.path.join("data", "active_season.txt")
    season = open(season_file).read().strip() if os.path.exists(season_file) else None

    if not os.path.exists(MILL_DATA_FILE):
        return render_template(
            "mill_return_tonnage_graph.html",
            chart_data=None,
            selected_season=season
        )

    df = pd.read_excel(MILL_DATA_FILE)
    df.columns = df.columns.str.strip()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # -------- ENSURE SEASON COLUMN EXISTS --------
    if "Season" not in df.columns:
        df["Season"] = season

    # -------- FILTER BY ACTIVE SEASON --------
    if season:
        df = df[df["Season"] == season]

    if df.empty:
        return render_template(
            "mill_return_tonnage_graph.html",
            chart_data=None,
            selected_season=season
        )

    # -------- GET SEASON START / END --------
    season_df = pd.read_excel("data/season_data.xlsx")
    season_df["Start Date"] = pd.to_datetime(season_df["Start Date"])
    season_df["End Date"] = pd.to_datetime(season_df["End Date"])

    row = season_df[season_df["Season Name"] == season].iloc[0]
    season_start = row["Start Date"]
    season_end = row["End Date"]

    # -------- BUILD MONTHLY USING get_reporting_range LOGIC --------
    labels = []
    monthly_totals = []

    current = season_start

    while current <= season_end:

        month = current.month

        start_date, end_date = get_reporting_range(season, month)

        month_df = df[
            (df["Date"] >= start_date) &
            (df["Date"] <= end_date)
        ]

        total_tons = month_df["Tons Delivered"].sum()

        labels.append(f"{start_date.strftime('%d %b')} - {end_date.strftime('%d %b')}")
        monthly_totals.append(round(total_tons, 2))

        # move to next month safely
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    # -------- CUMULATIVE --------
    cumulative = []
    running = 0
    for value in monthly_totals:
        running += value
        cumulative.append(round(running, 2))

    chart_data = {
        "labels": labels,
        "monthly": monthly_totals,
        "cumulative": cumulative,
    }

    return render_template(
        "mill_return_tonnage_graph.html",
        chart_data=chart_data,
        selected_season=season
    )