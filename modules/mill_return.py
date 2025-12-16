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

# ---------------- REPORTING RANGE ----------------
def get_reporting_range(month):
    df = pd.read_excel(REPORTING_FILE)
    df.columns = df.columns.str.strip()

    month_str = calendar.month_name[month].lower().strip()
    df["Start Month"] = df["Start Month"].astype(str).str.lower().str.strip()

    filtered = df[df["Start Month"] == month_str]
    if filtered.empty:
        raise ValueError(f"No reporting period found for {month_str}")

    row = filtered.iloc[0]
    return pd.to_datetime(row["Start Date"]), pd.to_datetime(row["End Date"])


# ---------------- FORM ----------------
@mill_bp.route("/mill-return", methods=["GET", "POST"])
def mill_return_form():
    if request.method == "POST":
        bundles = float(request.form["Bundles"])
        tons = float(request.form["Tons Delivered"])

        new_data = {
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

    return render_template("mill_return_form.html", columns=COLUMNS[:-1], title="DAILY MILL RETURN")


# ---------------- VIEW ----------------
@mill_bp.route("/mill-return/view")
def mill_return_view():
    df = pd.read_excel(MILL_DATA_FILE) if os.path.exists(MILL_DATA_FILE) else pd.DataFrame(columns=COLUMNS)
    return render_template("mill_return_view.html", records=df.to_dict(orient="records"))


# ---------------- SUMMARY ----------------
@mill_bp.route("/mill-return/summary")
def mill_return_summary():
    month = int(request.args.get("month", datetime.now().month))
    year = int(request.args.get("year", datetime.now().year))

    df = pd.read_excel(MILL_DATA_FILE) if os.path.exists(MILL_DATA_FILE) else pd.DataFrame(columns=COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    start_date, end_date = get_reporting_range(month)
    df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

    summary = {
        "Total Bundles": round(df["Bundles"].sum(), 2),
        "Total Tons Delivered": round(df["Tons Delivered"].sum(), 2),
        "Average Weight": round(df["Tons Delivered"].sum() / df["Bundles"].sum(), 2)
        if df["Bundles"].sum() > 0 else 0,
    }

    grouped = (
        df.groupby(["Field", "Variety"], as_index=False)
        .agg({"Bundles": "sum", "Tons Delivered": "sum", "Average Weight": "mean"})
        .round(2)
    )

    return render_template(
        "mill_return_summary.html",
        summary=summary,
        grouped=grouped.to_dict(orient="records"),
        month_name=datetime(year, month, 1).strftime("%B %Y"),
        current_year=datetime.now().year,
        reporting_period={"start": start_date, "end": end_date},
    )


# ---------------- TONNAGE GRAPH (MONTHLY + CUMULATIVE) ----------------
@mill_bp.route("/mill/tonnage-graph")
def mill_return_tonnage_graph():
    year = request.args.get("year", type=int)
    current_year = datetime.now().year

    if not os.path.exists(MILL_DATA_FILE):
        return render_template(
            "mill_return_tonnage_graph.html",
            chart_data=None,
            selected_year=year,
            current_year=current_year,
        )

    df = pd.read_excel(MILL_DATA_FILE)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    if year:
        df = df[df["Date"].dt.year == year]

    monthly = (
        df.groupby(df["Date"].dt.to_period("M"))["Tons Delivered"]
        .sum()
        .reset_index()
    )

    monthly["Month"] = monthly["Date"].astype(str)
    monthly["Cumulative"] = monthly["Tons Delivered"].cumsum()

    chart_data = {
        "labels": monthly["Month"].tolist(),
        "monthly": monthly["Tons Delivered"].round(2).tolist(),
        "cumulative": monthly["Cumulative"].round(2).tolist(),
    }

    return render_template(
        "mill_return_tonnage_graph.html",
        chart_data=chart_data,
        selected_year=year,
        current_year=current_year,
    )
