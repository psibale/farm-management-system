# ==========================================================
# DCGL FARM MANAGEMENT SYSTEM
# AUTOMATIC FERTILIZER PROGRAMME
# ==========================================================
#
# SEASON-AWARE + ESTATE-SPECIFIC VERSION
#
# Uses:
#   registered_fields.xlsx
#   planting_records.xlsx
#   harvesting_records.xlsx
#   fertilizer_records.xlsx
#
# Generates:
#   fertilizer_schedule.xlsx
#
#
# ==========================================================
# IMPORTANT AGRICULTURAL CALENDAR
# ==========================================================
#
# MAIN ESTATE
# ------------
# Field prefix:
#     DG
#
# Main Estate is IRRIGATED.
#
# Fertilizer programme follows the crop cycle:
#
#     Basal      = planting/cutting date
#     Top 1      = 28 days after basal
#     Top 2      = 28 days after Top 1
#
#
# LIWALADZI + KASITU
# -------------------
#
# Field prefixes:
#     L = Liwaladzi Estate
#     M = Kasitu Estate
#
# These estates are RAIN-FED.
#
# Fertilizer application starts from:
#
#     15 DECEMBER
#
# Therefore:
#
# If planting/cutting occurs BEFORE 15 December:
#
#     Base Date          = actual planting/cutting date
#     Planned Basal Date = 15 December
#
# If planting/cutting occurs ON/AFTER 15 December:
#
#     Base Date          = actual planting/cutting date
#     Planned Basal Date = actual planting/cutting date
#
# Then:
#
#     Top 1 = 28 days after basal
#     Top 2 = 28 days after Top 1 (IRRIGATED ONLY)
#
#
# ACTUAL APPLICATIONS
# -------------------
#
# If an actual basal application exists:
#
#     Main Estate:
#         actual basal date becomes the anchor.
#
#     Rain-fed:
#         only an actual basal application on/after
#         15 December is accepted as the programme
#         basal anchor.
#
# Actual top dressing applications are then used
# to determine the next programme stage.
#
#
# ==========================================================
# FERTILIZER RATES
# ==========================================================
#
FERTILIZER_RATES = {

    "IRRIGATED": {
        "PLANT": {
            "DAP": 5.0,
            "MOP": 2.0,
            "Zinc": 1.0,
            "UREA_TOP_1": 2.5,
            "SA_TOP_1": 2.0,
            "UREA_TOP_2": 2.5,
            "SA_TOP_2": 2.0,
        },
        "RATOON": {
            "DAP": 5.0,
            "MOP": 2.0,
            "UREA_TOP_1": 2.5,
            "SA_TOP_1": 2.0,
            "UREA_TOP_2": 2.5,
            "SA_TOP_2": 2.0,
        }
    },

    "RAIN-FED": {
        "PLANT": {
            "MOP": 1.0,
            "UREA_TOP_1": 3.0,
            "SA_TOP_1": 2.0,
        },
        "RATOON": {
            "MOP": 1.0,
            "UREA_TOP_1": 3.0,
            "SA_TOP_1": 2.0,
        }
    }
}
#
#
# ==========================================================
# AREA
# ==========================================================
#
# registered_fields.xlsx -> Hectares
#
# is the AUTHORITATIVE seasonal field area.
#
# ==========================================================


import os
import pandas as pd
from datetime import timedelta


# ==========================================================
# FILES
# ==========================================================

REGISTERED_FIELDS_FILE = "data/registered_fields.xlsx"

PLANTING_FILE = "data/planting_records.xlsx"

HARVESTING_FILE = "data/harvesting_records.xlsx"

FERTILIZER_FILE = "data/fertilizer_records.xlsx"

FERTILIZER_SCHEDULE_FILE = (
    "data/fertilizer_schedule.xlsx"
)


# ==========================================================
# FERTILIZER RATES
# ==========================================================

FERTILIZER_RATES = {

    "IRRIGATED": {
        "PLANT": {
            "DAP": 5.0,
            "MOP": 2.0,
            "Zinc": 1.0,
            "UREA_TOP_1": 2.5,
            "SA_TOP_1": 2.0,
            "UREA_TOP_2": 2.5,
            "SA_TOP_2": 2.0,
        },
        "RATOON": {
            "DAP": 5.0,
            "MOP": 2.0,
            "UREA_TOP_1": 2.5,
            "SA_TOP_1": 2.0,
            "UREA_TOP_2": 2.5,
            "SA_TOP_2": 2.0,
        }
    },

    "RAIN-FED": {
        "PLANT": {
            "MOP": 1.0,
            "UREA_TOP_1": 3.0,
            "SA_TOP_1": 2.0,
        },
        "RATOON": {
            "MOP": 1.0,
            "UREA_TOP_1": 3.0,
            "SA_TOP_1": 2.0,
        }
    }
}


# ==========================================================
# SEASON DATE RANGE
# ==========================================================

def get_season_dates(season):
    """
    Convert a DCGL season such as:

        2026/27

    into:

        Start = 2026-04-01
        End   = 2027-03-31

    DCGL agricultural season starts in April.
    """

    if not season:

        return None, None

    try:

        season_text = str(
            season
        ).strip()

        start_year = int(
            season_text.split("/")[0]
        )

        season_start = pd.Timestamp(
            year=start_year,
            month=4,
            day=1
        )

        season_end = pd.Timestamp(
            year=start_year + 1,
            month=3,
            day=31
        )

        return (
            season_start,
            season_end
        )

    except Exception as e:

        print(
            f"SEASON DATE ERROR: "
            f"{season} -> {e}"
        )

        return None, None


# ==========================================================
# RAIN-FED FERTILIZER START DATE
# ==========================================================

def get_rainfed_fertilizer_start_date(
    season
):
    """
    Return the fertilizer programme start date for
    rain-fed estates.

    Rain-fed fertilizer applications start from:

        15 December

    Example:

        2026/27
            -> 2026-12-15
    """

    season_start, season_end = (
        get_season_dates(
            season
        )
    )

    if season_start is None:

        return None

    return pd.Timestamp(
        year=season_start.year,
        month=12,
        day=15
    ).normalize()


# ==========================================================
# ESTATE CLASSIFICATION
# ==========================================================

def classify_estate(field):

    field = clean_field(
        field
    )

    if field.startswith("DG"):

        return "Main Estate"

    if field.startswith("L"):

        return "Liwaladzi Estate"

    if field.startswith("M"):

        return "Kasitu Estate"

    return "Other"


# ==========================================================
# FERTILIZER CALENDAR
# ==========================================================

def get_fertilizer_calendar(field):
    """
    Determine the fertilizer calendar for a field.

    Main Estate:
        IRRIGATED

    Liwaladzi Estate:
        RAIN-FED

    Kasitu Estate:
        RAIN-FED

    Unknown fields:
        IRRIGATED

    The unknown-field fallback preserves the previous
    programme behaviour while DG/L/M remain explicitly
    classified.
    """

    estate = classify_estate(
        field
    )

    if estate == "Main Estate":

        return "IRRIGATED"

    if estate in [
        "Liwaladzi Estate",
        "Kasitu Estate"
    ]:

        return "RAIN-FED"

    return "IRRIGATED"


# ==========================================================
# STATUS
# ==========================================================

def get_schedule_status(
    planned_date,
    actual_date=None
):
    """
    Determine the current status of an application.
    """

    if actual_date is not None:

        return "APPLIED"

    if planned_date is None:

        return "NO DATE"

    today = (
        pd.Timestamp
        .today()
        .normalize()
    )

    planned = pd.to_datetime(
        planned_date,
        errors="coerce"
    )

    if pd.isna(planned):

        return "NO DATE"

    planned = planned.normalize()

    days = (
        planned - today
    ).days

    if days < 0:

        return "OVERDUE"

    if days == 0:

        return "DUE TODAY"

    if days <= 7:

        return "DUE SOON"

    return "SCHEDULED"


# ==========================================================
# CLEAN FIELD
# ==========================================================

def clean_field(value):

    if pd.isna(value):

        return ""

    return str(
        value
    ).strip().upper()


# ==========================================================
# CLEAN SEASON
# ==========================================================

def clean_season(value):

    if pd.isna(value):

        return ""

    return str(
        value
    ).strip()


# ==========================================================
# LOAD EXCEL FILE SAFELY
# ==========================================================

def load_excel(path):

    if not os.path.exists(path):

        print(
            f"WARNING: File not found: {path}"
        )

        return pd.DataFrame()

    try:

        df = pd.read_excel(
            path
        )

        # ----------------------------------------------
        # CLEAN COLUMN NAMES
        # ----------------------------------------------

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        return df

    except Exception as e:

        print(
            f"WARNING: Could not load "
            f"{path}: {e}"
        )

        return pd.DataFrame()


# ==========================================================
# PREPARE EVENT DATAFRAME
# ==========================================================

def prepare_event_dataframe(df):
    """
    Clean Field and Date columns for planting,
    harvesting and fertilizer records.
    """

    if df.empty:

        return df

    temp = df.copy()

    if "Field" in temp.columns:

        temp["Field"] = (
            temp["Field"]
            .apply(clean_field)
        )

    if "Date" in temp.columns:

        temp["Date"] = pd.to_datetime(
            temp["Date"],
            errors="coerce"
        )

    return temp


# ==========================================================
# PREPARE REGISTERED FIELDS
# ==========================================================

def prepare_registered_fields(
    df,
    season
):
    """
    Prepare registered_fields.xlsx and filter it
    STRICTLY to the requested agricultural season.
    """

    if df.empty:

        return pd.DataFrame()

    temp = df.copy()

    # ------------------------------------------------------
    # CLEAN COLUMN NAMES
    # ------------------------------------------------------

    temp.columns = [
        str(column).strip()
        for column in temp.columns
    ]

    # ------------------------------------------------------
    # REQUIRED COLUMNS
    # ------------------------------------------------------

    required_columns = [
        "Field",
        "Hectares",
        "Season"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in temp.columns
    ]

    if missing_columns:

        print(
            "ERROR: registered_fields.xlsx "
            "is missing required columns: "
            f"{missing_columns}"
        )

        return pd.DataFrame()

    # ------------------------------------------------------
    # CLEAN FIELD
    # ------------------------------------------------------

    temp["Field"] = (
        temp["Field"]
        .apply(clean_field)
    )

    # ------------------------------------------------------
    # CLEAN SEASON
    # ------------------------------------------------------

    temp["Season"] = (
        temp["Season"]
        .apply(clean_season)
    )

    season = clean_season(
        season
    )

    # ------------------------------------------------------
    # STRICT SEASON FILTER
    # ------------------------------------------------------

    temp = temp[
        temp["Season"] == season
    ].copy()

    if temp.empty:

        print(
            "WARNING: No registered fields found "
            f"for season {season}."
        )

        return pd.DataFrame()

    # ------------------------------------------------------
    # CLEAN AREA
    # ------------------------------------------------------

    temp["Hectares"] = pd.to_numeric(
        temp["Hectares"],
        errors="coerce"
    )

    # ------------------------------------------------------
    # REMOVE INVALID FIELDS
    # ------------------------------------------------------

    temp = temp[
        temp["Field"] != ""
    ].copy()

    # ------------------------------------------------------
    # REMOVE INVALID AREAS
    # ------------------------------------------------------

    temp = temp[
        temp["Hectares"].notna()
        &
        (temp["Hectares"] > 0)
    ].copy()

    # ------------------------------------------------------
    # NORMALISE AREA
    # ------------------------------------------------------

    temp["Hectares"] = (
        temp["Hectares"]
        .astype(float)
    )

    # ------------------------------------------------------
    # DUPLICATE PROTECTION
    # ------------------------------------------------------

    duplicate_mask = (
        temp["Field"]
        .duplicated(
            keep=False
        )
    )

    duplicate_count = int(
        duplicate_mask.sum()
    )

    if duplicate_count > 0:

        duplicate_fields = sorted(
            temp.loc[
                duplicate_mask,
                "Field"
            ]
            .unique()
            .tolist()
        )

        print(
            "WARNING: Duplicate registered field "
            f"records found for {season}: "
            f"{duplicate_fields}"
        )

        temp = (
            temp
            .drop_duplicates(
                subset=["Field"],
                keep="last"
            )
            .copy()
        )

    # ------------------------------------------------------
    # RESET INDEX
    # ------------------------------------------------------

    temp = (
        temp
        .reset_index(
            drop=True
        )
    )

    print(
        f"Registered fields for {season}: "
        f"{len(temp)}"
    )

    print(
        f"Registered area for {season}: "
        f"{temp['Hectares'].sum():,.3f} ha"
    )

    return temp


# ==========================================================
# GET EVENTS FOR CURRENT SEASON
# ==========================================================

def get_season_events(
    df,
    field,
    season_start,
    season_end
):
    """
    Return records for a specific field that occurred
    inside the active season.
    """

    if df.empty:

        return pd.DataFrame()

    if "Field" not in df.columns:

        return pd.DataFrame()

    if "Date" not in df.columns:

        return pd.DataFrame()

    temp = df.copy()

    temp["Field"] = (
        temp["Field"]
        .apply(clean_field)
    )

    temp["Date"] = pd.to_datetime(
        temp["Date"],
        errors="coerce"
    )

    temp = temp.dropna(
        subset=["Date"]
    )

    field_clean = clean_field(
        field
    )

    temp = temp[
        temp["Field"] == field_clean
    ]

    temp = temp[
        (temp["Date"] >= season_start)
        &
        (temp["Date"] <= season_end)
    ]

    return temp.copy()


# ==========================================================
# GET CURRENT CROP CYCLE EVENT
# ==========================================================

def get_current_cycle_event(
    field,
    season_start,
    season_end,
    planting_df,
    harvesting_df
):
    """
    Find the planting/cutting event belonging to
    the ACTIVE season.

    Current-season cutting takes priority.

        Harvest/Cutting -> RATOON
        Planting        -> PLANT
        No event        -> None
    """

    # ------------------------------------------------------
    # CURRENT-SEASON HARVEST / CUTTING
    # ------------------------------------------------------

    harvest_events = get_season_events(
        harvesting_df,
        field,
        season_start,
        season_end
    )

    # ------------------------------------------------------
    # CURRENT-SEASON PLANTING
    # ------------------------------------------------------

    planting_events = get_season_events(
        planting_df,
        field,
        season_start,
        season_end
    )

    # ------------------------------------------------------
    # RATOON
    # ------------------------------------------------------

    if not harvest_events.empty:

        event = (
            harvest_events
            .sort_values("Date")
            .iloc[-1]
        )

        return {

            "crop_type":
                "RATOON",

            "base_date":
                pd.Timestamp(
                    event["Date"]
                ).normalize(),

            "event_type":
                "CUTTING"
        }

    # ------------------------------------------------------
    # PLANT CANE
    # ------------------------------------------------------

    if not planting_events.empty:

        event = (
            planting_events
            .sort_values("Date")
            .iloc[-1]
        )

        return {

            "crop_type":
                "PLANT",

            "base_date":
                pd.Timestamp(
                    event["Date"]
                ).normalize(),

            "event_type":
                "PLANTING"
        }

    return None


# ==========================================================
# GET LATEST EVENT DATE
# ==========================================================

def latest_event_date(
    df,
    field,
    before_or_equal=None
):

    if df.empty:

        return None

    if "Field" not in df.columns:

        return None

    temp = df.copy()

    temp["Field"] = (
        temp["Field"]
        .apply(clean_field)
    )

    temp = temp[
        temp["Field"]
        == clean_field(field)
    ]

    if temp.empty:

        return None

    if "Date" not in temp.columns:

        return None

    temp["Date"] = pd.to_datetime(
        temp["Date"],
        errors="coerce"
    )

    temp = temp.dropna(
        subset=["Date"]
    )

    if before_or_equal is not None:

        temp = temp[
            temp["Date"]
            <= pd.to_datetime(
                before_or_equal
            )
        ]

    if temp.empty:

        return None

    return temp["Date"].max()


# ==========================================================
# DETERMINE CROP TYPE
# ==========================================================

def determine_crop_type(
    field,
    planting_df,
    harvesting_df
):
    """
    Legacy/general crop determination.

    The season-aware generator uses
    get_current_cycle_event().
    """

    planting_date = latest_event_date(
        planting_df,
        field
    )

    harvest_date = latest_event_date(
        harvesting_df,
        field
    )

    if harvest_date is not None:

        if (
            planting_date is None
            or harvest_date > planting_date
        ):

            return (
                "RATOON",
                harvest_date
            )

    return (
        "PLANT",
        planting_date
    )


# ==========================================================
# FIND ACTUAL BASAL APPLICATION
# ==========================================================

def find_actual_basal_date(
    field,
    base_date,
    fertilizer_df,
    season_start=None,
    season_end=None,
    minimum_application_date=None
):
    """
    Find the first actual DAP/MOP/Zinc application
    after the current crop-cycle planting/cutting date.

    For rain-fed estates, an optional minimum application
    date can be supplied.

    Example:

        Rain-fed minimum = 15-Dec-2026

    Any basal application before that date is ignored
    for programme scheduling.
    """

    if fertilizer_df.empty:

        return None

    required_columns = {
        "Field",
        "Date"
    }

    if not required_columns.issubset(
        fertilizer_df.columns
    ):

        return None

    temp = fertilizer_df.copy()

    temp["Field"] = (
        temp["Field"]
        .apply(clean_field)
    )

    temp["Date"] = pd.to_datetime(
        temp["Date"],
        errors="coerce"
    )

    temp = temp.dropna(
        subset=["Date"]
    )

    temp = temp[
        temp["Field"]
        == clean_field(field)
    ]

    if temp.empty:

        return None

    # ------------------------------------------------------
    # CURRENT SEASON ONLY
    # ------------------------------------------------------

    if season_start is not None:

        temp = temp[
            temp["Date"]
            >= pd.to_datetime(
                season_start
            )
        ]

    if season_end is not None:

        temp = temp[
            temp["Date"]
            <= pd.to_datetime(
                season_end
            )
        ]

    # ------------------------------------------------------
    # AFTER CURRENT CROP CYCLE START
    # ------------------------------------------------------

    if base_date is not None:

        temp = temp[
            temp["Date"]
            >= pd.to_datetime(
                base_date
            )
        ]

    # ------------------------------------------------------
    # RAIN-FED MINIMUM APPLICATION DATE
    # ------------------------------------------------------

    if minimum_application_date is not None:

        temp = temp[
            temp["Date"]
            >= pd.to_datetime(
                minimum_application_date
            )
        ]

    if temp.empty:

        return None

    # ------------------------------------------------------
    # BASAL FERTILIZERS
    # ------------------------------------------------------

    fertilizer_columns = [
        col
        for col in [
            "DAP",
            "MOP",
            "Zinc"
        ]
        if col in temp.columns
    ]

    if not fertilizer_columns:

        return None

    for col in fertilizer_columns:

        temp[col] = pd.to_numeric(
            temp[col],
            errors="coerce"
        ).fillna(0)

    basal = temp[
        temp[
            fertilizer_columns
        ]
        .sum(axis=1)
        > 0
    ]

    if basal.empty:

        return None

    return (
        basal["Date"]
        .min()
        .normalize()
    )


# ==========================================================
# FIND ACTUAL APPLICATION DATES FOR ONE FERTILIZER
# ==========================================================

def find_actual_fertilizer_dates(
    field,
    fertilizer,
    after_date,
    fertilizer_df,
    season_start=None,
    season_end=None,
    minimum_application_date=None
):
    """
    Find actual application dates for ONE specific fertilizer.

    Examples:

        fertilizer = "DAP"
        fertilizer = "MOP"
        fertilizer = "Zinc"
        fertilizer = "UREA"
        fertilizer = "SA"

    An application is considered actual only when the
    corresponding fertilizer column contains a quantity
    greater than zero.

    This prevents DAP application from incorrectly marking
    MOP or Zinc as applied.
    """

    if fertilizer_df.empty:

        return []

    # ------------------------------------------------------
    # REQUIRED COLUMNS
    # ------------------------------------------------------

    if not {
        "Field",
        "Date"
    }.issubset(
        fertilizer_df.columns
    ):

        return []

    if fertilizer not in fertilizer_df.columns:

        return []

    temp = fertilizer_df.copy()

    # ------------------------------------------------------
    # CLEAN FIELD
    # ------------------------------------------------------

    temp["Field"] = (
        temp["Field"]
        .apply(clean_field)
    )

    # ------------------------------------------------------
    # CLEAN DATE
    # ------------------------------------------------------

    temp["Date"] = pd.to_datetime(
        temp["Date"],
        errors="coerce"
    )

    temp = temp.dropna(
        subset=["Date"]
    )

    # ------------------------------------------------------
    # FIELD FILTER
    # ------------------------------------------------------

    temp = temp[
        temp["Field"]
        == clean_field(field)
    ]

    if temp.empty:

        return []

    # ------------------------------------------------------
    # CURRENT SEASON ONLY
    # ------------------------------------------------------

    if season_start is not None:

        temp = temp[
            temp["Date"]
            >= pd.to_datetime(
                season_start
            )
        ]

    if season_end is not None:

        temp = temp[
            temp["Date"]
            <= pd.to_datetime(
                season_end
            )
        ]

    # ------------------------------------------------------
    # AFTER CROP CYCLE / BASAL ANCHOR
    # ------------------------------------------------------

    if after_date is not None:

        temp = temp[
            temp["Date"]
            >= pd.to_datetime(
                after_date
            )
        ]

    # ------------------------------------------------------
    # RAIN-FED MINIMUM DATE
    # ------------------------------------------------------

    if minimum_application_date is not None:

        temp = temp[
            temp["Date"]
            >= pd.to_datetime(
                minimum_application_date
            )
        ]

    if temp.empty:

        return []

    # ------------------------------------------------------
    # CONVERT FERTILIZER QUANTITY
    # ------------------------------------------------------

    temp[fertilizer] = pd.to_numeric(
        temp[fertilizer],
        errors="coerce"
    ).fillna(0)

    # ------------------------------------------------------
    # ONLY ACTUAL APPLICATIONS
    # ------------------------------------------------------
    #
    # IMPORTANT:
    #
    # > 0 means fertilizer was actually applied.
    #
    # Blank / NaN / 0 means NOT applied.
    #
    # ------------------------------------------------------

    actual = temp[
        temp[fertilizer] > 0
    ].copy()

    if actual.empty:

        return []

    # ------------------------------------------------------
    # UNIQUE APPLICATION DATES
    # ------------------------------------------------------

    dates = (
        actual["Date"]
        .dt.normalize()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    return dates

# ==========================================================
# GET FIRST AND SECOND APPLICATION FOR ONE FERTILIZER
# ==========================================================

def get_fertilizer_application_stages(
    field,
    fertilizer,
    after_date,
    fertilizer_df,
    season_start=None,
    season_end=None,
    minimum_application_date=None
):
    """
    Return the first and second actual application dates
    for one specific fertilizer.

    Returns:

        {
            "first":  first application date or None,
            "second": second application date or None
        }
    """

    dates = find_actual_fertilizer_dates(
        field,
        fertilizer,
        after_date,
        fertilizer_df,
        season_start,
        season_end,
        minimum_application_date
    )

    return {

        "first":
            dates[0]
            if len(dates) >= 1
            else None,

        "second":
            dates[1]
            if len(dates) >= 2
            else None
    }

# ==========================================================
# FIND ACTUAL TOP DRESSING APPLICATIONS
# ==========================================================

def find_actual_top_dates(
    field,
    after_date,
    fertilizer_df,
    season_start=None,
    season_end=None
):
    """
    Find actual UREA/SA application dates after
    the current basal application.

    First date:
        Top Dressing 1

    Second date:
        Top Dressing 2
    """

    if fertilizer_df.empty:

        return []

    required_columns = {
        "Field",
        "Date"
    }

    if not required_columns.issubset(
        fertilizer_df.columns
    ):

        return []

    temp = fertilizer_df.copy()

    temp["Field"] = (
        temp["Field"]
        .apply(clean_field)
    )

    temp["Date"] = pd.to_datetime(
        temp["Date"],
        errors="coerce"
    )

    temp = temp.dropna(
        subset=["Date"]
    )

    temp = temp[
        temp["Field"]
        == clean_field(field)
    ]

    if temp.empty:

        return []

    # ------------------------------------------------------
    # CURRENT SEASON ONLY
    # ------------------------------------------------------

    if season_start is not None:

        temp = temp[
            temp["Date"]
            >= pd.to_datetime(
                season_start
            )
        ]

    if season_end is not None:

        temp = temp[
            temp["Date"]
            <= pd.to_datetime(
                season_end
            )
        ]

    # ------------------------------------------------------
    # AFTER BASAL
    # ------------------------------------------------------

    if after_date is not None:

        temp = temp[
            temp["Date"]
            >= pd.to_datetime(
                after_date
            )
        ]

    if temp.empty:

        return []

    fertilizer_columns = [
        col
        for col in [
            "UREA",
            "SA"
        ]
        if col in temp.columns
    ]

    if not fertilizer_columns:

        return []

    for col in fertilizer_columns:

        temp[col] = pd.to_numeric(
            temp[col],
            errors="coerce"
        ).fillna(0)

    top_records = temp[
        temp[
            fertilizer_columns
        ]
        .sum(axis=1)
        > 0
    ]

    if top_records.empty:

        return []

    dates = (
        top_records["Date"]
        .dt.normalize()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    return dates


# ==========================================================
# GENERATE PROGRAMME
# ==========================================================

def generate_fertilizer_programme(
    season=None
):
    """
    Generate the season-aware automatic fertilizer
    programme.

    Estate calendars:

        Main Estate
            -> IRRIGATED
            -> follows actual crop-cycle date

        Liwaladzi Estate
            -> RAIN-FED
            -> fertilizer starts 15 December

        Kasitu Estate
            -> RAIN-FED
            -> fertilizer starts 15 December
    """

    print(
        "=================================================="
    )

    print(
        "GENERATING SEASON-AWARE "
        "AUTOMATIC FERTILIZER PROGRAMME"
    )

    print(
        "=================================================="
    )

    # ======================================================
    # GET ACTIVE SEASON
    # ======================================================

    if season is None:

        from modules.season import (
            get_active_season
        )

        season = get_active_season()

    if not season:

        print(
            "ERROR: No active season found."
        )

        return pd.DataFrame()

    season = clean_season(
        season
    )

    # ======================================================
    # CALCULATE SEASON DATES
    # ======================================================

    season_start, season_end = (
        get_season_dates(
            season
        )
    )

    if (
        season_start is None
        or season_end is None
    ):

        print(
            f"ERROR: Invalid season: {season}"
        )

        return pd.DataFrame()

    # ======================================================
    # RAIN-FED START DATE
    # ======================================================

    rainfed_start_date = (
        get_rainfed_fertilizer_start_date(
            season
        )
    )

    print(
        f"ACTIVE SEASON : {season}"
    )

    print(
        f"SEASON START  : "
        f"{season_start.strftime('%Y-%m-%d')}"
    )

    print(
        f"SEASON END    : "
        f"{season_end.strftime('%Y-%m-%d')}"
    )

    print(
        f"RAIN-FED START: "
        f"{rainfed_start_date.strftime('%Y-%m-%d')}"
    )

    # ======================================================
    # LOAD DATA
    # ======================================================

    registered_df = load_excel(
        REGISTERED_FIELDS_FILE
    )

    planting_df = load_excel(
        PLANTING_FILE
    )

    harvesting_df = load_excel(
        HARVESTING_FILE
    )

    fertilizer_df = load_excel(
        FERTILIZER_FILE
    )

    if registered_df.empty:

        print(
            "WARNING: No registered fields found."
        )

        return pd.DataFrame()

    # ======================================================
    # PREPARE REGISTERED FIELDS
    # ======================================================

    registered_df = (
        prepare_registered_fields(
            registered_df,
            season
        )
    )

    if registered_df.empty:

        print(
            "WARNING: No valid registered fields "
            f"for active season {season}."
        )

        return pd.DataFrame()

    # ======================================================
    # PREPARE EVENT DATA
    # ======================================================

    planting_df = (
        prepare_event_dataframe(
            planting_df
        )
    )

    harvesting_df = (
        prepare_event_dataframe(
            harvesting_df
        )
    )

    fertilizer_df = (
        prepare_event_dataframe(
            fertilizer_df
        )
    )

    # ======================================================
    # PROCESS FIELDS
    # ======================================================

    print(
        "Checking seasonal registered fields "
        "against actual planting/cutting events..."
    )

    programme = []

    fields_checked = 0

    fields_included = 0

    fields_excluded = 0

    # ======================================================
    # PROCESS EACH SEASONAL REGISTERED FIELD
    # ======================================================

    for _, field_record in (
        registered_df.iterrows()
    ):

        fields_checked += 1

        field = clean_field(
            field_record.get(
                "Field"
            )
        )

        if not field:

            continue

        # ==================================================
        # FIND CURRENT-SEASON CROP CYCLE
        # ==================================================

        cycle = (
            get_current_cycle_event(
                field,
                season_start,
                season_end,
                planting_df,
                harvesting_df
            )
        )

        # ==================================================
        # NO CURRENT-SEASON EVENT
        # ==================================================

        if cycle is None:

            fields_excluded += 1

            print(
                f"SKIPPED {field}: "
                f"registered for {season}, "
                f"but no planting/cutting event "
                f"inside {season}"
            )

            continue

        fields_included += 1

        # ==================================================
        # CURRENT CROP TYPE
        # ==================================================

        crop_type = cycle[
            "crop_type"
        ]

        base_date = cycle[
            "base_date"
        ]

        event_type = cycle[
            "event_type"
        ]

        # ==================================================
        # FIELD AREA
        # ==================================================

        area = pd.to_numeric(
            field_record.get(
                "Hectares"
            ),
            errors="coerce"
        )

        if pd.isna(area):

            print(
                f"SKIPPED {field}: "
                f"invalid Hectares value"
            )

            continue

        area = float(
            area
        )

        if area <= 0:

            print(
                f"SKIPPED {field}: "
                f"invalid Hectares value"
            )

            continue

        # ==================================================
        # FIELD INFORMATION
        # ==================================================

        main_field = field_record.get(
            "Main Field",
            ""
        )

        crop_name = field_record.get(
            "Crop Name",
            "Sugarcane"
        )

        location = field_record.get(
            "Location",
            ""
        )

        soil_type = field_record.get(
            "Soil Type",
            ""
        )

        field_season = season

        # ==================================================
        # NORMALISE BASE DATE
        # ==================================================

        base_date = pd.to_datetime(
            base_date
        ).normalize()

        # ==================================================
        # ESTATE / CALENDAR
        # ==================================================

        estate = classify_estate(
            field
        )

        fertilizer_calendar = (
            get_fertilizer_calendar(
                field
            )
        )

        # ==================================================
        # DETERMINE MINIMUM FERTILIZER DATE
        # ==================================================
        #
        # Main Estate:
        #
        #     fertilizer can start from crop-cycle date.
        #
        # Rain-fed:
        #
        #     fertilizer starts 15 December.
        #
        # ==================================================

        if fertilizer_calendar == "RAIN-FED":

            minimum_fertilizer_date = (
                rainfed_start_date
            )

        else:

            minimum_fertilizer_date = (
                base_date
            )

        # ==================================================
        # PLANNED BASAL DATE BEFORE ACTUAL APPLICATION
        # ==================================================

        planned_baseline_basal_date = max(
            base_date,
            minimum_fertilizer_date
        )

        print(
            f"INCLUDED {field}: "
            f"{crop_type} | "
            f"{event_type} | "
            f"{estate} | "
            f"{fertilizer_calendar} | "
            f"Base {base_date.strftime('%Y-%m-%d')} | "
            f"Basal from "
            f"{planned_baseline_basal_date.strftime('%Y-%m-%d')} | "
            f"{area:.3f} ha | "
            f"{season}"
        )

        # ==================================================
        # FIND ACTUAL BASAL APPLICATION
        # ==================================================
        #
        # For rain-fed fields:
        #
        #     actual basal before 15 December is NOT used
        #     as the programme anchor.
        #
        # ==================================================

        actual_basal_date = (
            find_actual_basal_date(
                field,
                base_date,
                fertilizer_df,
                season_start,
                season_end,
                minimum_application_date=(
                    minimum_fertilizer_date
                )
            )
        )

        # ==================================================
        # FIND ACTUAL BASAL DATE FOR EACH FERTILIZER
        # ==================================================

        actual_dap_dates = find_actual_fertilizer_dates(
            field,
            "DAP",
            base_date,
            fertilizer_df,
            season_start,
            season_end,
            minimum_application_date=minimum_fertilizer_date
        )

        actual_mop_dates = find_actual_fertilizer_dates(
            field,
            "MOP",
            base_date,
            fertilizer_df,
            season_start,
            season_end,
            minimum_application_date=minimum_fertilizer_date
        )

        actual_zinc_dates = find_actual_fertilizer_dates(
            field,
            "Zinc",
            base_date,
            fertilizer_df,
            season_start,
            season_end,
            minimum_application_date=minimum_fertilizer_date
        )

        actual_dap_date = (
            actual_dap_dates[0]
            if actual_dap_dates
            else None
        )

        actual_mop_date = (
            actual_mop_dates[0]
            if actual_mop_dates
            else None
        )

        actual_zinc_date = (
            actual_zinc_dates[0]
            if actual_zinc_dates
            else None
        )

        # ==================================================
        # PLANNED BASAL DATE
        # ==================================================

        planned_basal_date = (
            actual_basal_date
            if actual_basal_date is not None
            else planned_baseline_basal_date
        )

        planned_basal_date = pd.to_datetime(
            planned_basal_date
        ).normalize()

        # ==================================================
        # TOP DRESSING 1
        # ==================================================

        planned_top_1 = (
            planned_basal_date
            + timedelta(
                days=28
            )
        )

        # ==================================================
        # FIND ACTUAL TOP DRESSING APPLICATIONS
        # ==================================================
        #
        # IMPORTANT:
        # Actual applications are now tracked separately for:
        #
        #     UREA
        #     SA
        #
        # This prevents one fertilizer from incorrectly marking
        # the other fertilizer as applied.
        # ==================================================

        # --------------------------------------------------
        # UREA APPLICATION DATES
        # --------------------------------------------------

        urea_application_dates = (
            find_actual_fertilizer_dates(
                field,
                "UREA",
                planned_basal_date,
                fertilizer_df,
                season_start,
                season_end
            )
        )

        # --------------------------------------------------
        # SA APPLICATION DATES
        # --------------------------------------------------

        sa_application_dates = (
            find_actual_fertilizer_dates(
                field,
                "SA",
                planned_basal_date,
                fertilizer_df,
                season_start,
                season_end
            )
        )

        # ==================================================
        # ACTUAL UREA TOP DRESSING DATES
        # ==================================================

        actual_urea_top_1 = (
            urea_application_dates[0]
            if len(urea_application_dates) >= 1
            else None
        )

        actual_urea_top_2 = (
            urea_application_dates[1]
            if len(urea_application_dates) >= 2
            else None
        )

        # ==================================================
        # ACTUAL SA TOP DRESSING DATES
        # ==================================================

        actual_sa_top_1 = (
            sa_application_dates[0]
            if len(sa_application_dates) >= 1
            else None
        )

        actual_sa_top_2 = (
            sa_application_dates[1]
            if len(sa_application_dates) >= 2
            else None
        )

        # ==================================================
        # OVERALL ACTUAL TOP 1
        # ==================================================
        #
        # This is used only as the programme anchor for
        # calculating the next planned stage.
        #
        # It does NOT determine the Actual Date shown
        # against individual fertilizers.
        # ==================================================

        top_1_actual_candidates = [

            date

            for date in [

                actual_urea_top_1,

                actual_sa_top_1

            ]

            if date is not None
        ]

        actual_top_1 = (

            min(
                top_1_actual_candidates
            )

            if top_1_actual_candidates

            else None
        )

        # ==================================================
        # TOP 2
        # ==================================================

        top_2_base = (

            actual_top_1

            if actual_top_1 is not None

            else planned_top_1
        )

        planned_top_2 = (

                pd.to_datetime(
                    top_2_base
                )

                + timedelta(
            days=28
        )
        )

        # ==================================================
        # OVERALL ACTUAL TOP 2
        # ==================================================
        #
        # Used as the overall programme stage indicator.
        # Individual fertilizer rows use their own actual
        # application dates below.
        # ==================================================

        top_2_actual_candidates = [

            date

            for date in [

                actual_urea_top_2,

                actual_sa_top_2

            ]

            if date is not None
        ]

        actual_top_2 = (

            min(
                top_2_actual_candidates
            )

            if top_2_actual_candidates

            else None
        )

        # ==================================================
        # FERTILIZER RATES
        # ==================================================

        rates = FERTILIZER_RATES[
            fertilizer_calendar
        ][
            crop_type
        ]

        # ==================================================
        # BASAL FERTILIZERS
        # ==================================================

        if fertilizer_calendar == "RAIN-FED":

            # Rain-fed estates use MOP only as basal fertilizer.
            # DAP and Zinc are not applied.
            basal_fertilizers = [
                (
                    "MOP",
                    rates["MOP"]
                )
            ]

        else:

            # Irrigated Main Estate retains the existing programme.
            basal_fertilizers = [
                (
                    "DAP",
                    rates["DAP"]
                ),
                (
                    "MOP",
                    rates["MOP"]
                )
            ]

            # Zinc is only used for plant cane on the irrigated calendar.
            if crop_type == "PLANT":
                basal_fertilizers.append(
                    (
                        "Zinc",
                        rates["Zinc"]
                    )
                )

        # ==================================================
        # CREATE BASAL RECORDS
        # ==================================================

        for fertilizer, rate in (
                basal_fertilizers
        ):

            quantity = (
                    area * rate
            )

            # ==================================================
            # ACTUAL APPLICATION FOR THIS SPECIFIC FERTILIZER
            # ==================================================
            #
            # DAP is checked against DAP column.
            # MOP is checked against MOP column.
            # Zinc is checked against Zinc column.
            #
            # Therefore:
            #
            # DAP applied does NOT mean MOP applied.
            # ==================================================

            if fertilizer == "DAP":

                actual_fertilizer_date = (
                    actual_dap_date
                )

            elif fertilizer == "MOP":

                actual_fertilizer_date = (
                    actual_mop_date
                )

            elif fertilizer == "Zinc":

                actual_fertilizer_date = (
                    actual_zinc_date
                )

            else:

                actual_fertilizer_date = None

            programme.append({

                "Season":
                    field_season,

                "Estate":
                    estate,

                "Fertilizer Calendar":
                    fertilizer_calendar,

                "Main Field":
                    main_field,

                "Field":
                    field,

                "Area (Ha)":
                    round(
                        area,
                        3
                    ),

                "Crop":
                    crop_name,

                "Crop Type":
                    crop_type,

                "Base Date":
                    base_date,

                "Operation":
                    "Basal Dressing",

                "Fertilizer":
                    fertilizer,

                "Rate (bags/Ha)":
                    rate,

                "Planned Quantity (bags)":
                    round(
                        quantity,
                        3
                    ),

                "Planned Date":
                    planned_basal_date,

                "Actual Date":
                    actual_fertilizer_date,

                "Status":
                    get_schedule_status(
                        planned_basal_date,
                        actual_fertilizer_date
                    ),

                "Location":
                    location,

                "Soil Type":
                    soil_type,

                "Notes":
                    (
                            "Basal dressing. "

                            + (

                                "Rain-fed calendar: "
                                "fertilizer application starts "
                                "15 December."

                                if fertilizer_calendar
                                   == "RAIN-FED"

                                else

                                "Irrigated calendar: "
                                "basal dressing follows "
                                "planting/cutting."
                            )
                    )
            })

        # ==================================================
        # TOP DRESSING 1
        # ==================================================

        top_1_fertilizers = [

            (
                "UREA",
                rates["UREA_TOP_1"]
            ),

            (
                "SA",
                rates["SA_TOP_1"]
            )
        ]

        for fertilizer, rate in (
                top_1_fertilizers
        ):

            quantity = (
                    area * rate
            )

            # ==================================================
            # ACTUAL DATE FOR THIS SPECIFIC FERTILIZER
            # ==================================================

            if fertilizer == "UREA":

                actual_fertilizer_date = (
                    actual_urea_top_1
                )

            elif fertilizer == "SA":

                actual_fertilizer_date = (
                    actual_sa_top_1
                )

            else:

                actual_fertilizer_date = None

            programme.append({

                "Season":
                    field_season,

                "Estate":
                    estate,

                "Fertilizer Calendar":
                    fertilizer_calendar,

                "Main Field":
                    main_field,

                "Field":
                    field,

                "Area (Ha)":
                    round(
                        area,
                        3
                    ),

                "Crop":
                    crop_name,

                "Crop Type":
                    crop_type,

                "Base Date":
                    base_date,

                "Operation":
                    "Top Dressing 1",

                "Fertilizer":
                    fertilizer,

                "Rate (bags/Ha)":
                    rate,

                "Planned Quantity (bags)":
                    round(
                        quantity,
                        3
                    ),

                "Planned Date":
                    planned_top_1,

                "Actual Date":
                    actual_fertilizer_date,

                "Status":
                    get_schedule_status(
                        planned_top_1,
                        actual_fertilizer_date
                    ),

                "Location":
                    location,

                "Soil Type":
                    soil_type,

                "Notes":
                    (
                        "First top dressing, "
                        "28 days after basal."
                    )
            })

        # ==================================================
        # TOP DRESSING 2
        # ==================================================
        #
        # Rain-fed estates do NOT receive a second top dressing.
        # Irrigated Main Estate retains the existing second top dressing.
        # ==================================================

        if fertilizer_calendar != "RAIN-FED":


                    top_2_fertilizers = [

                        (
                            "UREA",
                            rates["UREA_TOP_2"]
                        ),

                        (
                            "SA",
                            rates["SA_TOP_2"]
                        )
                    ]

                    for fertilizer, rate in (
                            top_2_fertilizers
                    ):

                        quantity = (
                                area * rate
                        )

                        # ==================================================
                        # ACTUAL DATE FOR THIS SPECIFIC FERTILIZER
                        # ==================================================

                        if fertilizer == "UREA":

                            actual_fertilizer_date = (
                                actual_urea_top_2
                            )

                        elif fertilizer == "SA":

                            actual_fertilizer_date = (
                                actual_sa_top_2
                            )

                        else:

                            actual_fertilizer_date = None

                        programme.append({

                            "Season":
                                field_season,

                            "Estate":
                                estate,

                            "Fertilizer Calendar":
                                fertilizer_calendar,

                            "Main Field":
                                main_field,

                            "Field":
                                field,

                            "Area (Ha)":
                                round(
                                    area,
                                    3
                                ),

                            "Crop":
                                crop_name,

                            "Crop Type":
                                crop_type,

                            "Base Date":
                                base_date,

                            "Operation":
                                "Top Dressing 2",

                            "Fertilizer":
                                fertilizer,

                            "Rate (bags/Ha)":
                                rate,

                            "Planned Quantity (bags)":
                                round(
                                    quantity,
                                    3
                                ),

                            "Planned Date":
                                planned_top_2,

                            "Actual Date":
                                actual_fertilizer_date,

                            "Status":
                                get_schedule_status(
                                    planned_top_2,
                                    actual_fertilizer_date
                                ),

                            "Location":
                                location,

                            "Soil Type":
                                soil_type,

                            "Notes":
                                (
                                    "Second top dressing, "
                                    "28 days after first "
                                    "top dressing."
                                )
                        })

                # ======================================================
                # CREATE DATAFRAME
                # ======================================================

    result = pd.DataFrame(
        programme
    )

    if result.empty:

        print(
            "No fertilizer programme generated "
            f"for season {season}."
        )

        return result

    # ======================================================
    # DATE FORMATTING
    # ======================================================

    for column in [
        "Base Date",
        "Planned Date",
        "Actual Date"
    ]:

        if column in result.columns:

            result[column] = pd.to_datetime(
                result[column],
                errors="coerce"
            ).dt.strftime(
                "%Y-%m-%d"
            )

    # ======================================================
    # SORT
    # ======================================================

    status_order = {

        "OVERDUE": 0,

        "DUE TODAY": 1,

        "DUE SOON": 2,

        "SCHEDULED": 3,

        "APPLIED": 4,

        "NO DATE": 5
    }

    result["_status_order"] = (
        result["Status"]
        .map(
            status_order
        )
        .fillna(99)
    )

    result = (
        result
        .sort_values(
            by=[
                "_status_order",
                "Estate",
                "Field",
                "Planned Date",
                "Operation",
                "Fertilizer"
            ]
        )
        .drop(
            columns=[
                "_status_order"
            ]
        )
        .reset_index(
            drop=True
        )
    )

    # ======================================================
    # SAVE
    # ======================================================

    os.makedirs(
        os.path.dirname(
            FERTILIZER_SCHEDULE_FILE
        ),
        exist_ok=True
    )

    result.to_excel(
        FERTILIZER_SCHEDULE_FILE,
        index=False
    )

    # ======================================================
    # SUMMARY
    # ======================================================

    print(
        "=================================================="
    )

    print(
        "SEASON-AWARE FERTILIZER PROGRAMME GENERATED"
    )

    print(
        f"Season: {season}"
    )

    print(
        f"Season start: "
        f"{season_start.strftime('%Y-%m-%d')}"
    )

    print(
        f"Season end: "
        f"{season_end.strftime('%Y-%m-%d')}"
    )

    print(
        f"Rain-fed fertilizer start: "
        f"{rainfed_start_date.strftime('%Y-%m-%d')}"
    )

    print(
        f"Seasonal registered fields: "
        f"{len(registered_df)}"
    )

    print(
        f"Seasonal registered area: "
        f"{registered_df['Hectares'].sum():,.3f} ha"
    )

    print(
        f"Fields checked: "
        f"{fields_checked}"
    )

    print(
        f"Fields included: "
        f"{fields_included}"
    )

    print(
        f"Fields excluded: "
        f"{fields_excluded}"
    )

    print(
        f"Programme fields: "
        f"{result['Field'].nunique()}"
    )

    print(
        f"Programme records: "
        f"{len(result)}"
    )

    print(
        f"Overdue: "
        f"{(result['Status'] == 'OVERDUE').sum()}"
    )

    print(
        f"Due today: "
        f"{(result['Status'] == 'DUE TODAY').sum()}"
    )

    print(
        f"Due soon: "
        f"{(result['Status'] == 'DUE SOON').sum()}"
    )

    print(
        f"Scheduled: "
        f"{(result['Status'] == 'SCHEDULED').sum()}"
    )

    print(
        f"Applied: "
        f"{(result['Status'] == 'APPLIED').sum()}"
    )

    # ------------------------------------------------------
    # ESTATE SUMMARY
    # ------------------------------------------------------

    if "Fertilizer Calendar" in result.columns:

        print(
            "----------------------------------------------"
        )

        print(
            "FERTILIZER CALENDAR SUMMARY"
        )

        print(
            result[
                [
                    "Estate",
                    "Fertilizer Calendar"
                ]
            ]
            .drop_duplicates()
            .sort_values(
                [
                    "Estate"
                ]
            )
            .to_string(
                index=False
            )
        )

    print(
        f"Saved to: "
        f"{FERTILIZER_SCHEDULE_FILE}"
    )

    print(
        "=================================================="
    )

    return result
