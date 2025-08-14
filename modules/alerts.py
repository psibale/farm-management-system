# modules/alerts.py
import os
import pandas as pd
from flask import Blueprint, render_template
from datetime import datetime

alerts_bp = Blueprint("alerts", __name__)

# --- File Paths ---
INVENTORY_FILE = "data/inventory.xlsx"
EQUIPMENT_FILE = "data/equipment.xlsx"
BUDGET_FILE = "data/budget.xlsx"
EMPLOYEE_FILE = "data/employees.xlsx"

# --- Core Alert Functions ---
def get_all_alerts():
    equipment_alerts = []
    inventory_alerts = []
    budget_alerts = []
    retirement_alerts = []

    # --- Equipment Alerts ---
    if os.path.exists(EQUIPMENT_FILE):
        df = pd.read_excel(EQUIPMENT_FILE)
        df.columns = df.columns.str.strip().str.lower()
        if {"equipmentname", "status"}.issubset(df.columns):
            for _, row in df.iterrows():
                if row["status"].lower() in ["needs repair", "out of order"]:
                    equipment_alerts.append(f"Equipment '{row['equipmentname']}' is {row['status']}.")

    # --- Inventory Alerts ---
    if os.path.exists(INVENTORY_FILE):
        df = pd.read_excel(INVENTORY_FILE)
        df.columns = df.columns.str.strip().str.lower()
        if {"itemname", "quantity", "reorderlevel"}.issubset(df.columns):
            for _, row in df.iterrows():
                if row["quantity"] <= row["reorderlevel"]:
                    inventory_alerts.append(f"Item '{row['itemname']}' is low (Qty: {row['quantity']}).")

    # --- Budget Alerts ---
    if os.path.exists(BUDGET_FILE):
        df = pd.read_excel(BUDGET_FILE)
        df.columns = df.columns.str.strip().str.lower()
        if {"budgetitem", "spent", "allocated"}.issubset(df.columns):
            for _, row in df.iterrows():
                if row["spent"] > row["allocated"]:
                    budget_alerts.append(
                        f"Budget '{row['budgetitem']}' exceeded allocation by {row['spent'] - row['allocated']}."
                    )

    # --- Retirement Alerts ---
    if os.path.exists(EMPLOYEE_FILE):
        df = pd.read_excel(EMPLOYEE_FILE)
        df.columns = df.columns.str.strip().str.lower()
        if {"employeename", "retirementdate"}.issubset(df.columns):
            for _, row in df.iterrows():
                try:
                    retirement_date = pd.to_datetime(row["retirementdate"])
                    if (retirement_date - datetime.now()).days <= 180:
                        retirement_alerts.append(
                            f"Employee '{row['employeename']}' retiring soon ({retirement_date.date()})."
                        )
                except Exception:
                    continue

    return equipment_alerts, inventory_alerts, budget_alerts, retirement_alerts


# --- Combined Alert Format ---
def get_all_alerts_combined():
    eq, inv, bud, ret = get_all_alerts()
    alerts = []
    alerts += [{"type": "Equipment Failure", "message": a, "severity": "High"} for a in eq]
    alerts += [{"type": "Low Stock", "message": a, "severity": "Medium"} for a in inv]
    alerts += [{"type": "Budget Overrun", "message": a, "severity": "High"} for a in bud]
    alerts += [{"type": "Retirement Notice", "message": a, "severity": "Low"} for a in ret]
    return alerts


# --- Urgent Alerts for Dashboard ---
def get_urgent_alerts(limit=5):
    """Return only high severity alerts for AI Farm Manager briefing."""
    all_alerts = get_all_alerts_combined()
    urgent = [a for a in all_alerts if a["severity"] == "High"]
    return urgent[:limit]


# --- Blueprint Route ---
@alerts_bp.route("/alerts")
def show_alerts():
    alerts = get_all_alerts_combined()
    return render_template("alerts/alerts.html", alerts=alerts)
