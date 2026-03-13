from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import current_user
import pandas as pd
import os
from datetime import datetime
from random import randint
from modules.utils import role_required
from modules.utils import role_required
from flask import session

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")

INVENTORY_FILE = "data/inventory.xlsx"
LOG_FILE = "data/inventory_logs.xlsx"
REQUESTS_FILE = "data/inventory_requests.xlsx"

# Dashboard
@inventory_bp.route("/")
@role_required(['Stores', 'Admin', 'Manager', 'Field Officer', 'HR Officer'])
def dashboard():

    items_by_category = {}

    if os.path.exists(INVENTORY_FILE):

        df = pd.read_excel(INVENTORY_FILE)

        # Clean column names
        df.columns = df.columns.str.strip()

        # Ensure Quantity is numeric
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)

        # ✅ Show only items available in stock
        df = df[df["Quantity"] > 0]

        # Group by category
        for category, group in df.groupby("Category"):
            items_by_category[category] = group.to_dict(orient="records")

    # Low stock alert
    low_stock_items = [
        item for cat_items in items_by_category.values()
        for item in cat_items
        if item["Quantity"] <= item["ReorderLevel"]
    ]

    return render_template(
        "inventory.html",
        items_by_category=items_by_category,
        low_stock_items=low_stock_items
    )


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


@inventory_bp.route("/issue_request/<sr_number>", methods=["GET", "POST"])
@role_required(['Stores', 'Admin'])
def issue_request(sr_number):
    if not os.path.exists(REQUESTS_FILE) or not os.path.exists(INVENTORY_FILE):
        flash("Missing files!", "danger")
        return redirect(url_for("inventory.dashboard"))

    requests_df = pd.read_excel(REQUESTS_FILE)
    inventory_df = pd.read_excel(INVENTORY_FILE)
    request_row = requests_df[requests_df["SR#"] == sr_number]

    if request_row.empty:
        flash("Request not found.", "warning")
        return redirect(url_for("inventory.view_requests"))

    request_data = request_row.iloc[0]

    if request_data["Status"] != "Approved":
        flash("Request not approved yet.", "warning")
        return redirect(url_for("inventory.view_requests"))

    if request.method == "POST":
        issued_to = request.form["issued_to"]
        remarks = request.form.get("remarks", "")
        item_name = request_data["ItemName"]
        qty = int(request_data["Quantity"])

        idx = inventory_df.index[inventory_df["ItemName"] == item_name].tolist()[0]
        if inventory_df.at[idx, "Quantity"] < qty:
            flash("Insufficient stock to issue.", "warning")
            return redirect(url_for("inventory.view_requests"))

        # Deduct from inventory
        inventory_df.at[idx, "Quantity"] -= qty
        inventory_df.to_excel(INVENTORY_FILE, index=False)

        # Log issuance
        logs_df = pd.read_excel(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame()
        log_entry = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Action": "Issued",
            "ItemName": item_name,
            "Quantity": qty,
            "IssuedTo": issued_to,
            "Remarks": remarks,
            "PerformedBy": session.get("username", "Unknown"),
            "SR#": sr_number
        }
        logs_df = pd.concat([logs_df, pd.DataFrame([log_entry])], ignore_index=True)
        logs_df.to_excel(LOG_FILE, index=False)

        # Update request status
        requests_df.loc[requests_df["SR#"] == sr_number, "Status"] = "Issued"
        requests_df.to_excel(REQUESTS_FILE, index=False)

        flash(f"✅ {item_name} issued successfully!", "success")
        return redirect(url_for("inventory.view_requests"))

    return render_template("issue_requests.html", request_data=request_data)

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
            "PerformedBy": session.get("username", "Unknown")
        }

        logs_df = pd.read_excel(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame()
        logs_df = pd.concat([logs_df, pd.DataFrame([log])], ignore_index=True)
        logs_df.to_excel(LOG_FILE, index=False)

        return redirect(url_for("inventory.dashboard"))

    return render_template("replenish_stock.html", items=df["ItemName"].tolist())

INVENTORY_FILE = 'data/inventory.xlsx'
LOG_FILE = 'data/inventory_logs.xlsx'

# Inventory Analytics
@inventory_bp.route('/analytics')
@role_required(['agriculture Manager', 'Manager', 'Stores', 'HR Officer', 'Admin'])
def inventory_analytics():
    inventory_df = pd.read_excel(INVENTORY_FILE) if os.path.exists(INVENTORY_FILE) else pd.DataFrame()
    logs_df = pd.read_excel(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame()

    # Clean headers just in case
    inventory_df.columns = inventory_df.columns.str.strip()
    logs_df.columns = logs_df.columns.str.strip()

    category_counts = inventory_df["Category"].value_counts().to_dict()
    issued_items = logs_df[logs_df["Action"].str.contains("Issued", na=False)]
    top_issued = issued_items["ItemName"].value_counts().head(5).to_dict()

    logs_df["Date"] = pd.to_datetime(logs_df["Date"], errors='coerce')
    trend_series = logs_df.groupby(logs_df["Date"].dt.to_period("M"))["Quantity"].sum().sort_index().to_timestamp()

    # Convert Timestamp keys to string
    trend_data = {str(k.date()): v for k, v in trend_series.items()}

    return render_template("inventory_analytics.html",
                           category_counts=category_counts,
                           top_issued=top_issued,
                           trend_data=trend_data)


# Submit Request (with SR# generation)
from datetime import datetime
import random
import string

def generate_sr_number():
    return "SR" + ''.join(random.choices(string.digits, k=5))

@inventory_bp.route("/request_item", methods=["GET", "POST"])
@role_required(['Manager','Field Officer','HR Officer','Stores','Admin'])
def request_item():
    # Load available items grouped by category
    df = pd.read_excel(INVENTORY_FILE)
    df = df[df['Quantity'] > 0]  # Only available items
    items_by_category = df.groupby('Category').apply(lambda x: x.to_dict(orient='records')).to_dict()

    sr_number = None

    if request.method == "POST":
        selected_items = request.form.getlist("items[]")       # item names
        quantities = request.form.getlist("quantities[]")      # requested quantities
        reasons = request.form.getlist("reasons[]")            # per-item reasons

        if not selected_items:
            flash("⚠ No items selected for request.", "warning")
            return redirect(url_for("inventory.request_item"))

        # Load or create request log
        REQUEST_FILE = "data/inventory_requests.xlsx"
        requests_df = pd.read_excel(REQUEST_FILE) if os.path.exists(REQUEST_FILE) else pd.DataFrame()

        now = pd.Timestamp.now()
        sr_number = f"SR{int(now.timestamp())}"  # simple unique SR number

        # Append each requested item
        for i, item_name in enumerate(selected_items):
            try:
                qty = int(quantities[i])
                reason = reasons[i]
            except (IndexError, ValueError):
                qty = 1
                reason = ""

            log_entry = {
                "SRNumber": sr_number,
                "Date": now,
                "ItemName": item_name,
                "Quantity": qty,
                "Reason": reason,
                "RequestedBy": session.get("username", "Unknown"),
                "Status": "Pending"
            }
            requests_df = pd.concat([requests_df, pd.DataFrame([log_entry])], ignore_index=True)

        requests_df.to_excel(REQUEST_FILE, index=False)
        flash(f"✅ Request submitted successfully. SR#: {sr_number}", "success")
        return render_template("request_item.html", sr_number=sr_number, items_by_category=items_by_category)

    return render_template("request_item.html", items_by_category=items_by_category)


# view_requests route
@inventory_bp.route("/view_requests")
@role_required(['Admin','Stores','Manager','HR Officer','Agriculture Manager'])
def view_requests():
    import pandas as pd
    import os

    if not os.path.exists("data/inventory_requests.xlsx"):
        requests_list = []
    else:
        df = pd.read_excel("data/inventory_requests.xlsx")
        requests_list = df.to_dict(orient="records")

    # Group by SR# (or use SR# generation field)
    grouped_requests = {}
    for req in requests_list:
        sr = req.get('SRNumber', f"SR{req.get('Date','unknown')}")
        if sr not in grouped_requests:
            grouped_requests[sr] = []
        grouped_requests[sr].append(req)

    return render_template("view_requests.html", requests=grouped_requests)


# Approve a single request item
@inventory_bp.route("/approve_request/<sr>/<int:item_idx>", methods=["POST"])
@role_required(['Manager','Admin','Stores'])
def approve_request(sr, item_idx):
    import pandas as pd
    import os

    REQUEST_FILE = "data/inventory_requests.xlsx"

    if not os.path.exists(REQUEST_FILE):
        flash("No requests found!", "warning")
        return redirect(url_for("inventory.view_requests"))

    df = pd.read_excel(REQUEST_FILE)

    # Group by SR#
    grouped = {}
    for i, row in df.iterrows():
        key = row.get("SRNumber", f"SR{row.get('Date','unknown')}")
        grouped.setdefault(key, []).append(i)

    # Update the specific item
    if sr in grouped and item_idx < len(grouped[sr]):
        row_index = grouped[sr][item_idx]
        df.at[row_index, "Status"] = "Approved"
        df.at[row_index, "ApprovedBy"] = session.get("username", "Unknown")
        df.at[row_index, "ApprovalDate"] = pd.Timestamp.now()
        df.to_excel(REQUEST_FILE, index=False)
        flash(f"✅ Request item {sr} #{item_idx+1} approved.", "success")
    else:
        flash("Request item not found.", "danger")

    return redirect(url_for("inventory.view_requests"))


# Reject a single request item
@inventory_bp.route("/reject_request/<sr>/<int:item_idx>", methods=["POST"])
@role_required(['Manager','Admin','Stores'])
def reject_request(sr, item_idx):
    import pandas as pd
    import os

    REQUEST_FILE = "data/inventory_requests.xlsx"

    if not os.path.exists(REQUEST_FILE):
        flash("No requests found!", "warning")
        return redirect(url_for("inventory.view_requests"))

    df = pd.read_excel(REQUEST_FILE)

    # Group by SR#
    grouped = {}
    for i, row in df.iterrows():
        key = row.get("SRNumber", f"SR{row.get('Date','unknown')}")
        grouped.setdefault(key, []).append(i)

    # Update the specific item
    if sr in grouped and item_idx < len(grouped[sr]):
        row_index = grouped[sr][item_idx]
        df.at[row_index, "Status"] = "Rejected"
        df.at[row_index, "ApprovedBy"] = session.get("username", "Unknown")
        df.at[row_index, "ApprovalDate"] = pd.Timestamp.now()
        df.to_excel(REQUEST_FILE, index=False)
        flash(f"❌ Request item {sr} #{item_idx+1} rejected.", "warning")
    else:
        flash("Request item not found.", "danger")

    return redirect(url_for("inventory.view_requests"))


# SR Lookup for Store Issuance
@inventory_bp.route("/sr_lookup", methods=["GET", "POST"])
def sr_lookup():

    requests = None
    status = None

    if request.method == "POST":

        sr_number = request.form["sr_number"].strip()

        if os.path.exists(REQUESTS_FILE):

            df = pd.read_excel(REQUESTS_FILE)

            # Clean column names
            df.columns = df.columns.str.strip()

            # Ensure SRNumber is string
            df["SRNumber"] = df["SRNumber"].astype(str)

            rows = df[df["SRNumber"] == sr_number]

            if not rows.empty:
                requests = rows.to_dict(orient="records")
                status = rows.iloc[0]["Status"]
            else:
                status = "not_found"

    return render_template(
        "sr_lookup.html",
        requests=requests,
        status=status
    )


@inventory_bp.route("/issue_page")
@role_required(['Stores','Admin'])
def issue_page():

    if not os.path.exists(REQUESTS_FILE):
        flash("No request file found.", "warning")
        return redirect(url_for("inventory.dashboard"))

    df = pd.read_excel(REQUESTS_FILE)

    approved = df[df["Status"] == "Approved"]

    requests = approved.to_dict(orient="records")

    return render_template(
        "issue_requests.html",
        requests=requests
    )

from flask import request, render_template, redirect, url_for, flash
from modules.utils import role_required
from datetime import datetime
import pandas as pd
import random

@inventory_bp.route("/issue_form/<sr_number>")
@role_required(['Stores','Admin'])
def issue_form(sr_number):
    # Ensure SR# is treated as string
    sr_number = str(sr_number)

    # Load requests
    req_df = pd.read_excel(REQUESTS_FILE)
    req_df["SRNumber"] = req_df["SRNumber"].astype(str)  # make sure comparison works

    # Filter approved request
    rows = req_df[(req_df["SRNumber"] == sr_number) & (req_df["Status"] == "Approved")]

    if rows.empty:
        flash("Request not found or not approved.", "danger")
        return redirect(url_for("inventory.issue_page"))

    # Convert to dict for template
    requests = rows.to_dict(orient="records")

    # Auto-generate date, time, pass-out
    current_datetime = datetime.now()
    auto_pass_out = f"PO-{random.randint(1000,9999)}-{current_datetime.strftime('%Y%m%d%H%M')}"

    # Pass to template
    return render_template(
        "issue_list.html",
        requests=requests,
        sr_number=sr_number,
        date=current_datetime.strftime("%Y-%m-%d"),
        time=current_datetime.strftime("%H:%M"),
        pass_out_no=auto_pass_out
    )

# Issue via SR#
@inventory_bp.route("/issue_by_sr/<sr_number>", methods=["POST"])
@role_required(['Stores','Admin'])
def issue_item_by_sr(sr_number):

    if not os.path.exists(REQUESTS_FILE) or not os.path.exists(INVENTORY_FILE):
        flash("Missing inventory files.", "danger")
        return redirect(url_for("inventory.dashboard"))

    req_df = pd.read_excel(REQUESTS_FILE)
    inv_df = pd.read_excel(INVENTORY_FILE)

    issued_to = request.form.get("issued_to")
    remarks = request.form.get("remarks", "")

    sr_rows = req_df[req_df["SRNumber"] == sr_number]

    if sr_rows.empty:
        flash("SR# not found.", "danger")
        return redirect(url_for("inventory.view_requests"))

    for idx, row in sr_rows.iterrows():

        if row["Status"] != "Approved":
            continue

        item = row["ItemName"]
        qty = int(row["Quantity"])

        if item in inv_df["ItemName"].values:

            inv_idx = inv_df[inv_df["ItemName"] == item].index[0]

            if inv_df.at[inv_idx, "Quantity"] >= qty:

                # Deduct inventory
                inv_df.at[inv_idx, "Quantity"] -= qty

                # Update request status
                req_df.at[idx, "Status"] = "Issued"

                # Log transaction
                log = {
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Action": "Issued via SR",
                    "ItemName": item,
                    "Quantity": qty,
                    "IssuedTo": issued_to,
                    "Remarks": remarks,
                    "IssuedBy": session.get("username"),
                    "SR#": sr_number
                }

                logs_df = pd.read_excel(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame()
                logs_df = pd.concat([logs_df, pd.DataFrame([log])], ignore_index=True)
                logs_df.to_excel(LOG_FILE, index=False)

            else:
                flash(f"Not enough stock for {item}.", "warning")

        else:
            flash(f"{item} not found in inventory.", "danger")

    inv_df.to_excel(INVENTORY_FILE, index=False)
    req_df.to_excel(REQUESTS_FILE, index=False)

    flash(f"Items for SR# {sr_number} issued successfully.", "success")

    return redirect(url_for("inventory.dashboard"))



@inventory_bp.route("/my_requests")
@role_required(['Stores','Manager','Field Officer','HR Officer','Admin'])
def my_requests():
    import pandas as pd
    import os

    if not os.path.exists(REQUESTS_FILE):
        flash("No requests found.", "warning")
        return redirect(url_for("inventory.dashboard"))

    df = pd.read_excel(REQUESTS_FILE)

    username = session.get("username")

    my_df = df[df["RequestedBy"] == username]

    return render_template(
        "my_requests.html",
        requests=my_df.to_dict(orient="records")
    )


@inventory_bp.route("/confirm_issue/<sr_number>", methods=["POST"])
@role_required(["Stores"])
def confirm_issue(sr_number):
    # Load requests
    req_df = pd.read_excel(REQUESTS_FILE)
    row = req_df[req_df["SRNumber"] == sr_number]

    if row.empty:
        return "SR# not found."

    request_data = row.iloc[0]
    if request_data["Status"] != "Approved":
        return "Request not approved."

    # Load inventory
    inv_df = pd.read_excel(INVENTORY_FILE)
    item = request_data["ItemName"]
    qty = int(request_data["Quantity"])
    idx = inv_df.index[inv_df["ItemName"] == item].tolist()[0]

    if inv_df.at[idx, "Quantity"] < qty:
        return f"Insufficient stock for {item}."

    # Deduct inventory
    inv_df.at[idx, "Quantity"] -= qty
    inv_df.to_excel(INVENTORY_FILE, index=False)

    # Update request status
    req_df.loc[req_df["SRNumber"] == sr_number, "Status"] = "Issued"
    req_df.to_excel(REQUESTS_FILE, index=False)

    # Log issuance
    logs_df = pd.read_excel(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame()
    log_entry = {
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Action": "Issued",
        "SR#": sr_number,
        "Collector": request.form["collector"],
        "Department": request.form.get("department",""),
        "PassOutNo": request.form.get("pass_out_no"),
        "IssuedBy": session.get("username", "Stores"),
        "Remarks": request.form.get("remarks",""),
        "ItemName": item,
        "Quantity": qty
    }
    logs_df = pd.concat([logs_df, pd.DataFrame([log_entry])], ignore_index=True)
    logs_df.to_excel(LOG_FILE, index=False)

    return redirect(url_for("inventory.dashboard"))