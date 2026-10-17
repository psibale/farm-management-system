# ==========================================================
# AGRICULTURE REQUESTS & APPROVAL MODULE
# ==========================================================
#
# Single authority for ALL Agriculture approvals.
#
# Registers:
#
#   data/chemical_requests.xlsx
#       Existing Chemical / Herbicide Request Register
#
#   data/agriculture_requests.xlsx
#       General Agriculture Request Register
#
# This module does NOT replace the chemical request register.
# It provides the central Agriculture approval layer for both.
#
# ==========================================================

import os
from functools import lru_cache
from datetime import datetime

import pandas as pd

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from modules.season import get_active_season


# ==========================================================
# BLUEPRINT
# ==========================================================

agriculture_requests_bp = Blueprint(
    "agriculture_requests",
    __name__
)


# ==========================================================
# FILE PATHS
# ==========================================================

CHEMICAL_REQUEST_FILE = "data/chemical_requests.xlsx"

AGRICULTURE_REQUEST_FILE = "data/agriculture_requests.xlsx"

AGRICULTURE_REQUEST_HISTORY_FILE = (
    "data/agriculture_request_history.xlsx"
)


# ==========================================================
# GENERAL AGRICULTURE REQUEST CATEGORIES
# ==========================================================

AGRICULTURE_REQUEST_CATEGORIES = [
    "HERBICIDE",
    "PESTICIDE",
    "FERTILIZER",
    "FUEL",
    "STATIONERY",
    "PPE",
    "TOOLS",
    "SPARE PARTS",
    "EQUIPMENT",
    "OTHER"
]


# ==========================================================
# REQUEST TYPES
# ==========================================================

AGRICULTURE_REQUEST_TYPES = [
    "OPERATIONAL",
    "PROGRAMME",
    "EMERGENCY",
    "OTHER"
]


# ==========================================================
# URGENCY
# ==========================================================

AGRICULTURE_REQUEST_URGENCY = [
    "NORMAL",
    "URGENT",
    "CRITICAL"
]


# ==========================================================
# STATUS
# ==========================================================

AGRICULTURE_REQUEST_STATUSES = [
    "PENDING",
    "APPROVED",
    "REJECTED",
    "PARTIAL",
    "ISSUED",
    "CANCELLED"
]


# ==========================================================
# GENERAL AGRICULTURE REQUEST COLUMNS
# ==========================================================

AGRICULTURE_REQUEST_COLUMNS = [
    "Request ID",
    "Request Date",
    "Season",
    "Request Type",
    "Request Category",
    "Department",
    "Requester",
    "Item / Description",
    "Specification",
    "Quantity",
    "Quantity Unit",
    "Field",
    "Programme ID",
    "Required Date",
    "Urgency",
    "Reason",
    "Notes",
    "Status",
    "Approved By",
    "Approval Date",
    "Rejection Reason",
    "Stores Request ID",
    "Stores Request Date",
    "Issued Quantity",
    "Issue Date"
]


# ==========================================================
# REQUEST HISTORY COLUMNS
# ==========================================================

AGRICULTURE_REQUEST_HISTORY_COLUMNS = [
    "Request ID",
    "Event Date",
    "Event",
    "User",
    "Role",
    "Status",
    "Details"
]


# ==========================================================
# APPROVAL ROLES
# ==========================================================

AGRICULTURE_APPROVAL_ROLES = [
    "Admin",
    "Manager",
    "Agriculture Manager"
]


# ==========================================================
# INTERNAL HELPERS
# ==========================================================

def _clean(value):
    """
    Convert a value to a clean string.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def _normalise_status(value):
    """
    Return a standard uppercase status.
    """

    return _clean(value).upper()


def _normalise_category(value):
    """
    Return a standard uppercase category.
    """

    return _clean(value).upper()


def _normalise_season(value):
    """
    Return a clean season value.
    """

    return _clean(value)


def _current_user():
    """
    Return the currently logged-in username.
    """

    return _clean(session.get("username"))


def _current_role():
    """
    Try the common session keys used for role information.
    """

    role = session.get("role")

    if not role:
        role = session.get("user_role")

    if not role:
        role = session.get("Role")

    return _clean(role)


def _is_approval_role():
    """
    Determine whether the current user can perform
    Agriculture approvals.
    """

    role = _current_role()

    return role in AGRICULTURE_APPROVAL_ROLES


def _ensure_directory(filepath):
    """
    Ensure the directory containing a file exists.
    """

    directory = os.path.dirname(filepath)

    if directory:
        os.makedirs(directory, exist_ok=True)


@lru_cache(maxsize=4)
def _read_excel_cached(filepath, modified_ns):
    """Read an unchanged workbook once per process.

    Including the file modification time in the cache key means edits made
    by this application or directly in Excel are picked up automatically.
    Callers receive copies so normal DataFrame edits cannot alter the cache.
    """
    return pd.read_excel(
        filepath,
        engine="openpyxl"
    )


# ==========================================================
# CHEMICAL REQUEST REGISTER
# ==========================================================

def load_chemical_requests():
    """
    Load the existing chemical/herbicide request register.

    IMPORTANT:
    This function deliberately keeps the existing file:

        data/chemical_requests.xlsx

    so existing chemical request functionality remains
    compatible.
    """

    if not os.path.exists(CHEMICAL_REQUEST_FILE):
        return pd.DataFrame()

    try:
        modified_ns = os.stat(CHEMICAL_REQUEST_FILE).st_mtime_ns
        df = _read_excel_cached(
            CHEMICAL_REQUEST_FILE,
            modified_ns
        ).copy()
    except Exception as e:
        print("Error loading chemical requests:")
        print(e)
        return pd.DataFrame()

    return df


# ==========================================================
# GENERAL AGRICULTURE REQUEST REGISTER
# ==========================================================

def load_agriculture_requests():
    """
    Load the general Agriculture Request Register.

    File:

        data/agriculture_requests.xlsx

    Missing columns are automatically created.
    """

    _ensure_directory(AGRICULTURE_REQUEST_FILE)

    if not os.path.exists(AGRICULTURE_REQUEST_FILE):
        return pd.DataFrame(
            columns=AGRICULTURE_REQUEST_COLUMNS
        )

    try:
        modified_ns = os.stat(AGRICULTURE_REQUEST_FILE).st_mtime_ns
        df = _read_excel_cached(
            AGRICULTURE_REQUEST_FILE,
            modified_ns
        ).copy()
    except Exception as e:
        print("Error loading Agriculture requests:")
        print(e)

        return pd.DataFrame(
            columns=AGRICULTURE_REQUEST_COLUMNS
        )

    # ------------------------------------------------------
    # Ensure all expected columns exist
    # ------------------------------------------------------

    for column in AGRICULTURE_REQUEST_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    # ------------------------------------------------------
    # Preserve standard column order
    # ------------------------------------------------------

    df = df[AGRICULTURE_REQUEST_COLUMNS].copy()

    return df


# ==========================================================
# SAVE GENERAL AGRICULTURE REQUESTS
# ==========================================================

def save_agriculture_requests(df):
    """
    Save the general Agriculture Request Register.
    """

    _ensure_directory(AGRICULTURE_REQUEST_FILE)

    for column in AGRICULTURE_REQUEST_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[AGRICULTURE_REQUEST_COLUMNS].copy()

    df.to_excel(
        AGRICULTURE_REQUEST_FILE,
        index=False,
        engine="openpyxl"
    )


# ==========================================================
# REQUEST HISTORY
# ==========================================================

def load_agriculture_request_history():
    """
    Load Agriculture request history.

    This is separate from the request register so that
    approvals/rejections can have an audit trail.
    """

    _ensure_directory(
        AGRICULTURE_REQUEST_HISTORY_FILE
    )

    if not os.path.exists(
        AGRICULTURE_REQUEST_HISTORY_FILE
    ):
        return pd.DataFrame(
            columns=AGRICULTURE_REQUEST_HISTORY_COLUMNS
        )

    try:
        df = pd.read_excel(
            AGRICULTURE_REQUEST_HISTORY_FILE,
            engine="openpyxl"
        )
    except Exception as e:
        print("Error loading Agriculture request history:")
        print(e)

        return pd.DataFrame(
            columns=AGRICULTURE_REQUEST_HISTORY_COLUMNS
        )

    for column in AGRICULTURE_REQUEST_HISTORY_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df[
        AGRICULTURE_REQUEST_HISTORY_COLUMNS
    ].copy()


# ==========================================================
# SAVE REQUEST HISTORY
# ==========================================================

def save_agriculture_request_history(df):
    """
    Save Agriculture request history.
    """

    _ensure_directory(
        AGRICULTURE_REQUEST_HISTORY_FILE
    )

    for column in AGRICULTURE_REQUEST_HISTORY_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[
        AGRICULTURE_REQUEST_HISTORY_COLUMNS
    ].copy()

    df.to_excel(
        AGRICULTURE_REQUEST_HISTORY_FILE,
        index=False,
        engine="openpyxl"
    )


# ==========================================================
# LOG REQUEST EVENT
# ==========================================================

def log_agriculture_request_event(
    request_id,
    event,
    user="",
    role="",
    status="",
    details=""
):
    """
    Add an event to the Agriculture Request History.

    Examples:

        CREATED
        APPROVED
        REJECTED
        CANCELLED
        STORES REQUEST RAISED
        ISSUED
    """

    history_df = load_agriculture_request_history()

    new_event = {
        "Request ID": _clean(request_id),
        "Event Date": pd.Timestamp.now(),
        "Event": _clean(event),
        "User": _clean(user),
        "Role": _clean(role),
        "Status": _clean(status),
        "Details": _clean(details)
    }

    history_df = pd.concat(
        [
            history_df,
            pd.DataFrame([new_event])
        ],
        ignore_index=True
    )

    save_agriculture_request_history(
        history_df
    )


# ==========================================================
# GET REQUEST HISTORY
# ==========================================================

def get_agriculture_request_history(request_id):
    """
    Return history for one request.
    """

    history_df = load_agriculture_request_history()

    if history_df.empty:
        return []

    request_id = _clean(request_id)

    history_df = history_df[
        history_df["Request ID"]
        .astype(str)
        .str.strip()
        == request_id
    ].copy()

    if history_df.empty:
        return []

    if "Event Date" in history_df.columns:
        history_df = history_df.sort_values(
            "Event Date"
        )

    return history_df.to_dict(
        orient="records"
    )


# ==========================================================
# GENERAL AGRICULTURE REQUEST ID
# ==========================================================

def generate_agriculture_request_id(
    df,
    season
):
    """
    Generate a general Agriculture Request ID.

    The season separator "/" is converted to "-"
    so the Request ID is safe to use in Flask URLs.

    Examples:

        AR-2026-27-0001
        AR-2026-27-0002
        AR-2026-27-0003
    """

    season = _clean(season)

    # ------------------------------------------------------
    # Make the season URL-safe
    #
    # 2026/27 -> 2026-27
    # ------------------------------------------------------

    safe_season = season.replace("/", "-")

    prefix = f"AR-{safe_season}-"

    highest_number = 0

    if df is not None and not df.empty:

        if "Request ID" in df.columns:

            for request_id in (
                df["Request ID"]
                .astype(str)
                .tolist()
            ):

                request_id = request_id.strip()

                if not request_id.startswith(prefix):
                    continue

                try:

                    number = int(
                        request_id
                        .replace(prefix, "", 1)
                    )

                    highest_number = max(
                        highest_number,
                        number
                    )

                except ValueError:
                    continue

    return (
        f"{prefix}"
        f"{highest_number + 1:04d}"
    )


# ==========================================================
# FIND REQUEST
# ==========================================================

def find_agriculture_request(
    df,
    request_id
):
    """
    Find a request by Request ID.

    Returns:
        row_index, row
    """

    if df is None or df.empty:
        return None, None

    request_id = _clean(request_id)

    if "Request ID" not in df.columns:
        return None, None

    matches = df[
        df["Request ID"]
        .astype(str)
        .str.strip()
        == request_id
    ]

    if matches.empty:
        return None, None

    index = matches.index[0]

    return index, df.loc[index]


# ==========================================================
# CHECK WHETHER REQUEST IS PENDING
# ==========================================================

def is_request_pending(row):
    """
    Return True only when request status is PENDING.
    """

    if row is None:
        return False

    return (
        _normalise_status(
            row.get("Status", "")
        )
        == "PENDING"
    )


def get_pending_agriculture_approval_count(season=None):
    """Count pending agriculture and chemical requests for a season.

    This follows the same source files, season filters, and pending status
    used by the Agriculture Approval Centre.
    """
    season = season or get_active_season()
    pending_count = 0

    agriculture_df = load_agriculture_requests()
    if not agriculture_df.empty:
        agriculture_df = agriculture_df[
            agriculture_df["Season"].astype(str).str.strip()
            == str(season).strip()
        ]
        pending_count += sum(
            is_request_pending(record)
            for record in agriculture_df.to_dict(orient="records")
        )

    chemical_df = load_chemical_requests()
    if not chemical_df.empty:
        if "Season" in chemical_df.columns:
            chemical_df = chemical_df[
                chemical_df["Season"].astype(str).str.strip()
                == str(season).strip()
            ]
        pending_count += sum(
            is_request_pending(record)
            for record in chemical_df.to_dict(orient="records")
        )

    return pending_count


# ==========================================================
# SELF-APPROVAL PROTECTION
# ==========================================================

def can_user_approve_request(row):
    """
    A requester cannot approve or reject their own
    Agriculture request.
    """

    if row is None:
        return False

    requester = _clean(
        row.get("Requester", "")
    ).lower()

    current_user = _current_user().lower()

    if not requester or not current_user:
        return False

    return requester != current_user


# ==========================================================
# ACTIVE-SEASON REQUESTS
# ==========================================================

def get_active_agriculture_requests():
    """
    Return general Agriculture requests for the active season.
    """

    season = get_active_season()

    df = load_agriculture_requests()

    if df.empty:
        return df

    if "Season" not in df.columns:
        return pd.DataFrame(
            columns=AGRICULTURE_REQUEST_COLUMNS
        )

    return df[
        df["Season"]
        .astype(str)
        .str.strip()
        == str(season).strip()
    ].copy()


# ==========================================================
# CREATE GENERAL AGRICULTURE REQUEST
# ==========================================================

def create_agriculture_request(
    request_type="OPERATIONAL",
    request_category="OTHER",
    department="Agriculture",
    requester="",
    item_description="",
    specification="",
    quantity="",
    quantity_unit="",
    field="",
    programme_id="",
    required_date="",
    urgency="NORMAL",
    reason="",
    notes=""
):
    """
    Create a general Agriculture request.

    This function writes to:

        data/agriculture_requests.xlsx

    It does NOT write to chemical_requests.xlsx.
    """

    season = get_active_season()

    df = load_agriculture_requests()

    request_id = generate_agriculture_request_id(
        df,
        season
    )

    row = {
        "Request ID": request_id,
        "Request Date": pd.Timestamp.now(),
        "Season": season,
        "Request Type": _clean(
            request_type
        ).upper(),
        "Request Category": _clean(
            request_category
        ).upper(),
        "Department": _clean(
            department
        ),
        "Requester": _clean(
            requester
        ),
        "Item / Description": _clean(
            item_description
        ),
        "Specification": _clean(
            specification
        ),
        "Quantity": quantity,
        "Quantity Unit": _clean(
            quantity_unit
        ),
        "Field": _clean(
            field
        ),
        "Programme ID": _clean(
            programme_id
        ),
        "Required Date": required_date,
        "Urgency": _clean(
            urgency
        ).upper() or "NORMAL",
        "Reason": _clean(
            reason
        ),
        "Notes": _clean(
            notes
        ),
        "Status": "PENDING",
        "Approved By": "",
        "Approval Date": "",
        "Rejection Reason": "",
        "Stores Request ID": "",
        "Stores Request Date": "",
        "Issued Quantity": "",
        "Issue Date": ""
    }

    df = pd.concat(
        [
            df,
            pd.DataFrame([row])
        ],
        ignore_index=True
    )

    save_agriculture_requests(df)

    # ------------------------------------------------------
    # History
    # ------------------------------------------------------

    log_agriculture_request_event(
        request_id=request_id,
        event="CREATED",
        user=requester,
        role="",
        status="PENDING",
        details=(
            f"{row['Request Category']} request created."
        )
    )

    return request_id


# ==========================================================
# APPROVE GENERAL AGRICULTURE REQUEST
# ==========================================================

def approve_agriculture_request(
    request_id,
    approved_by=None
):
    """
    Approve a general Agriculture request.

    Approval is allowed only when:

        - Request exists
        - Request belongs to active season
        - Status is PENDING
        - Approver is an authorised Agriculture approval role
        - Approver is not the requester
    """

    if not _is_approval_role():
        return False, (
            "You are not authorised to approve "
            "Agriculture requests."
        )

    approved_by = (
        _clean(approved_by)
        or _current_user()
    )

    season = get_active_season()

    df = load_agriculture_requests()

    index, row = find_agriculture_request(
        df,
        request_id
    )

    if row is None:
        return False, "Agriculture request was not found."

    request_season = _normalise_season(
        row.get("Season", "")
    )

    if request_season != _clean(season):
        return False, (
            "This request does not belong to "
            "the active season."
        )

    if not is_request_pending(row):
        return False, (
            "Only PENDING requests can be approved."
        )

    if not can_user_approve_request(row):
        return False, (
            "You cannot approve your own Agriculture request."
        )

    # ------------------------------------------------------
    # Apply approval
    # ------------------------------------------------------

    df.at[
        index,
        "Status"
    ] = "APPROVED"

    df.at[
        index,
        "Approved By"
    ] = approved_by

    df.at[
        index,
        "Approval Date"
    ] = pd.Timestamp.now()

    df.at[
        index,
        "Rejection Reason"
    ] = ""

    save_agriculture_requests(df)

    # ------------------------------------------------------
    # History
    # ------------------------------------------------------

    log_agriculture_request_event(
        request_id=request_id,
        event="APPROVED",
        user=approved_by,
        role=_current_role(),
        status="APPROVED",
        details=(
            "Agriculture request approved."
        )
    )

    return True, (
        "Agriculture request approved successfully."
    )


# ==========================================================
# REJECT GENERAL AGRICULTURE REQUEST
# ==========================================================

def reject_agriculture_request(
    request_id,
    rejection_reason,
    rejected_by=None
):
    """
    Reject a general Agriculture request.

    A rejection reason is mandatory.
    """

    if not _is_approval_role():
        return False, (
            "You are not authorised to reject "
            "Agriculture requests."
        )

    rejection_reason = _clean(
        rejection_reason
    )

    if not rejection_reason:
        return False, (
            "A rejection reason is required."
        )

    rejected_by = (
        _clean(rejected_by)
        or _current_user()
    )

    season = get_active_season()

    df = load_agriculture_requests()

    index, row = find_agriculture_request(
        df,
        request_id
    )

    if row is None:
        return False, "Agriculture request was not found."

    request_season = _normalise_season(
        row.get("Season", "")
    )

    if request_season != _clean(season):
        return False, (
            "This request does not belong to "
            "the active season."
        )

    if not is_request_pending(row):
        return False, (
            "Only PENDING requests can be rejected."
        )

    if not can_user_approve_request(row):
        return False, (
            "You cannot reject your own Agriculture request."
        )

    # ------------------------------------------------------
    # Apply rejection
    # ------------------------------------------------------

    df.at[
        index,
        "Status"
    ] = "REJECTED"

    df.at[
        index,
        "Approved By"
    ] = rejected_by

    df.at[
        index,
        "Approval Date"
    ] = pd.Timestamp.now()

    df.at[
        index,
        "Rejection Reason"
    ] = rejection_reason

    save_agriculture_requests(df)

    # ------------------------------------------------------
    # History
    # ------------------------------------------------------

    log_agriculture_request_event(
        request_id=request_id,
        event="REJECTED",
        user=rejected_by,
        role=_current_role(),
        status="REJECTED",
        details=rejection_reason
    )

    return True, (
        "Agriculture request rejected."
    )


# ==========================================================
# AGRICULTURE APPROVAL DASHBOARD
# ==========================================================

@agriculture_requests_bp.route(
    "/agriculture/approvals",
    methods=["GET"]
)
def agriculture_approvals():

    # ------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------

    if "username" not in session:
        return redirect(
            url_for("login")
        )

    # ------------------------------------------------------
    # ROLE PROTECTION
    # ------------------------------------------------------

    if not _is_approval_role():
        flash(
            "You are not authorised to access "
            "the Agriculture Approval Centre.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    season = get_active_season()

    # ------------------------------------------------------
    # GENERAL AGRICULTURE REQUESTS
    # ------------------------------------------------------

    agriculture_df = (
        load_agriculture_requests()
    )

    if not agriculture_df.empty:

        agriculture_df = agriculture_df[
            agriculture_df["Season"]
            .astype(str)
            .str.strip()
            == str(season).strip()
        ].copy()

    # ------------------------------------------------------
    # CHEMICAL REQUESTS
    # ------------------------------------------------------
    #
    # Chemical requests remain in their own register.
    # They are brought into the Agriculture Approval Centre
    # for approval.
    #
    # IMPORTANT:
    # We do NOT copy them into agriculture_requests.xlsx.
    #
    # ------------------------------------------------------

    chemical_df = load_chemical_requests()

    if not chemical_df.empty:

        if "Season" in chemical_df.columns:

            chemical_df = chemical_df[
                chemical_df["Season"]
                .astype(str)
                .str.strip()
                == str(season).strip()
            ].copy()

    # ------------------------------------------------------
    # Build unified approval records
    # ------------------------------------------------------

    records = []

    # ------------------------------------------------------
    # General Agriculture requests
    # ------------------------------------------------------

    if not agriculture_df.empty:

        for _, row in agriculture_df.iterrows():

            record = row.to_dict()

            record["_Source"] = "AGRICULTURE"
            record["_Request ID"] = _clean(
                row.get("Request ID", "")
            )

            records.append(record)

    # ------------------------------------------------------
    # Chemical / Herbicide requests
    # ------------------------------------------------------

    if not chemical_df.empty:

        for _, row in chemical_df.iterrows():

            record = row.to_dict()

            record["_Source"] = "CHEMICAL"
            record["_Request ID"] = _clean(
                row.get("Request ID", "")
            )

            # --------------------------------------------------
            # Map chemical fields to generic approval fields
            # without changing the original register.
            # --------------------------------------------------

            if not _clean(
                record.get("Request Category", "")
            ):

                record["Request Category"] = (
                    "HERBICIDE"
                )

            if not _clean(
                record.get("Item / Description", "")
            ):

                record["Item / Description"] = (
                    record.get("Chemical", "")
                )

            if not _clean(
                record.get("Quantity", "")
            ):

                record["Quantity"] = (
                    record.get(
                        "Requested Quantity",
                        ""
                    )
                )

            if not _clean(
                record.get("Quantity Unit", "")
            ):

                record["Quantity Unit"] = (
                    record.get(
                        "Quantity Unit",
                        ""
                    )
                )

            record["_Approval Source"] = (
                "chemical_requests.xlsx"
            )

            records.append(record)

    # ------------------------------------------------------
    # Filters
    # ------------------------------------------------------

    category = _clean(
        request.args.get(
            "category"
        )
    ).upper()

    request_type = _clean(
        request.args.get(
            "request_type"
        )
    ).upper()

    urgency = _clean(
        request.args.get(
            "urgency"
        )
    ).upper()

    status = _clean(
        request.args.get(
            "status"
        )
    ).upper()

    requester = _clean(
        request.args.get(
            "requester"
        )
    )

    search = _clean(
        request.args.get(
            "search"
        )
    ).lower()

    date_filter = _clean(
        request.args.get(
            "date"
        )
    )

    # ------------------------------------------------------
    # Apply filters
    # ------------------------------------------------------

    filtered_records = []

    for record in records:

        record_category = _normalise_category(
            record.get(
                "Request Category",
                ""
            )
        )

        record_type = _clean(
            record.get(
                "Request Type",
                ""
            )
        ).upper()

        record_urgency = _clean(
            record.get(
                "Urgency",
                ""
            )
        ).upper()

        record_status = _normalise_status(
            record.get(
                "Status",
                ""
            )
        )

        record_requester = _clean(
            record.get(
                "Requester",
                ""
            )
        )

        if category and record_category != category:
            continue

        if request_type and record_type != request_type:
            continue

        if urgency and record_urgency != urgency:
            continue

        if status and record_status != status:
            continue

        if requester and (
            record_requester.lower()
            != requester.lower()
        ):
            continue

        # --------------------------------------------------
        # Date filter
        # --------------------------------------------------

        if date_filter:

            request_date = record.get(
                "Request Date",
                ""
            )

            try:
                request_date = pd.to_datetime(
                    request_date
                ).strftime("%Y-%m-%d")

            except Exception:
                request_date = ""

            if request_date != date_filter:
                continue

        # --------------------------------------------------
        # Search
        # --------------------------------------------------

        if search:

            searchable = " ".join([
                _clean(
                    record.get(
                        "Request ID",
                        ""
                    )
                ),
                _clean(
                    record.get(
                        "_Request ID",
                        ""
                    )
                ),
                _clean(
                    record.get(
                        "Request Category",
                        ""
                    )
                ),
                _clean(
                    record.get(
                        "Item / Description",
                        ""
                    )
                ),
                _clean(
                    record.get(
                        "Chemical",
                        ""
                    )
                ),
                _clean(
                    record.get(
                        "Requester",
                        ""
                    )
                ),
                _clean(
                    record.get(
                        "Field",
                        ""
                    )
                ),
                _clean(
                    record.get(
                        "Programme ID",
                        ""
                    )
                )
            ]).lower()

            if search not in searchable:
                continue

        filtered_records.append(
            record
        )

    # ------------------------------------------------------
    # KPI summary
    # ------------------------------------------------------

    total = len(records)

    pending = sum(
        1
        for record in records
        if _normalise_status(
            record.get("Status", "")
        ) == "PENDING"
    )

    approved = sum(
        1
        for record in records
        if _normalise_status(
            record.get("Status", "")
        ) == "APPROVED"
    )

    rejected = sum(
        1
        for record in records
        if _normalise_status(
            record.get("Status", "")
        ) == "REJECTED"
    )

    urgent = sum(
        1
        for record in records
        if _clean(
            record.get("Urgency", "")
        ).upper()
        in ["URGENT", "CRITICAL"]
    )

    # ------------------------------------------------------
    # Sort:
    #
    # PENDING first
    # URGENT/CRITICAL first
    # then newest requests
    # ------------------------------------------------------

    def sort_key(record):

        record_status = _normalise_status(
            record.get("Status", "")
        )

        record_urgency = _clean(
            record.get("Urgency", "")
        ).upper()

        status_order = {
            "PENDING": 1,
            "APPROVED": 2,
            "REJECTED": 3,
            "PARTIAL": 4,
            "ISSUED": 5,
            "CANCELLED": 6
        }

        urgency_order = {
            "CRITICAL": 1,
            "URGENT": 2,
            "NORMAL": 3
        }

        try:
            date_value = pd.to_datetime(
                record.get(
                    "Request Date",
                    ""
                )
            )

        except Exception:
            date_value = pd.Timestamp(
                "1900-01-01"
            )

        return (
            status_order.get(
                record_status,
                99
            ),
            urgency_order.get(
                record_urgency,
                99
            ),
            -date_value.timestamp()
        )

    filtered_records.sort(
        key=sort_key
    )

    # Render only one small page of requests. Both desktop and mobile
    # layouts are present in the template, so limiting this list also keeps
    # the generated HTML compact on phones and large screens alike.
    page_size = 30
    filtered_total = len(filtered_records)
    total_pages = max(
        1,
        (filtered_total + page_size - 1) // page_size
    )

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    page = min(page, total_pages)
    page_offset = (page - 1) * page_size
    page_start = page_offset + 1 if filtered_total else 0
    page_end = min(page_offset + page_size, filtered_total)
    filtered_records = filtered_records[
        page_offset:page_offset + page_size
    ]

    # ------------------------------------------------------
    # Filter options
    # ------------------------------------------------------

    categories = sorted(
        {
            _normalise_category(
                record.get(
                    "Request Category",
                    ""
                )
            )
            for record in records
            if _clean(
                record.get(
                    "Request Category",
                    ""
                )
            )
        }
    )

    request_types = sorted(
        {
            _clean(
                record.get(
                    "Request Type",
                    ""
                )
            ).upper()
            for record in records
            if _clean(
                record.get(
                    "Request Type",
                    ""
                )
            )
        }
    )

    requesters = sorted(
        {
            _clean(
                record.get(
                    "Requester",
                    ""
                )
            )
            for record in records
            if _clean(
                record.get(
                    "Requester",
                    ""
                )
            )
        }
    )

    return render_template(
        "agriculture/agriculture_approvals.html",
        season=season,
        records=filtered_records,
        filtered_total=filtered_total,
        page=page,
        total_pages=total_pages,
        page_start=page_start,
        page_end=page_end,
        total=total,
        pending=pending,
        approved=approved,
        rejected=rejected,
        urgent=urgent,
        categories=categories,
        request_types=request_types,
        requesters=requesters,
        current_category=category,
        current_request_type=request_type,
        current_urgency=urgency,
        current_status=status,
        current_requester=requester,
        current_search=search,
        current_date=date_filter
    )


# ==========================================================
# AGRICULTURE REQUEST REVIEW
# ==========================================================

@agriculture_requests_bp.route(
    "/agriculture/approval/<request_id>",
    methods=["GET"]
)
def agriculture_request_review(
    request_id
):

    # ------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------

    if "username" not in session:
        return redirect(
            url_for("login")
        )

    # ------------------------------------------------------
    # ROLE
    # ------------------------------------------------------

    if not _is_approval_role():
        flash(
            "You are not authorised to review "
            "Agriculture requests.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    season = get_active_season()

    request_id = _clean(
        request_id
    )

    # ------------------------------------------------------
    # Search general Agriculture register
    # ------------------------------------------------------

    agriculture_df = (
        load_agriculture_requests()
    )

    index, row = find_agriculture_request(
        agriculture_df,
        request_id
    )

    source = "AGRICULTURE"

    # ------------------------------------------------------
    # If not found, search chemical register
    # ------------------------------------------------------

    if row is None:

        chemical_df = (
            load_chemical_requests()
        )

        index, row = find_agriculture_request(
            chemical_df,
            request_id
        )

        source = "CHEMICAL"

    # ------------------------------------------------------
    # Not found
    # ------------------------------------------------------

    if row is None:

        flash(
            "Agriculture request was not found.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_approvals"
            )
        )

    # ------------------------------------------------------
    # Convert row to dictionary
    # ------------------------------------------------------

    record = row.to_dict()

    # ------------------------------------------------------
    # Verify active season
    # ------------------------------------------------------

    request_season = _clean(
        record.get(
            "Season",
            ""
        )
    )

    if request_season != _clean(season):

        flash(
            "This request does not belong to "
            "the active season.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_approvals"
            )
        )

    # ------------------------------------------------------
    # Generic fields for chemical requests
    # ------------------------------------------------------

    if source == "CHEMICAL":

        if not _clean(
            record.get(
                "Request Category",
                ""
            )
        ):
            record["Request Category"] = (
                "HERBICIDE"
            )

        if not _clean(
            record.get(
                "Item / Description",
                ""
            )
        ):
            record["Item / Description"] = (
                record.get(
                    "Chemical",
                    ""
                )
            )

        if not _clean(
            record.get(
                "Quantity",
                ""
            )
        ):
            record["Quantity"] = (
                record.get(
                    "Requested Quantity",
                    ""
                )
            )

    # ------------------------------------------------------
    # Approval permissions
    # ------------------------------------------------------

    requester = _clean(
        record.get(
            "Requester",
            ""
        )
    )

    current_user = _current_user()

    requester_is_current_user = (
        requester.lower()
        == current_user.lower()
        and requester != ""
        and current_user != ""
    )

    status = _normalise_status(
        record.get(
            "Status",
            ""
        )
    )

    can_review = (
        status == "PENDING"
        and not requester_is_current_user
    )

    # ------------------------------------------------------
    # History
    # ------------------------------------------------------

    history = get_agriculture_request_history(
        request_id
    )

    return render_template(
        "agriculture/agriculture_request_review.html",
        request_data=record,
        request_id=request_id,
        source=source,
        season=season,
        history=history,
        can_review=can_review,
        requester_is_current_user=(
            requester_is_current_user
        ),
        current_user=current_user,
        status=status
    )


# ==========================================================
# APPROVE AGRICULTURE REQUEST
# ==========================================================

@agriculture_requests_bp.route(
    "/agriculture/approval/<request_id>/approve",
    methods=["POST"]
)
def approve_request(
    request_id
):

    # ------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------

    if "username" not in session:
        return redirect(
            url_for("login")
        )

    # ------------------------------------------------------
    # ROLE
    # ------------------------------------------------------

    if not _is_approval_role():

        flash(
            "You are not authorised to approve "
            "Agriculture requests.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_approvals"
            )
        )

    # ------------------------------------------------------
    # Determine source
    # ------------------------------------------------------

    request_id = _clean(
        request_id
    )

    agriculture_df = (
        load_agriculture_requests()
    )

    index, row = find_agriculture_request(
        agriculture_df,
        request_id
    )

    # ------------------------------------------------------
    # General Agriculture request
    # ------------------------------------------------------

    if row is not None:

        season = get_active_season()

        if _clean(
            row.get("Season", "")
        ) != _clean(season):

            flash(
                "This request does not belong to "
                "the active season.",
                "danger"
            )

            return redirect(
                url_for(
                    "agriculture_requests.agriculture_approvals"
                )
            )

        success, message = (
            approve_agriculture_request(
                request_id
            )
        )

        flash(
            message,
            "success" if success else "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_request_review",
                request_id=request_id
            )
        )

    # ======================================================
    # CHEMICAL REQUEST
    # ======================================================

    chemical_df = load_chemical_requests()

    index, row = find_agriculture_request(
        chemical_df,
        request_id
    )

    if row is None:

        flash(
            "Agriculture request was not found.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_approvals"
            )
        )

    season = get_active_season()

    if _clean(
        row.get("Season", "")
    ) != _clean(season):

        flash(
            "This request does not belong to "
            "the active season.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_approvals"
            )
        )

    if not is_request_pending(row):

        flash(
            "Only PENDING requests can be approved.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_request_review",
                request_id=request_id
            )
        )

    if not can_user_approve_request(row):

        flash(
            "You cannot approve your own request.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_request_review",
                request_id=request_id
            )
        )

    # ------------------------------------------------------
    # Approve chemical request
    # ------------------------------------------------------

    approver = _current_user()

    chemical_df.at[
        index,
        "Status"
    ] = "APPROVED"

    chemical_df.at[
        index,
        "Approved By"
    ] = approver

    chemical_df.at[
        index,
        "Approval Date"
    ] = pd.Timestamp.now()

    chemical_df.at[
        index,
        "Rejection Reason"
    ] = ""

    _ensure_directory(
        CHEMICAL_REQUEST_FILE
    )

    chemical_df.to_excel(
        CHEMICAL_REQUEST_FILE,
        index=False,
        engine="openpyxl"
    )

    # ------------------------------------------------------
    # History
    # ------------------------------------------------------

    log_agriculture_request_event(
        request_id=request_id,
        event="APPROVED",
        user=approver,
        role=_current_role(),
        status="APPROVED",
        details=(
            "Chemical / Herbicide request approved."
        )
    )

    flash(
        "Chemical / Herbicide request approved successfully.",
        "success"
    )

    return redirect(
        url_for(
            "agriculture_requests.agriculture_request_review",
            request_id=request_id
        )
    )


# ==========================================================
# REJECT AGRICULTURE REQUEST
# ==========================================================

@agriculture_requests_bp.route(
    "/agriculture/approval/<request_id>/reject",
    methods=["POST"]
)
def reject_request(
    request_id
):

    # ------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------

    if "username" not in session:
        return redirect(
            url_for("login")
        )

    # ------------------------------------------------------
    # ROLE
    # ------------------------------------------------------

    if not _is_approval_role():

        flash(
            "You are not authorised to reject "
            "Agriculture requests.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_approvals"
            )
        )

    rejection_reason = _clean(
        request.form.get(
            "rejection_reason",
            ""
        )
    )

    if not rejection_reason:

        flash(
            "A rejection reason is required.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_request_review",
                request_id=request_id
            )
        )

    request_id = _clean(
        request_id
    )

    # ======================================================
    # GENERAL AGRICULTURE REQUEST
    # ======================================================

    agriculture_df = (
        load_agriculture_requests()
    )

    index, row = find_agriculture_request(
        agriculture_df,
        request_id
    )

    if row is not None:

        season = get_active_season()

        if _clean(
            row.get("Season", "")
        ) != _clean(season):

            flash(
                "This request does not belong to "
                "the active season.",
                "danger"
            )

            return redirect(
                url_for(
                    "agriculture_requests.agriculture_approvals"
                )
            )

        success, message = (
            reject_agriculture_request(
                request_id,
                rejection_reason
            )
        )

        flash(
            message,
            "warning" if success else "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_request_review",
                request_id=request_id
            )
        )

    # ======================================================
    # CHEMICAL REQUEST
    # ======================================================

    chemical_df = load_chemical_requests()

    index, row = find_agriculture_request(
        chemical_df,
        request_id
    )

    if row is None:

        flash(
            "Agriculture request was not found.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_approvals"
            )
        )

    season = get_active_season()

    if _clean(
        row.get("Season", "")
    ) != _clean(season):

        flash(
            "This request does not belong to "
            "the active season.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_approvals"
            )
        )

    if not is_request_pending(row):

        flash(
            "Only PENDING requests can be rejected.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_request_review",
                request_id=request_id
            )
        )

    if not can_user_approve_request(row):

        flash(
            "You cannot reject your own request.",
            "danger"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_request_review",
                request_id=request_id
            )
        )

    # ------------------------------------------------------
    # Reject chemical request
    # ------------------------------------------------------

    approver = _current_user()

    chemical_df.at[
        index,
        "Status"
    ] = "REJECTED"

    chemical_df.at[
        index,
        "Approved By"
    ] = approver

    chemical_df.at[
        index,
        "Approval Date"
    ] = pd.Timestamp.now()

    chemical_df.at[
        index,
        "Rejection Reason"
    ] = rejection_reason

    _ensure_directory(
        CHEMICAL_REQUEST_FILE
    )

    chemical_df.to_excel(
        CHEMICAL_REQUEST_FILE,
        index=False,
        engine="openpyxl"
    )

    # ------------------------------------------------------
    # History
    # ------------------------------------------------------

    log_agriculture_request_event(
        request_id=request_id,
        event="REJECTED",
        user=approver,
        role=_current_role(),
        status="REJECTED",
        details=(
            f"Chemical / Herbicide request rejected: "
            f"{rejection_reason}"
        )
    )

    flash(
        "Chemical / Herbicide request rejected.",
        "warning"
    )

    return redirect(
        url_for(
            "agriculture_requests.agriculture_request_review",
            request_id=request_id
        )
    )

# ==========================================================
# NEW GENERAL AGRICULTURE REQUEST
# ==========================================================

@agriculture_requests_bp.route(
    "/agriculture/request/new",
    methods=["GET", "POST"]
)
def new_agriculture_request():

    # ------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------

    if "username" not in session:
        return redirect(
            url_for("login")
        )

    season = get_active_season()

    current_user = _current_user()

    # ------------------------------------------------------
    # CREATE REQUEST
    # ------------------------------------------------------

    if request.method == "POST":

        request_type = _clean(
            request.form.get(
                "request_type",
                "OPERATIONAL"
            )
        ).upper()

        request_category = _clean(
            request.form.get(
                "request_category",
                "OTHER"
            )
        ).upper()

        department = _clean(
            request.form.get(
                "department",
                "Agriculture"
            )
        )

        item_description = _clean(
            request.form.get(
                "item_description",
                ""
            )
        )

        specification = _clean(
            request.form.get(
                "specification",
                ""
            )
        )

        quantity = _clean(
            request.form.get(
                "quantity",
                ""
            )
        )

        quantity_unit = _clean(
            request.form.get(
                "quantity_unit",
                ""
            )
        )

        field = _clean(
            request.form.get(
                "field",
                ""
            )
        )

        programme_id = _clean(
            request.form.get(
                "programme_id",
                ""
            )
        )

        required_date = _clean(
            request.form.get(
                "required_date",
                ""
            )
        )

        urgency = _clean(
            request.form.get(
                "urgency",
                "NORMAL"
            )
        ).upper()

        reason = _clean(
            request.form.get(
                "reason",
                ""
            )
        )

        notes = _clean(
            request.form.get(
                "notes",
                ""
            )
        )

        # --------------------------------------------------
        # VALIDATION
        # --------------------------------------------------

        errors = []

        if not request_category:
            errors.append(
                "Request category is required."
            )

        if not item_description:
            errors.append(
                "Item / Description is required."
            )

        if not quantity:
            errors.append(
                "Quantity is required."
            )

        if not quantity_unit:
            errors.append(
                "Quantity unit is required."
            )

        if not required_date:
            errors.append(
                "Required date is required."
            )

        if not reason:
            errors.append(
                "Reason is required."
            )

        if request_category not in (
            AGRICULTURE_REQUEST_CATEGORIES
        ):
            errors.append(
                "Invalid Agriculture request category."
            )

        if request_type not in (
            AGRICULTURE_REQUEST_TYPES
        ):
            errors.append(
                "Invalid request type."
            )

        if urgency not in (
            AGRICULTURE_REQUEST_URGENCY
        ):
            errors.append(
                "Invalid urgency level."
            )

        # --------------------------------------------------
        # STOP IF VALIDATION FAILED
        # --------------------------------------------------

        if errors:

            for error in errors:
                flash(
                    error,
                    "danger"
                )

            return render_template(
                "agriculture/agriculture_request_new.html",
                season=season,
                categories=AGRICULTURE_REQUEST_CATEGORIES,
                request_types=AGRICULTURE_REQUEST_TYPES,
                urgency_levels=AGRICULTURE_REQUEST_URGENCY,
                current_user=current_user,
                form=request.form
            )

        # --------------------------------------------------
        # CREATE REQUEST
        # --------------------------------------------------

        request_id = create_agriculture_request(
            request_type=request_type,
            request_category=request_category,
            department=department,
            requester=current_user,
            item_description=item_description,
            specification=specification,
            quantity=quantity,
            quantity_unit=quantity_unit,
            field=field,
            programme_id=programme_id,
            required_date=required_date,
            urgency=urgency,
            reason=reason,
            notes=notes
        )

        flash(
            f"Agriculture request {request_id} "
            f"was created successfully and is "
            f"pending approval.",
            "success"
        )

        return redirect(
            url_for(
                "agriculture_requests.agriculture_request_review",
                request_id=request_id
            )
        )

    # ------------------------------------------------------
    # GET
    # ------------------------------------------------------

    return render_template(
        "agriculture/agriculture_request_new.html",
        season=season,
        categories=AGRICULTURE_REQUEST_CATEGORIES,
        request_types=AGRICULTURE_REQUEST_TYPES,
        urgency_levels=AGRICULTURE_REQUEST_URGENCY,
        current_user=current_user,
        form={}
    )
