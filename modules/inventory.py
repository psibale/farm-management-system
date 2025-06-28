from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import current_user
import pandas as pd
import os
from datetime import datetime
from random import randint
from modules.utils import role_required
from modules.utils import role_required

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")

INVENTORY_FILE = "data/inventory_data.xlsx"
LOG_FILE = "data/inventory_logs.xlsx"
REQUESTS_FILE = "data/inventory_requests.xlsx"

# Dashboard
@inventory_bp.route("/")
def dashboard():
    items = []
    if os.path.exists(INVENTORY_FILE):
        df = pd.read_excel(INVENTORY_FILE)
        items = df.to_dict(orient="records")
    return render_template("inventory.html", items=items)


# Add Item
@inventory_bp.route("/add", methods=["GET", "POST"])
@role_required(['Stores', 'Admin'])
def add_item():
    if request.method == "POST":
        item = {
            "ItemName": request.form["item_name"],
            "Category": request.form["category"],
            "Quantity": int(request.form["quantity"]),
            "Unit": request.form["unit"],
            "ReorderLevel": int(request.form["reorder_level"])
        }
        if os.path.exists(INVENTORY_FILE):
            df = pd.read_excel(INVENTORY_FILE)
            df = pd.concat([df, pd.DataFrame([item])], ignore_index=True)
        else:
            df = pd.DataFrame([item])
        df.to_excel(INVENTORY_FILE, index=False)
        return redirect(url_for("inventory.dashboard"))
    return render_template("add_item.html")


# View Logs
@inventory_bp.route("/logs")
@role_required(['Stores', 'Manager', 'Field Officer', 'HR Officer', 'Admin'])
def view_logs():
    logs = []
    if os.path.exists(LOG_FILE):
        df = pd.read_excel(LOG_FILE)
        logs = df.to_dict(orient="records")
    return render_template("inventory_logs.html", logs=logs)


# Issue Item (manual)
@inventory_bp.route("/issue", methods=["GET", "POST"])
@role_required(['Stores', 'Admin'])
def issue_item():
    if request.method == "POST":
        log = {
            "Date": pd.Timestamp.now(),
            "Action": "Issued",
            "ItemName": request.form["item_name"],
            "Quantity": int(request.form["quantity"]),
            "IssuedTo": request.form["issued_to"],
            "Remarks": request.form["remarks"],
            "PerformedBy": current_user.username
        }

        # Save log
        logs_df = pd.read_excel(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame()
        logs_df = pd.concat([logs_df, pd.DataFrame([log])], ignore_index=True)
        logs_df.to_excel(LOG_FILE, index=False)

        # Update inventory
        df = pd.read_excel(INVENTORY_FILE)
        df.loc[df["ItemName"] == log["ItemName"], "Quantity"] -= log["Quantity"]
        df.to_excel(INVENTORY_FILE, index=False)

        return redirect(url_for("inventory.dashboard"))

    df = pd.read_excel(INVENTORY_FILE)
    items = df["ItemName"].tolist()
    return render_template("issue_item.html", items=items)


# Replenish Stock
@inventory_bp.route("/replenish", methods=["GET", "POST"])
@role_required(['Admin', 'Stores'])
def replenish_stock():
    if not os.path.exists(INVENTORY_FILE):
        return "Inventory file not found."

    df = pd.read_excel(INVENTORY_FILE)
    if request.method == "POST":
        item_name = request.form["item_name"]
        quantity_added = int(request.form["quantity"])
        df.loc[df["ItemName"] == item_name, "Quantity"] += quantity_added
        df.to_excel(INVENTORY_FILE, index=False)

        # Log
        log = {
            "Date": pd.Timestamp.now(),
            "Action": "Replenishment",
            "ItemName": item_name,
            "Quantity": quantity_added,
            "Remarks": request.form.get("remarks", ""),
            "PerformedBy": current_user.username
        }

        logs_df = pd.read_excel(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame()
        logs_df = pd.concat([logs_df, pd.DataFrame([log])], ignore_index=True)
        logs_df.to_excel(LOG_FILE, index=False)

        return redirect(url_for("inventory.dashboard"))

    return render_template("replenish_stock.html", items=df["ItemName"].tolist())


# Inventory Analytics
@inventory_bp.route('/analytics')
@role_required(['agriculture Manager', 'Manager', 'Stores', 'HR Officer', 'Admin'])
def inventory_analytics():
    inventory_df = pd.read_excel(INVENTORY_FILE) if os.path.exists(INVENTORY_FILE) else pd.DataFrame()
    logs_df = pd.read_excel(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame()

    category_counts = inventory_df["Category"].value_counts().to_dict()
    issued_items = logs_df[logs_df["Action"].str.contains("Issued", na=False)]
    top_issued = issued_items["ItemName"].value_counts().head(5).to_dict()
    logs_df["Date"] = pd.to_datetime(logs_df["Date"], errors='coerce')
    trend_data = logs_df.groupby(logs_df["Date"].dt.to_period("M"))["Quantity"].sum().sort_index().to_timestamp()

    return render_template("inventory_analytics.html",
                           category_counts=category_counts,
                           top_issued=top_issued,
                           trend_data=trend_data.to_dict())


# Submit Request (with SR# generation)
from datetime import datetime
import random
import string

def generate_sr_number():
    return "SR" + ''.join(random.choices(string.digits, k=5))

@inventory_bp.route("/inventory/request", methods=["GET", "POST"])
def request_item():
    sr_number = None

    if request.method == "POST":
        item_name = request.form["item_name"]
        quantity = int(request.form["quantity"])
        reason = request.form["reason"]
        user = session.get("username", "Unknown")
        sr_number = generate_sr_number()

        request_data = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ItemName": item_name,
            "Quantity": quantity,
            "Reason": reason,
            "Status": "Pending",
            "RequestedBy": user,
            "SR#": sr_number
        }

        if os.path.exists(REQUESTS_FILE):
            df = pd.read_excel(REQUESTS_FILE)
            df = pd.concat([df, pd.DataFrame([request_data])], ignore_index=True)
        else:
            df = pd.DataFrame([request_data])

        df.to_excel(REQUESTS_FILE, index=False)

        # ✅ Pass the SR# to the template
        return render_template("request_item.html", sr_number=sr_number)

    return render_template("request_item.html", sr_number=None)


# View Requests
@inventory_bp.route("/requests")
@role_required(['agriculture Manager', 'Manager', 'HR Officer', 'Admin'])
def view_requests():
    requests = []
    if os.path.exists(REQUESTS_FILE):
        df = pd.read_excel(REQUESTS_FILE)
        requests = df.to_dict(orient="records")
    return render_template("view_requests.html", requests=requests)


# Approve Request
@inventory_bp.route("/approve/<int:index>", methods=["POST"])
@role_required(['agriculture Manager', 'Manager', 'HR Officer', 'Admin'])
def approve_request(index):
    if not os.path.exists(REQUESTS_FILE):
        return "No requests found."

    df = pd.read_excel(REQUESTS_FILE)
    df.at[index, "Status"] = "Approved"
    df.to_excel(REQUESTS_FILE, index=False)
    return redirect(url_for("inventory.view_requests"))


# Reject Request
@inventory_bp.route("/reject/<int:index>", methods=["POST"])
@role_required(['agriculture Manager', 'Manager', 'HR Officer', 'Admin'])
def reject_request(index):
    if not os.path.exists(REQUESTS_FILE):
        return "No requests found."

    df = pd.read_excel(REQUESTS_FILE)
    df.at[index, "Status"] = "Rejected"
    df.to_excel(REQUESTS_FILE, index=False)
    return redirect(url_for("inventory.view_requests"))


# SR Lookup for Store Issuance
@inventory_bp.route("/sr_lookup", methods=["GET", "POST"])
def sr_lookup():
    request_data = None
    status = None

    if request.method == "POST":
        sr_number = request.form["sr_number"]
        if os.path.exists(REQUESTS_FILE):
            df = pd.read_excel(REQUESTS_FILE)
            row = df[df["SR#"] == sr_number]
            if not row.empty:
                request_data = row.iloc[0].to_dict()
                status = request_data["Status"]
            else:
                status = "not_found"

    return render_template("sr_lookup.html", request_data=request_data, status=status)


# Issue via SR#
@inventory_bp.route("/issue_by_sr/<sr_number>", methods=["POST"])
def issue_item_by_sr(sr_number):
    if not os.path.exists(REQUESTS_FILE) or not os.path.exists(INVENTORY_FILE):
        return "Missing files."

    req_df = pd.read_excel(REQUESTS_FILE)
    inv_df = pd.read_excel(INVENTORY_FILE)
    row = req_df[req_df["SR#"] == sr_number]

    if row.empty:
        return "SR# not found."

    request_data = row.iloc[0]
    if request_data["Status"] != "Approved":
        return "Request not approved."

    item = request_data["ItemName"]
    qty = int(request_data["Quantity"])

    if item in inv_df["ItemName"].values:
        idx = inv_df[inv_df["ItemName"] == item].index[0]
        if inv_df.at[idx, "Quantity"] >= qty:
            inv_df.at[idx, "Quantity"] -= qty
            inv_df.to_excel(INVENTORY_FILE, index=False)

            req_df.loc[req_df["SR#"] == sr_number, "Status"] = "Issued"
            req_df.to_excel(REQUESTS_FILE, index=False)

            log = {
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Action": "Issued (via SR)",
                "ItemName": item,
                "Quantity": qty,
                "IssuedBy": current_user.username,
                "SR#": sr_number
            }
            logs_df = pd.read_excel(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame()
            logs_df = pd.concat([logs_df, pd.DataFrame([log])], ignore_index=True)
            logs_df.to_excel(LOG_FILE, index=False)

            return redirect(url_for("inventory.dashboard"))

        else:
            return "Insufficient stock."
    return "Item not found in inventory."


