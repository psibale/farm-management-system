from flask import Blueprint, render_template
import pandas as pd
import os
from datetime import datetime, timedelta

alerts_bp = Blueprint("alerts", __name__, url_prefix="/alerts")

# File paths
EQUIPMENT_FILE = "data/equipment_records.xlsx"
INVENTORY_FILE = "data/inventory.xlsx"
EXPENSE_FILE = "data/expenses.xlsx"
BUDGET_FILE = "data/expenses_budgets.xlsx"
EMPLOYEE_FILE = "data/employees.xlsx"

# Main alert route
@alerts_bp.route("/")
def show_alerts():
    equipment_alerts, inventory_alerts, budget_alerts, retirement_alerts = get_all_alerts()

    # Combine all alerts into a single list of dicts for the template
    alerts = []

    alerts += [{"type": "🛠️ Equipment", "message": a, "severity": "High"} for a in equipment_alerts]
    alerts += [{"type": "📦 Inventory", "message": a, "severity": "Medium"} for a in inventory_alerts]
    alerts += [{"type": "💸 Budget", "message": a, "severity": "High"} for a in budget_alerts]
    alerts += [{"type": "👴 Retirement", "message": a, "severity": "Low"} for a in retirement_alerts]

    return render_template("alerts/alerts.html", alerts=alerts)


# Core logic to gather all alerts
def get_all_alerts():
    equipment_alerts = []
    inventory_alerts = []
    budget_alerts = []
    retirement_alerts = []

    # 1. Equipment Alerts
    try:
        if os.path.exists(EQUIPMENT_FILE):
            df = pd.read_excel(EQUIPMENT_FILE)
            df.columns = df.columns.str.strip()
            if 'Next Maintenance Date' in df.columns and 'Equipment Name' in df.columns:
                df['Next Maintenance Date'] = pd.to_datetime(df['Next Maintenance Date'], errors='coerce')
                due_items = df[df["Next Maintenance Date"] <= pd.Timestamp.now()]
                equipment_alerts = [f"{row['Equipment Name']} is due for maintenance." for _, row in due_items.iterrows()]
            else:
                equipment_alerts.append("⚠️ Required columns missing in equipment.xlsx")
    except Exception as e:
        equipment_alerts.append(f"⚠️ Equipment alert error: {str(e)}")

    # 2. Inventory Alerts
    try:
        if os.path.exists(INVENTORY_FILE):
            df = pd.read_excel(INVENTORY_FILE)
            df.columns = df.columns.str.strip()
            if 'ItemName' in df.columns and 'Quantity' in df.columns and 'ReorderLevel' in df.columns:
                low_stock = df[df["Quantity"] < df["ReorderLevel"]]
                inventory_alerts = [f"{row['ItemName']} is below minimum stock." for _, row in low_stock.iterrows()]
            else:
                inventory_alerts.append("⚠️ Required columns missing in inventory.xlsx")
    except Exception as e:
        inventory_alerts.append(f"⚠️ Inventory alert error: {str(e)}")

    # 3. Budget Alerts
    try:
        if os.path.exists(EXPENSE_FILE) and os.path.exists(BUDGET_FILE):
            exp_df = pd.read_excel(EXPENSE_FILE)
            bud_df = pd.read_excel(BUDGET_FILE)
            exp_df.columns = exp_df.columns.str.strip()
            bud_df.columns = bud_df.columns.str.strip()

            if 'Category' in exp_df.columns and 'Amount' in exp_df.columns and 'Category' in bud_df.columns and 'Budget' in bud_df.columns:
                grouped = exp_df.groupby('Category')['Amount'].sum().reset_index()
                for _, budget in bud_df.iterrows():
                    actual = grouped[grouped['Category'] == budget['Category']]
                    if not actual.empty and actual['Amount'].values[0] > budget['Budget']:
                        budget_alerts.append(f"{budget['Category']} spending exceeded budget.")
            else:
                budget_alerts.append("⚠️ Required columns missing in expenses or budgets.xlsx")
    except Exception as e:
        budget_alerts.append(f"⚠️ Budget alert error: {str(e)}")

    # 4. Retirement Alerts (within 2 years to retirement)
    try:
        if os.path.exists(EMPLOYEE_FILE):
            df = pd.read_excel(EMPLOYEE_FILE)
            df.columns = df.columns.str.strip()
            if "Full Name" in df.columns and "Date of Birth" in df.columns:
                df["Date of Birth"] = pd.to_datetime(df["Date of Birth"], errors='coerce')
                df["Retirement Date"] = df["Date of Birth"] + pd.DateOffset(years=60)
                df["Years Left"] = (df["Retirement Date"] - pd.Timestamp.now()).dt.days // 365
                nearing_retirement = df[df["Years Left"] <= 2]
                for _, row in nearing_retirement.iterrows():
                    retirement_alerts.append(f"{row['Full Name']} has {row['Years Left']} year(s) left to retirement.")
            else:
                retirement_alerts.append("⚠️ Required columns missing in employees.xlsx")
    except Exception as e:
        retirement_alerts.append(f"⚠️ Retirement alert error: {str(e)}")

    return equipment_alerts, inventory_alerts, budget_alerts, retirement_alerts
