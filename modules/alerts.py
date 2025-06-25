# modules/alerts.py
from flask import Blueprint, render_template
import pandas as pd
import os
from datetime import datetime, timedelta

alerts_bp = Blueprint("alerts", __name__, url_prefix="/alerts")

EQUIPMENT_FILE = "data/equipment_maintenance.xlsx"
INVENTORY_FILE = "data/stores.xlsx"
EXPENSE_FILE = "data/expenses.xlsx"
BUDGET_FILE = "data/budgets.xlsx"

@alerts_bp.route("/")
def show_alerts():
    alerts = []

    # 1. Equipment Maintenance Alerts
    if os.path.exists(EQUIPMENT_FILE):
        df = pd.read_excel(EQUIPMENT_FILE)
        if 'Last Service Date' in df.columns and 'Equipment' in df.columns:
            df['Last Service Date'] = pd.to_datetime(df['Last Service Date'], errors='coerce')
            due_date = datetime.now() - timedelta(days=90)  # 3 months threshold
            for _, row in df.iterrows():
                if pd.notna(row['Last Service Date']) and row['Last Service Date'] < due_date:
                    alerts.append({
                        "type": "Equipment Maintenance",
                        "message": f"{row['Equipment']} is overdue for service.",
                        "severity": "High"
                    })

    # 2. Low Inventory Alerts
    if os.path.exists(INVENTORY_FILE):
        df = pd.read_excel(INVENTORY_FILE)
        if 'Item' in df.columns and 'Quantity' in df.columns and 'Reorder Level' in df.columns:
            for _, row in df.iterrows():
                if row['Quantity'] < row['Reorder Level']:
                    alerts.append({
                        "type": "Low Inventory",
                        "message": f"{row['Item']} stock is below reorder level.",
                        "severity": "Medium"
                    })

    # 3. Budget Overspending Alerts
    if os.path.exists(EXPENSE_FILE) and os.path.exists(BUDGET_FILE):
        exp_df = pd.read_excel(EXPENSE_FILE)
        bud_df = pd.read_excel(BUDGET_FILE)

        if 'Category' in exp_df.columns and 'Amount' in exp_df.columns:
            grouped = exp_df.groupby('Category')['Amount'].sum().reset_index()
            for _, budget in bud_df.iterrows():
                actual = grouped[grouped['Category'] == budget['Category']]
                if not actual.empty and actual['Amount'].values[0] > budget['Budget']:
                    alerts.append({
                        "type": "Budget Overspending",
                        "message": f"{budget['Category']} spending exceeded budget.",
                        "severity": "High"
                    })

    return render_template("alerts/alerts.html", alerts=alerts)

import pandas as pd
import os

def get_all_alerts():
    equipment_alerts = []
    inventory_alerts = []
    budget_alerts = []

    # Equipment Alerts
    if os.path.exists("data/equipment.xlsx"):
        df = pd.read_excel("data/equipment.xlsx")
        due_items = df[df["Next Maintenance Date"] <= pd.Timestamp.now()]
        equipment_alerts = [f"{row['Equipment Name']} is due for maintenance." for _, row in due_items.iterrows()]

    # Inventory Alerts
    if os.path.exists("data/inventory.xlsx"):
        df = pd.read_excel("data/inventory.xlsx")
        low_stock = df[df["Quantity"] < df["Min Stock"]]
        inventory_alerts = [f"{row['Item']} is below minimum stock." for _, row in low_stock.iterrows()]

    # Budget Alerts
    if os.path.exists("data/expenses.xlsx"):
        df = pd.read_excel("data/expenses.xlsx")
        total = df["Amount"].sum()
        if total > 5000000:  # example threshold
            budget_alerts.append(f"Budget exceeded: Current total is {total:,}")

    return equipment_alerts, inventory_alerts, budget_alerts
