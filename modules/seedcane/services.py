import os
import pandas as pd

from .calculations import (
    calculate_age_months,
    seedcane_age_status,
    get_estate
)


# ============================================================
# FILE LOCATIONS
# ============================================================

DATA_DIR = "data"

REGISTERED_FIELDS_FILE = os.path.join(
    DATA_DIR,
    "registered_fields.xlsx"
)

PLANTING_FILE = os.path.join(
    DATA_DIR,
    "planting_records.xlsx"
)

HARVEST_FILE = os.path.join(
    DATA_DIR,
    "harvesting_records.xlsx"
)

CROP_ESTIMATE_FILE = os.path.join(
    DATA_DIR,
    "crop_estimates.xlsx"
)

REPLANT_PLAN_FILE = os.path.join(
    DATA_DIR,
    "replant_plan.xlsx"
)

SEEDCANE_HAULAGE_FILE = os.path.join(
    DATA_DIR,
    "seedcane_haulage.xlsx"
)

SEEDCANE_GAPFILLING_FILE = os.path.join(
    DATA_DIR,
    "seedcane_gapfilling.xlsx"
)

SEEDCANE_RATE_TONS_PER_HA = 12.0
SEEDCANE_BUNDLE_TONS = 3.0

SEEDCANE_ALLOCATIONS_FILE = "data/seedcane_allocations.xlsx"
SEEDCANE_CUTTING_FILE = "data/seedcane_cutting.xlsx"

# ============================================================
# BASIC HELPERS
# ============================================================

def clean_field(value):
    """
    Standardise field names.

    Example:
        dg01001 -> DG01001
        DG01001 -> DG01001
    """

    if pd.isna(value):
        return ""

    return str(value).strip().upper()


def clean_season(value):
    """
    Standardise season values.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def clean_text(value):
    """
    Safely convert a value to clean text.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def load_excel(path):
    """
    Safely load an Excel file.
    """

    if not os.path.exists(path):

        print(
            f"Seedcane: file not found: {path}"
        )

        return pd.DataFrame()

    try:

        return pd.read_excel(path)

    except Exception as e:

        print(
            f"Seedcane: error reading {path}: {e}"
        )

        return pd.DataFrame()


# ============================================================
# REGISTERED FIELD VARIETY
# ============================================================

def get_registered_variety(row):
    """
    Get the field variety from registered_fields.xlsx.

    IMPORTANT
    ----------------------------------------------------------
    In the DCGL Farm Management System:

        registered_fields.xlsx["Crop Name"]

    is the authoritative field variety.

    Example:

        Field       Crop Name
        ----------------------
        DG01001     N41
        DG01002     N41
        DG01003     R570

    Therefore:

        Crop Name = Field Variety

    DO NOT use:

        planting_records.xlsx["Seed Variety"]

    because planting_records.xlsx records individual planting
    operations and is not the authoritative current field
    variety register.
    """

    if "Crop Name" not in row.index:

        return ""

    return clean_text(
        row.get(
            "Crop Name",
            ""
        )
    )


# ============================================================
# PARENT MAIN FIELD
# ============================================================

def get_parent_main_field(
    field,
    registered_main_field=None
):
    """
    Determine the parent Main Field for a subfield.

    Examples:

        DG01001 -> DG01000
        DG01002 -> DG01000
        DG01003 -> DG01000

        DG17001 -> DG17000
        DG17006 -> DG17000

        DG19006 -> DG19000

    If registered_fields.xlsx provides Main Field, that value
    is preferred because registered_fields.xlsx is the
    authoritative field hierarchy.
    """

    field = clean_field(
        field
    )

    # --------------------------------------------------------
    # Prefer Main Field from registered_fields.xlsx
    # --------------------------------------------------------

    if registered_main_field:

        main_field = clean_field(
            registered_main_field
        )

        if main_field:

            return main_field

    # --------------------------------------------------------
    # Derive parent from field naming convention
    # --------------------------------------------------------

    if not field:

        return ""

    if len(field) >= 2:

        last_two = field[-2:]

        if last_two.isdigit():

            return (
                field[:-2]
                + "00"
            )

    return field


# ============================================================
# REPLANT PLAN
# ============================================================

def load_replant_requirements(season):
    """
    Load approved replant requirements for the selected season.

    Source:
        data/replant_plan.xlsx

    Conditions:
        Season = selected season
        Approved = Yes
        Recommended Action = Replant
    """

    df = load_excel(
        REPLANT_PLAN_FILE
    )

    if df.empty:
        return pd.DataFrame()

    required_columns = [
        "Field",
        "Season",
        "Priority",
        "Reason",
        "Recommended Action",
        "Planned Planting Date",
        "Lock",
        "Approved"
    ]

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:

        print(
            "Seedcane: missing replant plan columns:",
            missing
        )

        return pd.DataFrame()

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    df["Field"] = (
        df["Field"]
        .apply(clean_field)
    )

    df["Season"] = (
        df["Season"]
        .apply(clean_season)
    )

    # --------------------------------------------------------
    # Season
    # --------------------------------------------------------

    df = df[
        df["Season"] == str(season).strip()
    ].copy()

    # --------------------------------------------------------
    # Approved
    # --------------------------------------------------------

    df = df[
        df["Approved"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin([
            "yes",
            "true",
            "1"
        ])
    ].copy()

    # --------------------------------------------------------
    # Replant only
    # --------------------------------------------------------

    df = df[
        df["Recommended Action"]
        .astype(str)
        .str.strip()
        .str.lower()
        == "replant"
    ].copy()

    # --------------------------------------------------------
    # Planned planting date
    # --------------------------------------------------------

    df["Planned Planting Date"] = pd.to_datetime(
        df["Planned Planting Date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Remove blank fields
    # --------------------------------------------------------

    df = df[
        df["Field"] != ""
    ].copy()

    return df


# ============================================================
# PLANTING HISTORY
# ============================================================

def load_planting_history():
    """
    Load planting_records.xlsx once.

    Planting records are used ONLY for determining the
    crop-cycle start date.

    IMPORTANT:
    ----------------------------------------------------------
    Variety is NOT taken from planting_records.xlsx.

    Field Variety comes from:

        registered_fields.xlsx["Crop Name"]
    """

    df = load_excel(
        PLANTING_FILE
    )

    if df.empty:
        return pd.DataFrame()

    required = [
        "Date",
        "Field",
        "Season"
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        print(
            "Seedcane: planting_records.xlsx "
            f"missing columns: {missing}"
        )

        return pd.DataFrame()

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    df["Field"] = (
        df["Field"]
        .apply(clean_field)
    )

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    df["Season"] = (
        df["Season"]
        .apply(clean_season)
    )

    df = df[
        (df["Field"] != "")
        & df["Date"].notna()
    ].copy()

    return df


# ============================================================
# HARVEST HISTORY
# ============================================================

def load_harvest_history():
    """
    Load harvesting_records.xlsx once.

    IMPORTANT:
    ----------------------------------------------------------
    Harvesting remains at ACTUAL SUBFIELD level.

    We do NOT convert DG01001 into DG01000 here.

    This is important for Seedcane because the actual source
    subfield must be preserved.
    """

    df = load_excel(
        HARVEST_FILE
    )

    if df.empty:
        return pd.DataFrame()

    required = [
        "Date",
        "Field",
        "Season"
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        print(
            "Seedcane: harvesting_records.xlsx "
            f"missing columns: {missing}"
        )

        return pd.DataFrame()

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    df["Field"] = (
        df["Field"]
        .apply(clean_field)
    )

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    df["Season"] = (
        df["Season"]
        .apply(clean_season)
    )

    df = df[
        (df["Field"] != "")
        & df["Date"].notna()
    ].copy()

    return df


# ============================================================
# CROP ESTIMATES
# ============================================================

def load_crop_estimates():
    """
    Load crop_estimates.xlsx once.

    IMPORTANT:
    ----------------------------------------------------------
    crop_estimates.xlsx stores TCH at MAIN FIELD level.

    Example:

        Main Field = DG01000
        TCH        = 105

    Therefore:

        DG01001 -> TCH 105
        DG01002 -> TCH 105
        DG01003 -> TCH 105

    etc.

    Seedcane candidates remain at SUBFIELD level.

    Field Variety is NOT taken from this workbook.
    """

    df = load_excel(
        CROP_ESTIMATE_FILE
    )

    if df.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # MAIN FIELD
    # --------------------------------------------------------

    if "Main Field" not in df.columns:

        # Backward compatibility
        if "Field" in df.columns:

            print(
                "Seedcane: crop_estimates.xlsx is using "
                "'Field' as the estimate field column. "
                "Treating it as Main Field."
            )

            df["Main Field"] = (
                df["Field"]
                .apply(clean_field)
            )

        else:

            print(
                "Seedcane: crop_estimates.xlsx "
                "does not contain Main Field column."
            )

            return pd.DataFrame()

    else:

        df["Main Field"] = (
            df["Main Field"]
            .apply(clean_field)
        )

    # --------------------------------------------------------
    # SEASON
    # --------------------------------------------------------

    if "Season" in df.columns:

        df["Season"] = (
            df["Season"]
            .apply(clean_season)
        )

    # --------------------------------------------------------
    # PLANTING DATE
    #
    # Supplementary only.
    # --------------------------------------------------------

    if "Planting Date" in df.columns:

        df["Planting Date"] = pd.to_datetime(
            df["Planting Date"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # TCH
    # --------------------------------------------------------

    if "TCH" in df.columns:

        df["TCH"] = pd.to_numeric(
            df["TCH"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # ESTIMATED YIELD
    # --------------------------------------------------------

    if "Estimated Yield (Tons)" in df.columns:

        df["Estimated Yield (Tons)"] = pd.to_numeric(
            df["Estimated Yield (Tons)"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Remove blank Main Fields
    # --------------------------------------------------------

    df = df[
        df["Main Field"] != ""
    ].copy()

    return df


# ============================================================
# CROP ESTIMATE LOOKUP
# ============================================================

def get_crop_estimate(
    field,
    season,
    estimates_df,
    registered_main_field=None,
    subfield_area=None
):
    """
    Get the crop estimate for a SUBFIELD by looking up its
    parent MAIN FIELD.

    Example:

        crop_estimates.xlsx

            Main Field = DG01000
            TCH = 105

        registered_fields.xlsx

            Field = DG01001
            Hectares = 3.008

        Result:

            TCH = 105

            Estimated Yield =
                3.008 x 105
                = 315.84 tons
    """

    empty_result = {

        "Main Field": "",

        "TCH": None,

        "Estimated Yield (Tons)": None,

        "Planting Date": None,

        "Crop Estimate Available": False
    }

    if estimates_df is None:
        return empty_result

    if estimates_df.empty:
        return empty_result

    field = clean_field(
        field
    )

    season = clean_season(
        season
    )

    # ========================================================
    # DETERMINE PARENT MAIN FIELD
    # ========================================================

    main_field = get_parent_main_field(
        field,
        registered_main_field
    )

    if not main_field:
        return empty_result

    # ========================================================
    # MATCH MAIN FIELD
    # ========================================================

    rows = estimates_df[
        estimates_df["Main Field"]
        == main_field
    ].copy()

    # ========================================================
    # SEASON
    # ========================================================

    if "Season" in rows.columns:

        rows = rows[
            rows["Season"] == season
        ].copy()

    if rows.empty:
        return empty_result

    # ========================================================
    # SELECT MOST USEFUL RECORD
    # ========================================================

    if "Planting Date" in rows.columns:

        rows_with_date = rows[
            rows["Planting Date"].notna()
        ].copy()

        if not rows_with_date.empty:

            rows = rows_with_date.sort_values(
                "Planting Date"
            )

    row = rows.iloc[-1]

    # ========================================================
    # TCH
    # ========================================================

    tch = row.get(
        "TCH",
        None
    )

    if pd.isna(tch):
        tch = None

    # ========================================================
    # PLANTING DATE
    # ========================================================

    planting_date = row.get(
        "Planting Date",
        None
    )

    if pd.isna(planting_date):
        planting_date = None

    # ========================================================
    # ESTIMATED YIELD
    #
    # SUBFIELD AREA x PARENT MAIN FIELD TCH
    # ========================================================

    estimated_yield = None

    if (
        tch is not None
        and subfield_area is not None
    ):

        try:

            area = float(
                subfield_area
            )

            estimated_yield = (
                area * float(tch)
            )

        except (
            TypeError,
            ValueError
        ):

            estimated_yield = None

    # --------------------------------------------------------
    # Fallback to estimate workbook's own value
    # --------------------------------------------------------

    if (
        estimated_yield is None
        and "Estimated Yield (Tons)" in row.index
    ):

        file_estimate = row.get(
            "Estimated Yield (Tons)"
        )

        if not pd.isna(file_estimate):

            estimated_yield = file_estimate

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "Main Field": main_field,

        "TCH": tch,

        "Estimated Yield (Tons)": estimated_yield,

        "Planting Date": planting_date,

        "Crop Estimate Available": True
    }


# ============================================================
# CURRENT CROP CYCLE
# ============================================================

def get_current_crop_cycle(
    field,
    planting_df,
    harvest_df,
    crop_estimates_df=None,
    season=None
):
    """
    Determine the current crop-cycle start date for a
    specific SUBFIELD.

    Variety is NOT calculated here.

    Field Variety comes directly from:

        registered_fields.xlsx["Crop Name"]

    This function determines only the current crop-cycle date.
    """

    field = clean_field(
        field
    )

    season = clean_season(
        season
    )

    # ========================================================
    # 1. GET PLANTING RECORDS
    # ========================================================

    field_plantings = pd.DataFrame()

    if not planting_df.empty:

        field_plantings = planting_df[
            planting_df["Field"] == field
        ].copy()

        field_plantings = field_plantings[
            field_plantings["Date"].notna()
        ].sort_values(
            "Date"
        )

    # ========================================================
    # 2. GET HARVEST RECORDS
    # ========================================================

    field_harvests = pd.DataFrame()

    if not harvest_df.empty:

        field_harvests = harvest_df[
            harvest_df["Field"] == field
        ].copy()

        field_harvests = field_harvests[
            field_harvests["Date"].notna()
        ].sort_values(
            "Date"
        )

    latest_harvest_date = None

    if not field_harvests.empty:

        latest_harvest_date = (
            field_harvests["Date"].max()
        )

    # ========================================================
    # 3. GET CROP ESTIMATE BASELINE
    # ========================================================

    crop_estimate = get_crop_estimate(
        field,
        season,
        crop_estimates_df
        if crop_estimates_df is not None
        else pd.DataFrame()
    )

    estimate_planting_date = (
        crop_estimate.get(
            "Planting Date"
        )
    )

    # ========================================================
    # 4. NO PLANTING RECORD
    # ========================================================

    if field_plantings.empty:

        if estimate_planting_date is not None:

            return (
                estimate_planting_date,
                "Crop Estimate",
                "Crop estimate planting date"
            )

        if latest_harvest_date is not None:

            return (
                latest_harvest_date,
                "Last Harvest",
                "Latest harvest available; no planting record"
            )

        return (
            None,
            None,
            "No planting record or harvest record"
        )

    # ========================================================
    # 5. DETERMINE PLANTING INFORMATION
    # ========================================================

    latest_planting_date = (
        field_plantings["Date"].max()
    )

    # ========================================================
    # 6. NO HARVEST
    # ========================================================

    if latest_harvest_date is None:

        cycle_start = (
            field_plantings["Date"].min()
        )

        return (
            cycle_start,
            "Planting Date",
            "Planting record available; no later harvest"
        )

    # ========================================================
    # 7. NEW PLANTING AFTER LATEST HARVEST
    # ========================================================

    if latest_planting_date > latest_harvest_date:

        current_campaign = field_plantings[
            field_plantings["Date"]
            > latest_harvest_date
        ]

        if not current_campaign.empty:

            cycle_start = (
                current_campaign["Date"].min()
            )

            return (
                cycle_start,
                "Planting Date",
                "New planting campaign after latest harvest"
            )

    # ========================================================
    # 8. RATOON CYCLE
    # ========================================================

    return (
        latest_harvest_date,
        "Last Harvest",
        "Ratoon cycle after latest harvest"
    )


# ============================================================
# SEEDCANE SOURCE CANDIDATES
# ============================================================

def get_seedcane_source_candidates(season):
    """
    Build potential seedcane source fields.

    STAGE 1
    ----------------------------------------------------------
    READ-ONLY.

    Does NOT create or modify:

        seedcane_sources.xlsx

    FIELD VARIETY
    ----------------------------------------------------------
    Field Variety comes from:

        registered_fields.xlsx["Crop Name"]

    NOT from:

        planting_records.xlsx["Seed Variety"]

    NOT from:

        crop_estimates.xlsx

    TCH
    ----------------------------------------------------------
    TCH comes from crop_estimates.xlsx at MAIN FIELD level.

    Example:

        DG01000 TCH = 105

    means:

        DG01001 TCH = 105
        DG01002 TCH = 105
        DG01003 TCH = 105

    ESTIMATED YIELD
    ----------------------------------------------------------
    For each subfield:

        Estimated Yield =
            Subfield Hectares x Parent Main Field TCH

    AGE
    ----------------------------------------------------------
    Expected seedcane age is calculated against the planned
    requirement date.

    It is NOT calculated against today's date.
    """

    season = clean_season(
        season
    )

    print("")
    print("=" * 70)
    print("SEEDCANE SOURCE ANALYSIS")
    print("=" * 70)

    print(
        f"SEASON: {season}"
    )

    # ========================================================
    # LOAD ALL WORKBOOKS ONCE
    # ========================================================

    registered_df = load_excel(
        REGISTERED_FIELDS_FILE
    )

    planting_df = load_planting_history()

    harvest_df = load_harvest_history()

    estimates_df = load_crop_estimates()

    requirements = load_replant_requirements(
        season
    )

    # ========================================================
    # VALIDATE REGISTERED FIELDS
    # ========================================================

    if registered_df.empty:

        print(
            "Seedcane: registered_fields.xlsx is empty."
        )

        return []

    if "Field" not in registered_df.columns:

        print(
            "Seedcane: registered_fields.xlsx "
            "does not contain Field column."
        )

        return []

    # ========================================================
    # CLEAN REGISTERED FIELDS
    # ========================================================

    registered_df["Field"] = (
        registered_df["Field"]
        .apply(clean_field)
    )

    # --------------------------------------------------------
    # Main Field
    # --------------------------------------------------------

    if "Main Field" in registered_df.columns:

        registered_df["Main Field"] = (
            registered_df["Main Field"]
            .apply(clean_field)
        )

    # --------------------------------------------------------
    # Season
    # --------------------------------------------------------

    if "Season" in registered_df.columns:

        registered_df["Season"] = (
            registered_df["Season"]
            .apply(clean_season)
        )

        registered_df = registered_df[
            registered_df["Season"] == season
        ].copy()

    registered_df = registered_df[
        registered_df["Field"] != ""
    ].copy()

    # --------------------------------------------------------
    # Remove duplicate field rows.
    # --------------------------------------------------------

    registered_df = (
        registered_df
        .drop_duplicates(
            subset=["Field"],
            keep="last"
        )
        .copy()
    )

    # ========================================================
    # REPLANT REQUIREMENTS
    # ========================================================

    if requirements.empty:

        print(
            "Seedcane: no approved replant requirements "
            f"for {season}."
        )

        return []

    # ========================================================
    # REQUIREMENT DATES
    # ========================================================

    planned_dates = requirements[
        "Planned Planting Date"
    ].dropna()

    if planned_dates.empty:

        print(
            "Seedcane: no valid planned planting dates."
        )

        return []

    # ========================================================
    # STAGE 1 SCREENING DATE
    # ========================================================

    planned_requirement_date = (
        planned_dates.min()
    )

    print(
        "EARLIEST PLANNED REQUIREMENT:",
        planned_requirement_date.strftime(
            "%Y-%m-%d"
        )
    )

    # ========================================================
    # DATA COUNTS
    # ========================================================

    print(
        "REGISTERED FIELDS:",
        len(registered_df)
    )

    print(
        "PLANTING RECORDS:",
        len(planting_df)
    )

    print(
        "HARVEST RECORDS:",
        len(harvest_df)
    )

    print(
        "CROP ESTIMATE RECORDS:",
        len(estimates_df)
    )

    print(
        "REPLANT REQUIREMENTS:",
        len(requirements)
    )

    # ========================================================
    # BUILD CANDIDATES
    # ========================================================

    candidates = []

    for _, row in registered_df.iterrows():

        field = clean_field(
            row.get(
                "Field",
                ""
            )
        )

        if not field:
            continue

        # ====================================================
        # MAIN FIELD
        # ====================================================

        main_field = clean_text(
            row.get(
                "Main Field",
                ""
            )
        )

        if not main_field:

            main_field = get_parent_main_field(
                field
            )

        # ====================================================
        # AREA
        # ====================================================

        area = row.get(
            "Hectares",
            ""
        )

        try:

            area = float(
                area
            )

        except (
            TypeError,
            ValueError
        ):

            area = None

        # ====================================================
        # FIELD VARIETY
        #
        # AUTHORITATIVE SOURCE:
        #
        # registered_fields.xlsx["Crop Name"]
        #
        # NOT planting_records.xlsx["Seed Variety"]
        # ====================================================

        field_variety = get_registered_variety(
            row
        )

        # ====================================================
        # CURRENT CROP CYCLE
        # ====================================================

        (
            cycle_start,
            age_source,
            cycle_reason
        ) = get_current_crop_cycle(
            field,
            planting_df,
            harvest_df,
            estimates_df,
            season
        )

        # ====================================================
        # EXPECTED AGE AT REQUIREMENT DATE
        # ====================================================

        age_months = calculate_age_months(
            cycle_start,
            planned_requirement_date
        )

        # ====================================================
        # SEEDCANE AGE STATUS
        # ====================================================

        suitability = seedcane_age_status(
            age_months
        )

        # ====================================================
        # MISSING DATA
        # ====================================================

        if cycle_start is None:

            missing_data_reason = cycle_reason

        elif age_months is None:

            missing_data_reason = (
                "Crop cycle established but "
                "reference date unavailable"
            )

        else:

            missing_data_reason = ""

        # ====================================================
        # CROP ESTIMATE
        # ====================================================

        estimate = get_crop_estimate(
            field,
            season,
            estimates_df,
            registered_main_field=main_field,
            subfield_area=area
        )

        # ====================================================
        # CROP NAME
        #
        # Same authoritative field as variety.
        # ====================================================

        crop = clean_text(
            row.get(
                "Crop Name",
                ""
            )
        )

        # ====================================================
        # GROWER
        # ====================================================

        grower = clean_text(
            row.get(
                "Growers Name",
                ""
            )
        )

        # ====================================================
        # CROP CYCLE START DISPLAY
        # ====================================================

        cycle_start_display = ""

        if cycle_start is not None:

            cycle_start_display = (
                pd.to_datetime(
                    cycle_start
                ).strftime(
                    "%Y-%m-%d"
                )
            )

        # ====================================================
        # ESTIMATE PLANTING DATE DISPLAY
        # ====================================================

        estimate_planting_date = (
            estimate.get(
                "Planting Date"
            )
        )

        estimate_planting_display = ""

        if estimate_planting_date is not None:

            estimate_planting_display = (
                pd.to_datetime(
                    estimate_planting_date
                ).strftime(
                    "%Y-%m-%d"
                )
            )

        # ====================================================
        # BUILD CANDIDATE
        # ====================================================

        candidates.append({

            # ------------------------------------------------
            # FIELD IDENTITY
            # ------------------------------------------------

            "Field": field,

            "Main Field": main_field,

            "Estate": get_estate(
                field
            ),

            "Grower": grower,

            "Area (Ha)": area,

            # ------------------------------------------------
            # CURRENT REGISTERED CROP
            # ------------------------------------------------

            "Crop": crop,

            # IMPORTANT:
            # registered_fields.xlsx["Crop Name"]
            "Variety": field_variety,

            # ------------------------------------------------
            # CROP CYCLE
            # ------------------------------------------------

            "Crop Cycle Start": (
                cycle_start_display
            ),

            "Age Source": (
                age_source
                if age_source
                else ""
            ),

            "Crop Cycle Reason": (
                cycle_reason
                if cycle_reason
                else ""
            ),

            "Crop Estimate Planting Date": (
                estimate_planting_display
            ),

            # ------------------------------------------------
            # SEEDCANE REQUIREMENT
            # ------------------------------------------------

            "Planned Requirement Date": (
                planned_requirement_date.strftime(
                    "%Y-%m-%d"
                )
            ),

            "Expected Age (Months)": (
                age_months
                if age_months is not None
                else ""
            ),

            # ------------------------------------------------
            # PRODUCTION INFORMATION
            # ------------------------------------------------

            "TCH": estimate.get(
                "TCH"
            ),

            "Estimated Yield (Tons)": (
                estimate.get(
                    "Estimated Yield (Tons)"
                )
            ),

            "Crop Estimate Available": (
                "Yes"
                if estimate.get(
                    "Crop Estimate Available"
                )
                else "No"
            ),

            # ------------------------------------------------
            # SUITABILITY
            # ------------------------------------------------

            "Suitability": suitability,

            "Missing Data Reason": (
                missing_data_reason
            ),

            # ------------------------------------------------
            # SOURCE DESIGNATION
            # ------------------------------------------------

            "Selected": "No"
        })

    # ========================================================
    # SORT
    # ========================================================

    suitability_order = {

        "Suitable": 0,

        "Too Young": 1,

        "Too Old": 2,

        "Missing Data": 3
    }

    candidates.sort(
        key=lambda x: (
            suitability_order.get(
                x.get(
                    "Suitability"
                ),
                9
            ),

            x.get(
                "Estate",
                ""
            ),

            x.get(
                "Field",
                ""
            )
        )
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    suitable = sum(
        1
        for row in candidates
        if row["Suitability"]
        == "Suitable"
    )

    too_young = sum(
        1
        for row in candidates
        if row["Suitability"]
        == "Too Young"
    )

    too_old = sum(
        1
        for row in candidates
        if row["Suitability"]
        == "Too Old"
    )

    missing = sum(
        1
        for row in candidates
        if row["Suitability"]
        == "Missing Data"
    )

    # ========================================================
    # ADDITIONAL DATA-QUALITY COUNTS
    # ========================================================

    planting_record_count = sum(
        1
        for row in candidates
        if row["Age Source"]
        == "Planting Date"
    )

    harvest_record_count = sum(
        1
        for row in candidates
        if row["Age Source"]
        == "Last Harvest"
    )

    crop_estimate_cycle_count = sum(
        1
        for row in candidates
        if row["Age Source"]
        == "Crop Estimate"
    )

    registered_variety_count = sum(
        1
        for row in candidates
        if row["Variety"]
    )

    missing_variety_count = sum(
        1
        for row in candidates
        if not row["Variety"]
    )

    # ========================================================
    # CONSOLE SUMMARY
    # ========================================================

    print("")
    print(
        "SEEDCANE SOURCE SUMMARY"
    )
    print("-" * 50)

    print(
        "TOTAL CANDIDATES:",
        len(candidates)
    )

    print(
        "SUITABLE:",
        suitable
    )

    print(
        "TOO YOUNG:",
        too_young
    )

    print(
        "TOO OLD:",
        too_old
    )

    print(
        "MISSING DATA:",
        missing
    )

    print("")
    print(
        "CROP-CYCLE DATA SOURCES"
    )
    print("-" * 50)

    print(
        "PLANTING RECORD:",
        planting_record_count
    )

    print(
        "LAST HARVEST:",
        harvest_record_count
    )

    print(
        "CROP ESTIMATE:",
        crop_estimate_cycle_count
    )

    print("")
    print(
        "REGISTERED FIELD VARIETY DATA"
    )
    print("-" * 50)

    print(
        "VARIETY AVAILABLE:",
        registered_variety_count
    )

    print(
        "VARIETY MISSING:",
        missing_variety_count
    )

    print("=" * 70)
    print("")

    return candidates

# ============================================================
# STAGE 2A — DESTINATION-SPECIFIC SEEDCANE SUITABILITY
# ============================================================

def get_seedcane_sources_for_destination(
    destination_field,
    season
):
    """
    Return seedcane source subfields for ONE destination.

    The seedcane age is calculated against the destination's
    individual Planned Planting Date.

    IMPORTANT
    ----------------------------------------------------------
    Source field:
        Always the registered subfield.

    Variety:
        registered_fields.xlsx["Crop Name"]

    Main Field:
        registered_fields.xlsx["Main Field"] when available,
        otherwise derived from the field number.

    TCH:
        crop_estimates.xlsx at MAIN FIELD level.

    Estimated seedcane yield:
        Subfield Hectares x Parent Main Field TCH.

    Allocation:
        Existing allocations are handled later by
        prepare_destination_sources().
    """

    season = clean_season(season)

    destination_field = clean_field(
        destination_field
    )

    # ========================================================
    # 1. LOAD DESTINATION REQUIREMENTS
    # ========================================================

    requirements = load_replant_requirements(
        season
    )

    if requirements.empty:

        return {
            "destination": destination_field,
            "season": season,
            "planned_date": None,
            "priority": "",
            "reason": "",
            "sources": []
        }

    # ========================================================
    # 2. FIND DESTINATION
    # ========================================================

    requirements["Field"] = (
        requirements["Field"]
        .apply(clean_field)
    )

    destination_rows = requirements[
        requirements["Field"] == destination_field
    ].copy()

    if destination_rows.empty:

        return {
            "destination": destination_field,
            "season": season,
            "planned_date": None,
            "priority": "",
            "reason": "",
            "sources": []
        }

    # Normally there should be one approved requirement
    destination = destination_rows.iloc[0]

    # ========================================================
    # 3. PLANNED PLANTING DATE
    # ========================================================

    planned_date = pd.to_datetime(
        destination.get(
            "Planned Planting Date"
        ),
        errors="coerce"
    )

    if pd.isna(planned_date):

        return {
            "destination": destination_field,
            "season": season,
            "planned_date": None,
            "priority": clean_text(
                destination.get(
                    "Priority",
                    ""
                )
            ),
            "reason": clean_text(
                destination.get(
                    "Reason",
                    ""
                )
            ),
            "sources": []
        }

    # ========================================================
    # 4. LOAD REGISTERED FIELDS
    # ========================================================

    registered_df = load_excel(
        REGISTERED_FIELDS_FILE
    )

    if registered_df.empty:

        return {
            "destination": destination_field,
            "season": season,
            "planned_date": planned_date,
            "priority": clean_text(
                destination.get(
                    "Priority",
                    ""
                )
            ),
            "reason": clean_text(
                destination.get(
                    "Reason",
                    ""
                )
            ),
            "sources": []
        }

    # ========================================================
    # 5. VALIDATE FIELD COLUMN
    # ========================================================

    if "Field" not in registered_df.columns:

        print(
            "Seedcane: registered_fields.xlsx "
            "does not contain Field column."
        )

        return {
            "destination": destination_field,
            "season": season,
            "planned_date": planned_date,
            "priority": clean_text(
                destination.get(
                    "Priority",
                    ""
                )
            ),
            "reason": clean_text(
                destination.get(
                    "Reason",
                    ""
                )
            ),
            "sources": []
        }

    # ========================================================
    # 6. CLEAN REGISTERED FIELDS
    # ========================================================

    registered_df["Field"] = (
        registered_df["Field"]
        .apply(clean_field)
    )

    if "Main Field" in registered_df.columns:

        registered_df["Main Field"] = (
            registered_df["Main Field"]
            .apply(clean_field)
        )

    if "Season" in registered_df.columns:

        registered_df["Season"] = (
            registered_df["Season"]
            .apply(clean_season)
        )

        registered_df = registered_df[
            registered_df["Season"] == season
        ].copy()

    registered_df = registered_df[
        registered_df["Field"] != ""
    ].copy()

    # ========================================================
    # 7. LOAD SUPPORTING DATA ONCE
    # ========================================================

    planting_df = load_planting_history()

    harvest_df = load_harvest_history()

    estimates_df = load_crop_estimates()

    # ========================================================
    # 8. BUILD SOURCE LIST
    # ========================================================

    sources = []

    for _, row in registered_df.iterrows():

        source_field = clean_field(
            row.get(
                "Field",
                ""
            )
        )

        if not source_field:
            continue

        # ----------------------------------------------------
        # Do not offer the destination itself as a source
        # ----------------------------------------------------

        if source_field == destination_field:
            continue

        # ----------------------------------------------------
        # Variety
        #
        # AUTHORITATIVE:
        # registered_fields.xlsx["Crop Name"]
        # ----------------------------------------------------

        variety = get_registered_variety(
            row
        )

        # ----------------------------------------------------
        # Main Field
        # ----------------------------------------------------

        registered_main_field = clean_text(
            row.get(
                "Main Field",
                ""
            )
        )

        main_field = get_parent_main_field(
            source_field,
            registered_main_field
        )

        # ----------------------------------------------------
        # Area
        # ----------------------------------------------------

        area = row.get(
            "Hectares",
            None
        )

        try:

            area = float(
                area
            )

        except (
            TypeError,
            ValueError
        ):

            area = None

        # ----------------------------------------------------
        # Current crop cycle
        #
        # IMPORTANT:
        # This function returns a tuple.
        # ----------------------------------------------------

        (
            cycle_start,
            age_source,
            cycle_reason
        ) = get_current_crop_cycle(
            source_field,
            planting_df,
            harvest_df,
            estimates_df,
            season
        )

        # ----------------------------------------------------
        # Age at destination requirement date
        # ----------------------------------------------------

        age_months = calculate_age_months(
            cycle_start,
            planned_date
        )

        age_status = seedcane_age_status(
            age_months
        )

        # ----------------------------------------------------
        # Crop estimate
        #
        # Parent Main Field TCH x source subfield area
        # ----------------------------------------------------

        estimate = get_crop_estimate(
            source_field,
            season,
            estimates_df,
            registered_main_field=main_field,
            subfield_area=area
        )

        tch = estimate.get(
            "TCH"
        )

        estimated_yield = estimate.get(
            "Estimated Yield (Tons)"
        )

        # ----------------------------------------------------
        # Crop Cycle Start display
        # ----------------------------------------------------

        cycle_start_display = ""

        if cycle_start is not None:

            cycle_start_display = (
                pd.to_datetime(
                    cycle_start
                ).strftime(
                    "%Y-%m-%d"
                )
            )

        # ----------------------------------------------------
        # Build source
        # ----------------------------------------------------

        sources.append({

            "Source Field": source_field,

            "Main Field": main_field,

            "Estate": get_estate(
                source_field
            ),

            "Grower": clean_text(
                row.get(
                    "Growers Name",
                    ""
                )
            ),

            "Variety": variety,

            "Hectares": area,

            "Crop": clean_text(
                row.get(
                    "Crop Name",
                    ""
                )
            ),

            "Crop Cycle Start": (
                cycle_start_display
            ),

            "Age Source": (
                age_source
                if age_source
                else ""
            ),

            "Crop Cycle Reason": (
                cycle_reason
                if cycle_reason
                else ""
            ),

            "Age Months": (
                age_months
                if age_months is not None
                else ""
            ),

            "Age Status": age_status,

            "TCH": tch,

            "Estimated Yield Tons": (
                estimated_yield
            ),

            "Destination": (
                destination_field
            ),

            "Requirement Date": (
                planned_date.strftime(
                    "%Y-%m-%d"
                )
            ),

            "Reason": clean_text(
                destination.get(
                    "Reason",
                    ""
                )
            ),

            "Priority": clean_text(
                destination.get(
                    "Priority",
                    ""
                )
            )
        })

    # ========================================================
    # 9. SORT
    # ========================================================

    status_order = {

        "Suitable": 0,

        "Too Young": 1,

        "Too Old": 2,

        "Missing Data": 3
    }

    sources.sort(
        key=lambda x: (
            status_order.get(
                x.get(
                    "Age Status",
                    ""
                ),
                99
            ),

            -(
                float(
                    x.get(
                        "Age Months",
                        0
                    ) or 0
                )
                if str(
                    x.get(
                        "Age Months",
                        ""
                    )
                ).replace(
                    ".",
                    "",
                    1
                ).isdigit()
                else 0
            ),

            x.get(
                "Source Field",
                ""
            )
        )
    )

    # ========================================================
    # 10. RETURN
    # ========================================================

    return {

        "destination": destination_field,

        "season": season,

        "planned_date": planned_date,

        "priority": clean_text(
            destination.get(
                "Priority",
                ""
            )
        ),

        "reason": clean_text(
            destination.get(
                "Reason",
                ""
            )
        ),

        "sources": sources
    }

# ============================================================
# STAGE 2B — SEEDCANE ALLOCATIONS
# ============================================================

SEEDCANE_ALLOCATIONS_FILE = "data/seedcane_allocations.xlsx"


def load_seedcane_allocations():
    """
    Load planned source-to-destination seedcane allocations.

    Returns an empty DataFrame with the correct structure when
    the allocation file does not yet exist.
    """

    columns = [
        "Allocation ID",
        "Season",
        "Allocation Date",
        "Destination Field",
        "Source Field",
        "Main Field",
        "Estate",
        "Variety",
        "Use Type",
        "Planned Tonnes",
        "Status",
        "Notes"
    ]

    if not os.path.exists(SEEDCANE_ALLOCATIONS_FILE):
        return pd.DataFrame(columns=columns)

    try:
        df = pd.read_excel(SEEDCANE_ALLOCATIONS_FILE)

        for column in columns:
            if column not in df.columns:
                df[column] = ""

        return df[columns]

    except Exception:
        return pd.DataFrame(columns=columns)


def get_allocated_tonnes(source_field, season):
    """
    Return total planned tonnes already allocated from a
    particular source field for the selected season.
    """

    df = load_seedcane_allocations()

    if df.empty:
        return 0.0

    df["Season"] = (
        df["Season"]
        .astype(str)
        .str.strip()
    )

    df["Source Field"] = (
        df["Source Field"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    filtered = df[
        (df["Season"] == str(season).strip()) &
        (df["Source Field"] == str(source_field).strip().upper()) &
        (df["Status"].astype(str).str.strip().str.upper() != "CANCELLED")
    ]

    if filtered.empty:
        return 0.0

    return pd.to_numeric(
        filtered["Planned Tonnes"],
        errors="coerce"
    ).fillna(0).sum()


def get_source_available_tonnes(source, season):
    """
    Calculate remaining planned seedcane available from a source.

    Estimated yield comes from the existing crop estimate logic.
    Existing allocations are deducted.
    """

    estimated_yield = source.get(
        "Estimated Yield Tons"
    )

    if estimated_yield is None:
        estimated_yield = source.get(
            "Estimated Yield (Tons)"
        )

    try:
        estimated_yield = float(
            estimated_yield or 0
        )
    except (TypeError, ValueError):
        estimated_yield = 0.0

    source_field = source.get(
        "Source Field"
    ) or source.get(
        "Field",
        ""
    )

    allocated = get_allocated_tonnes(
        source_field,
        season
    )

    remaining = max(
        estimated_yield - allocated,
        0
    )

    return {
        "Estimated Yield Tons": estimated_yield,
        "Allocated Tons": allocated,
        "Remaining Tons": remaining
    }

def prepare_destination_sources(
    destination_field,
    season
):
    """
    Prepare the destination source list for allocation.

    Only suitable sources are returned for allocation.
    Each source includes its estimated, allocated and
    remaining seedcane balance.
    """

    result = get_seedcane_sources_for_destination(
        destination_field,
        season
    )

    sources = []

    for source in result.get("sources", []):

        if source.get("Age Status") != "Suitable":
            continue

        balance = get_source_available_tonnes(
            source,
            season
        )

        source = dict(source)

        source.update(balance)

        sources.append(source)

    return {
        "destination": result.get("destination"),
        "season": result.get("season"),
        "planned_date": result.get("planned_date"),
        "priority": result.get("priority", ""),
        "reason": result.get("reason", ""),
        "sources": sources
    }

# ============================================================
# STAGE 2C — SAVE SEEDCANE ALLOCATIONS
# ============================================================

from datetime import datetime


def generate_allocation_id():
    """
    Generate a unique allocation ID.
    """

    df = load_seedcane_allocations()

    if df.empty:
        return "SCA-0001"

    numbers = []

    for value in df["Allocation ID"].astype(str):

        value = value.strip().upper()

        if value.startswith("SCA-"):

            try:
                number = int(value.replace("SCA-", ""))
                numbers.append(number)
            except ValueError:
                continue

    next_number = max(numbers, default=0) + 1

    return f"SCA-{next_number:04d}"


def save_seedcane_allocations(
    destination_field,
    season,
    allocations
):
    """
    Save validated source-to-destination seedcane
    allocations.

    allocations must be a list containing dictionaries:

        {
            "source_field": "...",
            "planned_tonnes": 10.0
        }

    Returns:

        {
            "success": True/False,
            "message": "...",
            "saved": [...]
        }
    """

    destination_field = (
        str(destination_field)
        .strip()
        .upper()
    )

    season = str(season).strip()

    if not allocations:
        return {
            "success": False,
            "message": "No seedcane allocations were supplied.",
            "saved": []
        }

    # --------------------------------------------------------
    # Destination validation
    # --------------------------------------------------------

    requirements = load_replant_requirements(season)

    if requirements.empty:
        return {
            "success": False,
            "message": (
                f"No approved replant requirement exists "
                f"for {destination_field} in season {season}."
            ),
            "saved": []
        }

    requirements["Field"] = (
        requirements["Field"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    destination_rows = requirements[
        requirements["Field"] == destination_field
    ]

    if destination_rows.empty:
        return {
            "success": False,
            "message": (
                f"{destination_field} is not an approved "
                f"replant destination for season {season}."
            ),
            "saved": []
        }

    destination = destination_rows.iloc[0]

    planned_date = pd.to_datetime(
        destination.get("Planned Planting Date"),
        errors="coerce"
    )

    if pd.isna(planned_date):
        return {
            "success": False,
            "message": (
                f"{destination_field} does not have a "
                f"valid planned planting date."
            ),
            "saved": []
        }

    # --------------------------------------------------------
    # Get suitable sources
    # --------------------------------------------------------

    source_result = prepare_destination_sources(
        destination_field,
        season
    )

    source_map = {
        str(source["Source Field"])
        .strip()
        .upper(): source
        for source in source_result["sources"]
    }

    # --------------------------------------------------------
    # Validate ALL allocations BEFORE saving ANYTHING
    # --------------------------------------------------------

    validated = []

    for allocation in allocations:

        source_field = (
            str(allocation.get("source_field", ""))
            .strip()
            .upper()
        )

        raw_tonnes = allocation.get(
            "planned_tonnes"
        )

        # ----------------------------------------------------
        # Source must exist
        # ----------------------------------------------------

        if source_field not in source_map:
            return {
                "success": False,
                "message": (
                    f"{source_field} is not a valid "
                    f"suitable source for {destination_field}."
                ),
                "saved": []
            }

        source = source_map[source_field]

        # ----------------------------------------------------
        # Convert tonnes
        # ----------------------------------------------------

        try:
            tonnes = float(raw_tonnes)
        except (TypeError, ValueError):
            return {
                "success": False,
                "message": (
                    f"Invalid planned tonnes for "
                    f"{source_field}."
                ),
                "saved": []
            }

        if tonnes <= 0:
            return {
                "success": False,
                "message": (
                    f"Planned tonnes for {source_field} "
                    f"must be greater than zero."
                ),
                "saved": []
            }

        # ----------------------------------------------------
        # Check available balance
        # ----------------------------------------------------

        remaining = float(
            source.get("Remaining Tons", 0) or 0
        )

        if tonnes > remaining:

            return {
                "success": False,
                "message": (
                    f"Allocation of {tonnes:.1f} tonnes "
                    f"from {source_field} exceeds the "
                    f"remaining available balance of "
                    f"{remaining:.1f} tonnes."
                ),
                "saved": []
            }

        validated.append({
            "source_field": source_field,
            "planned_tonnes": round(tonnes, 2),
            "source": source
        })

    # --------------------------------------------------------
    # Load existing allocations
    # --------------------------------------------------------

    df = load_seedcane_allocations()

    new_rows = []

    for item in validated:

        source = item["source"]

        allocation_id = generate_allocation_id()

        new_rows.append({
            "Allocation ID": allocation_id,
            "Season": season,
            "Allocation Date": datetime.now().strftime("%Y-%m-%d"),
            "Destination Field": destination_field,
            "Source Field": item["source_field"],
            "Main Field": source.get("Main Field", ""),
            "Estate": source.get("Estate", ""),
            "Variety": source.get("Variety", ""),
            "Use Type": "New Planting",
            "Planned Tonnes": item["planned_tonnes"],
            "Status": "Planned",
            "Notes": ""
        })

    # --------------------------------------------------------
    # Append
    # --------------------------------------------------------

    new_df = pd.DataFrame(new_rows)

    if df.empty:
        final_df = new_df
    else:
        final_df = pd.concat(
            [df, new_df],
            ignore_index=True
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    os.makedirs(
        os.path.dirname(SEEDCANE_ALLOCATIONS_FILE),
        exist_ok=True
    )

    final_df.to_excel(
        SEEDCANE_ALLOCATIONS_FILE,
        index=False
    )

    return {
        "success": True,
        "message": (
            f"{len(new_rows)} seedcane allocation(s) "
            f"saved successfully."
        ),
        "saved": new_rows
    }

# ============================================================
# SEEDCANE ALLOCATION REGISTER
# ============================================================

def get_destination_hectares(destination_field, season):
    """
    Get the total registered hectares for a destination main field.

    The registered_fields.xlsx file normally stores the actual
    hectares against subfields, for example:

        Main Field | Field
        DG22000    | DG22001
        DG22000    | DG22002
        DG22000    | DG22003

    Therefore the destination area is the sum of the Hectares
    belonging to that Main Field.

    The function also supports the case where the destination
    itself exists directly in the Field column.
    """

    if not os.path.exists(REGISTERED_FIELDS_FILE):
        return 0.0

    destination_field = (
        str(destination_field)
        .strip()
        .upper()
    )

    season = str(season).strip()

    try:
        df = pd.read_excel(
            REGISTERED_FIELDS_FILE
        )

        required_columns = {
            "Field",
            "Main Field",
            "Hectares",
            "Season"
        }

        if not required_columns.issubset(df.columns):
            return 0.0

        # ----------------------------------------------------
        # CLEAN IDENTIFIERS
        # ----------------------------------------------------

        df["Field"] = (
            df["Field"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        df["Main Field"] = (
            df["Main Field"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        df["Season"] = (
            df["Season"]
            .astype(str)
            .str.strip()
        )

        df["Hectares"] = pd.to_numeric(
            df["Hectares"],
            errors="coerce"
        ).fillna(0)

        # ----------------------------------------------------
        # FILTER SELECTED SEASON
        # ----------------------------------------------------

        season_df = df[
            df["Season"] == season
        ].copy()

        if season_df.empty:
            return 0.0

        # ----------------------------------------------------
        # PRIMARY METHOD:
        # SUM ALL SUBFIELDS BELONGING TO MAIN FIELD
        # ----------------------------------------------------

        main_field_rows = season_df[
            season_df["Main Field"]
            == destination_field
        ]

        if not main_field_rows.empty:

            total_hectares = (
                main_field_rows["Hectares"]
                .sum()
            )

            if total_hectares > 0:
                return round(
                    float(total_hectares),
                    2
                )

        # ----------------------------------------------------
        # FALLBACK:
        # DESTINATION MAY EXIST DIRECTLY IN FIELD COLUMN
        # ----------------------------------------------------

        direct_rows = season_df[
            season_df["Field"]
            == destination_field
        ]

        if not direct_rows.empty:

            total_hectares = (
                direct_rows["Hectares"]
                .sum()
            )

            return round(
                float(total_hectares),
                2
            )

        # ----------------------------------------------------
        # NOTHING FOUND
        # ----------------------------------------------------

        return 0.0

    except Exception as exc:

        print(
            f"ERROR calculating hectares for "
            f"{destination_field}: {exc}"
        )

        return 0.0


def get_destination_requirement(destination_field, season):
    """
    Calculate seedcane requirement for a destination.

    Standard planting rate:
        12 tonnes per hectare
    """

    hectares = get_destination_hectares(
        destination_field,
        season
    )

    required_tonnes = hectares * SEEDCANE_RATE_TONS_PER_HA

    return {
        "Hectares": round(hectares, 2),
        "Seedcane Rate": SEEDCANE_RATE_TONS_PER_HA,
        "Required Tons": round(required_tonnes, 2)
    }


def get_destination_allocated_tonnes(destination_field, season):
    """
    Return total planned seedcane allocation for a destination.
    """

    df = load_seedcane_allocations()

    if df.empty:
        return 0.0

    df["Season"] = (
        df["Season"]
        .astype(str)
        .str.strip()
    )

    df["Destination Field"] = (
        df["Destination Field"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    filtered = df[
        (df["Season"] == str(season).strip()) &
        (
            df["Destination Field"]
            == str(destination_field).strip().upper()
        ) &
        (
            df["Status"]
            .astype(str)
            .str.strip()
            .str.upper()
            != "CANCELLED"
        )
    ]

    if filtered.empty:
        return 0.0

    return round(
        pd.to_numeric(
            filtered["Planned Tonnes"],
            errors="coerce"
        ).fillna(0).sum(),
        2
    )


def get_destination_allocation_register(season):
    """
    Build the complete Seedcane Allocation Register.

    Each approved replant destination is shown once,
    with its 12 t/ha seedcane requirement and all
    planned source allocations.
    """

    requirements = load_replant_requirements(season)

    if requirements.empty:
        return []

    registered_df = pd.DataFrame()

    if os.path.exists(REGISTERED_FIELDS_FILE):
        try:
            registered_df = pd.read_excel(
                REGISTERED_FIELDS_FILE
            )
        except Exception:
            registered_df = pd.DataFrame()

    if not registered_df.empty:
        if "Field" in registered_df.columns:
            registered_df["Field"] = (
                registered_df["Field"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

        if "Season" in registered_df.columns:
            registered_df["Season"] = (
                registered_df["Season"]
                .astype(str)
                .str.strip()
            )

    records = []

    for _, requirement in requirements.iterrows():

        destination = str(
            requirement.get("Field", "")
        ).strip().upper()

        if not destination:
            continue

        # ----------------------------------------------------
        # Destination information
        # ----------------------------------------------------

        hectares = get_destination_hectares(
            destination,
            season
        )

        estate = get_estate(destination)

        # Try to obtain the estate/location from the
        # registered field records.
        if not registered_df.empty and "Main Field" in registered_df.columns:

            matching = registered_df[
                (registered_df["Main Field"] == destination) &
                (
                        registered_df["Season"]
                        == str(season).strip()
                )
                ]

            if not matching.empty and "Location" in matching.columns:

                location = str(
                    matching.iloc[0].get(
                        "Location",
                        ""
                    )
                ).strip()

                if location:
                    estate = location

        # ----------------------------------------------------
        # Seedcane requirement
        # ----------------------------------------------------

        required_tonnes = (
            hectares *
            SEEDCANE_RATE_TONS_PER_HA
        )

        # ----------------------------------------------------
        # Planned allocations
        # ----------------------------------------------------

        allocations = []

        allocation_df = load_seedcane_allocations()

        if not allocation_df.empty:

            destination_allocations = allocation_df[
                (
                    allocation_df["Season"]
                    .astype(str)
                    .str.strip()
                    == str(season).strip()
                )
                &
                (
                    allocation_df["Destination Field"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    == destination
                )
                &
                (
                    allocation_df["Status"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    != "CANCELLED"
                )
            ]

            for _, allocation in destination_allocations.iterrows():

                allocations.append({
                    "Allocation ID": allocation.get(
                        "Allocation ID",
                        ""
                    ),
                    "Source Field": allocation.get(
                        "Source Field",
                        ""
                    ),
                    "Main Field": allocation.get(
                        "Main Field",
                        ""
                    ),
                    "Estate": allocation.get(
                        "Estate",
                        ""
                    ),
                    "Variety": allocation.get(
                        "Variety",
                        ""
                    ),
                    "Planned Tonnes": round(
                        float(
                            pd.to_numeric(
                                allocation.get(
                                    "Planned Tonnes",
                                    0
                                ),
                                errors="coerce"
                            ) or 0
                        ),
                        2
                    ),
                    "Status": allocation.get(
                        "Status",
                        ""
                    ),
                    "Notes": allocation.get(
                        "Notes",
                        ""
                    )
                })

        allocated_tonnes = round(
            sum(
                item["Planned Tonnes"]
                for item in allocations
            ),
            2
        )

        remaining_tonnes = round(
            max(
                required_tonnes - allocated_tonnes,
                0
            ),
            2
        )

        excess_tonnes = round(
            max(
                allocated_tonnes - required_tonnes,
                0
            ),
            2
        )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        if required_tonnes <= 0:
            allocation_status = "Missing Area"

        elif allocated_tonnes <= 0:
            allocation_status = "Not Allocated"

        elif allocated_tonnes < required_tonnes:
            allocation_status = "Partially Allocated"

        elif allocated_tonnes == required_tonnes:
            allocation_status = "Fully Allocated"

        else:
            allocation_status = "Over Allocated"

        planned_date = pd.to_datetime(
            requirement.get(
                "Planned Planting Date"
            ),
            errors="coerce"
        )

        records.append({
            "Destination Field": destination,
            "Estate": estate,
            "Hectares": round(
                hectares,
                2
            ),
            "Seedcane Rate": SEEDCANE_RATE_TONS_PER_HA,
            "Required Tons": round(
                required_tonnes,
                2
            ),
            "Allocated Tons": allocated_tonnes,
            "Remaining Tons": remaining_tonnes,
            "Excess Tons": excess_tonnes,
            "Planned Planting Date":
                planned_date.strftime("%Y-%m-%d")
                if not pd.isna(planned_date)
                else "",
            "Priority": requirement.get(
                "Priority",
                ""
            ),
            "Reason": requirement.get(
                "Reason",
                ""
            ),
            "Approved": requirement.get(
                "Approved",
                ""
            ),
            "Allocation Status":
                allocation_status,
            "Allocations":
                allocations,
            "Allocation Count":
                len(allocations)
        })

    return records


def get_seedcane_allocation_summary(register):
    """
    KPI summary for the Seedcane Allocation Register.
    """

    if not register:
        return {
            "destinations": 0,
            "hectares": 0,
            "required_tons": 0,
            "allocated_tons": 0,
            "remaining_tons": 0,
            "fully_allocated": 0,
            "partially_allocated": 0,
            "not_allocated": 0,
            "over_allocated": 0
        }

    return {
        "destinations": len(register),

        "hectares": round(
            sum(
                row["Hectares"]
                for row in register
            ),
            2
        ),

        "required_tons": round(
            sum(
                row["Required Tons"]
                for row in register
            ),
            2
        ),

        "allocated_tons": round(
            sum(
                row["Allocated Tons"]
                for row in register
            ),
            2
        ),

        "remaining_tons": round(
            sum(
                row["Remaining Tons"]
                for row in register
            ),
            2
        ),

        "fully_allocated": sum(
            1 for row in register
            if row["Allocation Status"]
            == "Fully Allocated"
        ),

        "partially_allocated": sum(
            1 for row in register
            if row["Allocation Status"]
            == "Partially Allocated"
        ),

        "not_allocated": sum(
            1 for row in register
            if row["Allocation Status"]
            == "Not Allocated"
        ),

        "over_allocated": sum(
            1 for row in register
            if row["Allocation Status"]
            == "Over Allocated"
        )
    }

# ============================================================
# SEEDCANE CUTTING
# ============================================================

def load_seedcane_cutting():
    """
    Load the actual daily seedcane cutting register.
    """

    columns = [
        "Cutting ID",
        "Date",
        "Season",
        "Use Type",
        "Source Field",
        "Destination Field",
        "Destination Subfield",
        "Main Field",
        "Estate",
        "Variety",
        "Bundles Cut",
        "Estimated Tons",
        "Status",
        "Notes"
    ]

    if not os.path.exists(SEEDCANE_CUTTING_FILE):
        return pd.DataFrame(columns=columns)

    try:
        df = pd.read_excel(
            SEEDCANE_CUTTING_FILE
        )

        for column in columns:
            if column not in df.columns:
                df[column] = ""

        # Existing cutting records were New Planting
        # before Use Type was introduced.
        df["Use Type"] = (
            df["Use Type"]
            .astype(str)
            .str.strip()
        )

        df.loc[
            df["Use Type"].isin(["", "nan", "None"]),
            "Use Type"
        ] = "New Planting"

        return df[columns]

    except Exception as exc:

        print(
            f"ERROR loading seedcane cutting file: {exc}"
        )

        return pd.DataFrame(columns=columns)


def generate_cutting_id():
    """
    Generate sequential cutting IDs.

    Example:
        SCC-0001
        SCC-0002
        SCC-0003
    """

    df = load_seedcane_cutting()

    if df.empty:
        return "SCC-0001"

    numbers = []

    for value in df["Cutting ID"].astype(str):

        value = value.strip().upper()

        if value.startswith("SCC-"):

            try:

                number = int(
                    value.replace(
                        "SCC-",
                        ""
                    )
                )

                numbers.append(number)

            except ValueError:
                continue

    next_number = max(
        numbers,
        default=0
    ) + 1

    return f"SCC-{next_number:04d}"


def get_cutting_allocated_tonnes(
    source_field,
    destination_field,
    season
):
    """
    Get planned tonnes allocated from a specific
    source field to a specific destination.
    """

    df = load_seedcane_allocations()

    if df.empty:
        return 0.0

    df["Season"] = (
        df["Season"]
        .astype(str)
        .str.strip()
    )

    df["Source Field"] = (
        df["Source Field"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Destination Field"] = (
        df["Destination Field"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    filtered = df[
        (df["Season"] == str(season).strip())
        &
        (
            df["Source Field"]
            == str(source_field).strip().upper()
        )
        &
        (
            df["Destination Field"]
            == str(destination_field).strip().upper()
        )
        &
        (
            df["Status"]
            .astype(str)
            .str.strip()
            .str.upper()
            != "CANCELLED"
        )
    ]

    if filtered.empty:
        return 0.0

    return round(
        pd.to_numeric(
            filtered["Planned Tonnes"],
            errors="coerce"
        ).fillna(0).sum(),
        2
    )

def get_cutting_recorded_tonnes(
        source_field,
        destination_field,
        season,
        use_type="New Planting"
):
    """
    Get estimated tonnes already cut against a
    specific source → destination allocation.

    Cutting is calculated from bundles × 3 tonnes.
    """

    df = load_seedcane_cutting()

    if df.empty:
        return 0.0

    df["Season"] = (
        df["Season"]
        .astype(str)
        .str.strip()
    )

    df["Source Field"] = (
        df["Source Field"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Destination Field"] = (
        df["Destination Field"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Use Type"] = (
        df["Use Type"]
        .astype(str)
        .str.strip()
    )

    df.loc[
        df["Use Type"].isin(["", "nan", "None"]),
        "Use Type"
    ] = "New Planting"

    filtered = df[
        (df["Season"] == str(season).strip())
        &
        (
                df["Source Field"]
                == str(source_field).strip().upper()
        )
        &
        (
                df["Destination Field"]
                == str(destination_field).strip().upper()
        )
        &
        (
                df["Use Type"].str.upper()
                == str(use_type).strip().upper()
        )
        &
        (
                df["Status"]
                .astype(str)
                .str.strip()
                .str.upper()
                != "CANCELLED"
        )
    ]

    if filtered.empty:
        return 0.0

    return round(
        pd.to_numeric(
            filtered["Estimated Tons"],
            errors="coerce"
        ).fillna(0).sum(),
        2
    )


def get_cutting_balance(
    source_field,
    destination_field,
    season
):
    """
    Compare planned allocation against actual
    seedcane cutting.

    Returns:

        Planned
        Already Cut
        Remaining
    """

    planned = get_cutting_allocated_tonnes(
        source_field,
        destination_field,
        season
    )

    already_cut = get_cutting_recorded_tonnes(
        source_field,
        destination_field,
        season
    )

    remaining = max(
        planned - already_cut,
        0
    )

    return {
        "Planned Tons": round(
            planned,
            2
        ),
        "Cut Tons": round(
            already_cut,
            2
        ),
        "Remaining Tons": round(
            remaining,
            2
        )
    }


def save_seedcane_cutting(
    date,
    season,
    source_field,
    destination_field,
    destination_subfield,
    use_type,
    bundles,
    notes=""
):
    use_type = str(use_type or "New Planting").strip()
    season = clean_season(season)

    # ------------------------------------------------------------
    # VALIDATE USE TYPE
    # ------------------------------------------------------------

    if use_type not in ["New Planting", "Gap Filling"]:
        return {
            "success": False,
            "message": "Invalid seedcane use type."
        }

    # ------------------------------------------------------------
    # BASIC VALIDATION
    # ------------------------------------------------------------

    if not source_field:
        return {
            "success": False,
            "message": "Please select a source field."
        }

    if not destination_field:
        return {
            "success": False,
            "message": "Please select a destination main field."
        }

    if not destination_subfield:
        return {
            "success": False,
            "message": "Please select a receiving sub-field."
        }

    # ------------------------------------------------------------
    # NORMALISE FIELD VALUES
    # ------------------------------------------------------------

    source_field = clean_field(source_field)
    destination_field = clean_field(destination_field)
    destination_subfield = clean_field(destination_subfield)

    # ------------------------------------------------------------
    # VALIDATE BUNDLES
    # ------------------------------------------------------------

    try:
        bundles = float(bundles)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "Bundles cut must be a valid number."
        }

    if bundles <= 0:
        return {
            "success": False,
            "message": "Bundles cut must be greater than zero."
        }

    # ------------------------------------------------------------
    # ESTIMATED TONNES
    #
    # DCGL operational estimate:
    # 1 bundle = approximately 3 tonnes
    # ------------------------------------------------------------

    estimated_tons = bundles * 3

    # ------------------------------------------------------------
    # SOURCE VALIDATION
    #
    # get_seedcane_source_candidates() returns:
    #
    # [
    #     {
    #         "Field": "...",
    #         "Main Field": "...",
    #         "Estate": "...",
    #         "Variety": "...",
    #         "Suitability": "...",
    #         ...
    #     },
    #     ...
    # ]
    #
    # Therefore we search the LIST of dictionaries.
    # ------------------------------------------------------------

    source_candidates = get_seedcane_source_candidates(
        season=season
    )

    source_match = next(
        (
            row
            for row in source_candidates
            if clean_field(row.get("Field", "")) == source_field
        ),
        None
    )

    # ------------------------------------------------------------
    # SOURCE NOT FOUND
    # ------------------------------------------------------------

    if source_match is None:
        return {
            "success": False,
            "message": (
                f"Source field {source_field} is not a valid "
                f"seedcane source for season {season}."
            )
        }

    # ------------------------------------------------------------
    # CHECK SOURCE SUITABILITY
    # ------------------------------------------------------------

    suitability = str(
        source_match.get("Suitability", "")
    ).strip()

    if suitability != "Suitable":
        return {
            "success": False,
            "message": (
                f"Source field {source_field} is not currently "
                f"suitable for seedcane. "
                f"Status: {suitability or 'Unknown'}."
            )
        }

    # ------------------------------------------------------------
    # NEW PLANTING
    #
    # New Planting must have a planned seedcane allocation.
    # ------------------------------------------------------------

    if use_type == "New Planting":

        planned = get_cutting_allocated_tonnes(
            source_field,
            destination_field,
            season
        )

        if planned <= 0:
            return {
                "success": False,
                "message": (
                    f"No seedcane allocation exists from "
                    f"{source_field} to {destination_field} "
                    f"for {season}."
                )
            }

        already_cut = get_cutting_recorded_tonnes(
            source_field,
            destination_field,
            season,
            "New Planting"
        )

        remaining = max(
            planned - already_cut,
            0
        )

        if estimated_tons > remaining:
            return {
                "success": False,
                "message": (
                    f"Cutting exceeds the remaining New Planting "
                    f"allocation. "
                    f"Remaining: {remaining:.2f} tonnes."
                )
            }

    # ------------------------------------------------------------
    # GAP FILLING
    #
    # Gap Filling does NOT require a planned allocation.
    # The operational field requirement determines the quantity.
    # ------------------------------------------------------------

    elif use_type == "Gap Filling":

        pass

    # ------------------------------------------------------------
    # LOAD EXISTING CUTTING REGISTER
    # ------------------------------------------------------------

    df = load_seedcane_cutting()

    # ------------------------------------------------------------
    # ENSURE REQUIRED COLUMNS EXIST
    # ------------------------------------------------------------

    required_columns = [
        "Cutting ID",
        "Date",
        "Season",
        "Source Field",
        "Destination Field",
        "Destination Subfield",
        "Main Field",
        "Estate",
        "Variety",
        "Use Type",
        "Bundles Cut",
        "Estimated Tons",
        "Status",
        "Notes"
    ]

    for column in required_columns:
        if column not in df.columns:
            df[column] = ""

    # Keep the register in the expected column order.
    df = df[required_columns]

    # ------------------------------------------------------------
    # GENERATE CUTTING ID
    # ------------------------------------------------------------

    cutting_id = generate_cutting_id()

    # ------------------------------------------------------------
    # SOURCE INFORMATION
    # ------------------------------------------------------------

    main_field = source_match.get(
        "Main Field",
        ""
    )

    estate = source_match.get(
        "Estate",
        ""
    )

    variety = source_match.get(
        "Variety",
        ""
    )

    # ------------------------------------------------------------
    # CREATE NEW CUTTING RECORD
    # ------------------------------------------------------------

    new_record = {
        "Cutting ID": cutting_id,
        "Date": date,
        "Season": season,
        "Source Field": source_field,
        "Destination Field": destination_field,
        "Destination Subfield": destination_subfield,
        "Main Field": main_field,
        "Estate": estate,
        "Variety": variety,
        "Use Type": use_type,
        "Bundles Cut": bundles,
        "Estimated Tons": estimated_tons,
        "Status": "Recorded",
        "Notes": notes
    }

    # ------------------------------------------------------------
    # APPEND RECORD
    # ------------------------------------------------------------

    df = pd.concat(
        [
            df,
            pd.DataFrame([new_record])
        ],
        ignore_index=True
    )

    # ------------------------------------------------------------
    # SAVE DIRECTLY TO EXCEL
    #
    # IMPORTANT:
    # Do NOT call save_seedcane_cutting(df) here because this
    # function itself is named save_seedcane_cutting().
    # ------------------------------------------------------------

    cutting_file = os.path.join(
        DATA_DIR,
        "seedcane_cutting.xlsx"
    )

    try:

        df.to_excel(
            cutting_file,
            index=False
        )

    except Exception as e:

        return {
            "success": False,
            "message": (
                f"Unable to save seedcane cutting record: {e}"
            )
        }

    # ------------------------------------------------------------
    # SUCCESS
    # ------------------------------------------------------------

    return {
        "success": True,
        "message": (
            f"Seedcane cutting recorded successfully "
            f"({use_type})."
        ),
        "cutting_id": cutting_id
    }


def get_seedcane_cutting_register(
    season
):
    """
    Return cutting records for the selected season.
    """

    df = load_seedcane_cutting()

    if df.empty:
        return []

    df["Season"] = (
        df["Season"]
        .astype(str)
        .str.strip()
    )

    filtered = df[
        df["Season"] == str(season).strip()
    ].copy()

    if filtered.empty:
        return []

    filtered["Date"] = pd.to_datetime(
        filtered["Date"],
        errors="coerce"
    )

    filtered = filtered.sort_values(
        "Date",
        ascending=False
    )

    records = []

    for _, row in filtered.iterrows():

        records.append({
            "Cutting ID": row.get(
                "Cutting ID",
                ""
            ),
            "Date": (
                row["Date"].strftime(
                    "%Y-%m-%d"
                )
                if not pd.isna(row["Date"])
                else ""
            ),
            "Use Type": row.get(
                "Use Type",
                "New Planting"
            ),
            "Source Field": row.get(
                "Source Field",
                ""
            ),
            "Destination Field": row.get(
                "Destination Field",
                ""
            ),
            "Destination Subfield": row.get(
                "Destination Subfield",
                ""
            ),
            "Main Field": row.get(
                "Main Field",
                ""
            ),
            "Estate": row.get(
                "Estate",
                ""
            ),
            "Variety": row.get(
                "Variety",
                ""
            ),
            "Bundles Cut": float(
                pd.to_numeric(
                    row.get(
                        "Bundles Cut",
                        0
                    ),
                    errors="coerce"
                ) or 0
            ),
            "Estimated Tons": float(
                pd.to_numeric(
                    row.get(
                        "Estimated Tons",
                        0
                    ),
                    errors="coerce"
                ) or 0
            ),
            "Status": row.get(
                "Status",
                ""
            ),
            "Notes": row.get(
                "Notes",
                ""
            )
        })

    return records


def get_seedcane_cutting_summary(
    season
):
    """
    Summary KPIs for actual seedcane cutting.
    """

    records = get_seedcane_cutting_register(
        season
    )

    if not records:

        return {
            "records": 0,
            "bundles": 0,
            "estimated_tons": 0
        }

    return {
        "records": len(records),

        "bundles": round(
            sum(
                record["Bundles Cut"]
                for record in records
            ),
            2
        ),

        "estimated_tons": round(
            sum(
                record["Estimated Tons"]
                for record in records
            ),
            2
        )
    }

def get_destination_subfields(destination_field, season):
    """
    Return registered subfields belonging to a main destination field.

    Example:

        Destination Field: DG22000

        Returns:
            DG22001
            DG22002
            DG22003
    """

    if not os.path.exists(REGISTERED_FIELDS_FILE):
        return []

    destination_field = (
        str(destination_field)
        .strip()
        .upper()
    )

    season = str(season).strip()

    try:

        df = pd.read_excel(
            REGISTERED_FIELDS_FILE
        )

        required_columns = {
            "Main Field",
            "Field",
            "Hectares",
            "Season"
        }

        if not required_columns.issubset(
            df.columns
        ):
            return []

        df["Main Field"] = (
            df["Main Field"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        df["Field"] = (
            df["Field"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        df["Season"] = (
            df["Season"]
            .astype(str)
            .str.strip()
        )

        df["Hectares"] = pd.to_numeric(
            df["Hectares"],
            errors="coerce"
        ).fillna(0)

        filtered = df[
            (df["Main Field"] == destination_field)
            &
            (df["Season"] == season)
        ].copy()

        if filtered.empty:
            return []

        records = []

        for _, row in filtered.iterrows():

            subfield = str(
                row.get("Field", "")
            ).strip().upper()

            if not subfield:
                continue

            records.append({
                "Field": subfield,
                "Hectares": round(
                    float(
                        row.get(
                            "Hectares",
                            0
                        )
                    ),
                    2
                )
            })

        return records

    except Exception as exc:

        print(
            f"ERROR loading destination subfields "
            f"for {destination_field}: {exc}"
        )

        return []

# ============================================================
# SEEDCANE HAULAGE / WEIGHBRIDGE
# ============================================================

SEEDCANE_HAULAGE_COLUMNS = [
    "Haulage ID",
    "Date",
    "Season",
    "Cutting ID",
    "Source Field",
    "Destination Field",
    "Destination Subfield",
    "Main Field",
    "Estate",
    "Variety",
    "Bundles Hauled",
    "Estimated Tons",
    "Actual Tons",
    "Vehicle",
    "Weighbridge Ticket",
    "Status",
    "Notes"
]


def load_seedcane_haulage():
    """
    Load the Seedcane Haulage / Weighbridge register.
    """

    if not os.path.exists(SEEDCANE_HAULAGE_FILE):
        return pd.DataFrame(columns=SEEDCANE_HAULAGE_COLUMNS)

    try:
        df = pd.read_excel(SEEDCANE_HAULAGE_FILE)

        for column in SEEDCANE_HAULAGE_COLUMNS:
            if column not in df.columns:
                df[column] = ""

        return df[SEEDCANE_HAULAGE_COLUMNS]

    except Exception:
        return pd.DataFrame(columns=SEEDCANE_HAULAGE_COLUMNS)


def generate_haulage_id():
    """
    Generate the next Seedcane Haulage ID.
    """

    df = load_seedcane_haulage()

    if df.empty:
        return "SC-H-00001"

    numbers = (
        df["Haulage ID"]
        .astype(str)
        .str.extract(r"(\d+)$")[0]
    )

    numbers = pd.to_numeric(
        numbers,
        errors="coerce"
    ).dropna()

    if numbers.empty:
        next_number = 1
    else:
        next_number = int(numbers.max()) + 1

    return f"SC-H-{next_number:05d}"

def get_cutting_record(cutting_id):
    """
    Return one Seedcane Cutting record by Cutting ID.
    """

    df = load_seedcane_cutting()

    if df.empty:
        return None

    cutting_id = str(cutting_id).strip().upper()

    matches = df[
        df["Cutting ID"]
        .astype(str)
        .str.strip()
        .str.upper()
        == cutting_id
    ]

    if matches.empty:
        return None

    return matches.iloc[0].to_dict()

def get_hauled_tonnes(cutting_id):
    """
    Return actual tonnes already hauled for a Cutting ID.
    """

    df = load_seedcane_haulage()

    if df.empty:
        return 0.0

    cutting_id = str(cutting_id).strip().upper()

    filtered = df[
        df["Cutting ID"]
        .astype(str)
        .str.strip()
        .str.upper()
        == cutting_id
    ]

    if filtered.empty:
        return 0.0

    return float(
        pd.to_numeric(
            filtered["Actual Tons"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )

def get_cutting_remaining_tonnes(cutting_id):
    """
    Calculate the estimated tonnes remaining to be hauled
    from a cutting record.

    The actual weighbridge quantity is authoritative once hauled.
    """

    cutting = get_cutting_record(cutting_id)

    if not cutting:
        return 0.0

    estimated_tons = float(
        pd.to_numeric(
            cutting.get("Estimated Tons", 0),
            errors="coerce"
        ) or 0
    )

    hauled_tons = get_hauled_tonnes(cutting_id)

    return max(
        estimated_tons - hauled_tons,
        0.0
    )


def get_seedcane_haulage_register(season=None):
    """
    Return Seedcane Haulage records for the selected season.
    """

    df = load_seedcane_haulage()

    if df.empty:
        return df

    if season:
        season = str(season).strip()

        df = df[
            df["Season"]
            .astype(str)
            .str.strip()
            == season
        ]

    return df.sort_values(
        by=["Date", "Haulage ID"],
        ascending=[False, False]
    ).reset_index(drop=True)

# ============================================================
# SEEDCANE GAP FILLING
# ============================================================

def load_seedcane_gapfilling():
    """
    Load the actual Gap Filling operation register.

    This is an ACTUAL USE register.

    It does NOT contain planned seedcane requirements.
    """

    columns = [
        "Gap Filling ID",
        "Date",
        "Season",
        "Cutting ID",
        "Source Field",
        "Destination Field",
        "Destination Subfield",
        "Bundles Used",
        "Estimated Tons",
        "Capitao",
        "Seedcane Choppers",
        "Planters",
        "Mandays",
        "Status",
        "Notes"
    ]

    if not os.path.exists(
        SEEDCANE_GAPFILLING_FILE
    ):
        return pd.DataFrame(
            columns=columns
        )

    try:

        df = pd.read_excel(
            SEEDCANE_GAPFILLING_FILE
        )

        for column in columns:

            if column not in df.columns:
                df[column] = ""

        return df[columns]

    except Exception as exc:

        print(
            "ERROR loading seedcane gap filling file:",
            exc
        )

        return pd.DataFrame(
            columns=columns
        )


def generate_gapfilling_id():
    """
    Generate sequential Gap Filling IDs.

    Example:

        SGF-0001
        SGF-0002
        SGF-0003
    """

    df = load_seedcane_gapfilling()

    if df.empty:
        return "SGF-0001"

    numbers = []

    for value in df["Gap Filling ID"].astype(str):

        value = (
            value
            .strip()
            .upper()
        )

        if value.startswith("SGF-"):

            try:

                number = int(
                    value.replace(
                        "SGF-",
                        ""
                    )
                )

                numbers.append(
                    number
                )

            except ValueError:

                continue

    next_number = (
        max(
            numbers,
            default=0
        )
        + 1
    )

    return (
        f"SGF-{next_number:04d}"
    )


def get_gapfilling_cuttings(season):
    """
    Return Gap Filling cutting records for
    the selected season.

    Includes:

        Bundles Cut
        Bundles Used
        Bundles Remaining
        Estimated Tons Cut
        Estimated Tons Used
        Estimated Tons Remaining
        Usage Status
    """

    df = load_seedcane_cutting()

    if df.empty:
        return []

    # --------------------------------------------------------
    # BACKWARD COMPATIBILITY
    # --------------------------------------------------------

    if "Use Type" not in df.columns:

        df["Use Type"] = "New Planting"

    df["Use Type"] = (
        df["Use Type"]
        .fillna("New Planting")
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # SEASON
    # --------------------------------------------------------

    df["Season"] = (
        df["Season"]
        .astype(str)
        .str.strip()
    )

    filtered = df[
        (df["Season"] == str(season).strip())
        &
        (
            df["Use Type"]
            .str.lower()
            == "gap filling"
        )
    ].copy()

    if filtered.empty:
        return []

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    filtered["Date"] = pd.to_datetime(
        filtered["Date"],
        errors="coerce"
    )

    filtered = (
        filtered
        .sort_values(
            "Date",
            ascending=False
        )
    )

    records = []

    # --------------------------------------------------------
    # BUILD CUTTING BALANCE
    # --------------------------------------------------------

    for _, row in filtered.iterrows():

        cutting_id = str(
            row.get(
                "Cutting ID",
                ""
            )
        ).strip().upper()

        bundles_cut = float(
            pd.to_numeric(
                row.get(
                    "Bundles Cut",
                    0
                ),
                errors="coerce"
            ) or 0
        )

        estimated_tons_cut = float(
            pd.to_numeric(
                row.get(
                    "Estimated Tons",
                    0
                ),
                errors="coerce"
            ) or 0
        )

        # ----------------------------------------------------
        # BUNDLES ALREADY USED
        # ----------------------------------------------------

        bundles_used = (
            get_gapfilling_used_bundles(
                cutting_id,
                season
            )
        )

        bundles_remaining = max(
            bundles_cut - bundles_used,
            0
        )

        # ----------------------------------------------------
        # TONNES
        # ----------------------------------------------------

        estimated_tons_used = round(
            bundles_used
            * SEEDCANE_BUNDLE_TONS,
            2
        )

        estimated_tons_remaining = round(
            bundles_remaining
            * SEEDCANE_BUNDLE_TONS,
            2
        )

        # ----------------------------------------------------
        # USAGE STATUS
        # ----------------------------------------------------

        if bundles_used <= 0:

            usage_status = "Unused"

        elif bundles_remaining <= 0:

            usage_status = "Fully Used"

        else:

            usage_status = "Partially Used"

        # ----------------------------------------------------
        # RECORD
        # ----------------------------------------------------

        records.append({

            "Cutting ID":
                cutting_id,

            "Date": (
                row["Date"].strftime(
                    "%Y-%m-%d"
                )
                if not pd.isna(
                    row["Date"]
                )
                else ""
            ),

            "Season":
                row.get(
                    "Season",
                    ""
                ),

            "Source Field":
                row.get(
                    "Source Field",
                    ""
                ),

            "Destination Field":
                row.get(
                    "Destination Field",
                    ""
                ),

            "Destination Subfield":
                row.get(
                    "Destination Subfield",
                    ""
                ),

            "Bundles Cut":
                round(
                    bundles_cut,
                    2
                ),

            "Bundles Used":
                round(
                    bundles_used,
                    2
                ),

            "Bundles Remaining":
                round(
                    bundles_remaining,
                    2
                ),

            "Estimated Tons Cut":
                round(
                    estimated_tons_cut,
                    2
                ),

            "Estimated Tons Used":
                estimated_tons_used,

            "Estimated Tons Remaining":
                estimated_tons_remaining,

            "Usage Status":
                usage_status,

            "Status":
                row.get(
                    "Status",
                    ""
                )

        })

    return records


def get_gapfilling_used_bundles(
    cutting_id,
    season
):
    """
    Return the number of bundles already used
    from a particular Gap Filling cutting.
    """

    df = load_seedcane_gapfilling()

    if df.empty:
        return 0.0

    df["Season"] = (
        df["Season"]
        .astype(str)
        .str.strip()
    )

    df["Cutting ID"] = (
        df["Cutting ID"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    filtered = df[
        (df["Season"] == str(season).strip())
        &
        (
            df["Cutting ID"]
            == str(cutting_id)
            .strip()
            .upper()
        )
        &
        (
            df["Status"]
            .astype(str)
            .str.strip()
            .str.upper()
            != "CANCELLED"
        )
    ]

    if filtered.empty:
        return 0.0

    return round(
        pd.to_numeric(
            filtered["Bundles Used"],
            errors="coerce"
        )
        .fillna(0)
        .sum(),
        2
    )


def save_seedcane_gapfilling(
    date,
    season,
    cutting_id,
    destination_subfield,
    bundles_used,
    capitao,
    seedcane_choppers,
    planters,
    mandays,
    notes=""
):
    """
    Save one actual Gap Filling operation.

    Gap Filling has:

        - no planned tonnage requirement
        - no allocation requirement
        - actual bundles used
        - field labour record

    Estimated Tons = Bundles Used × 3 tonnes.
    """

    # --------------------------------------------------------
    # CLEAN INPUT
    # --------------------------------------------------------

    season = str(
        season
    ).strip()

    cutting_id = str(
        cutting_id
    ).strip().upper()

    destination_subfield = str(
        destination_subfield
    ).strip().upper()

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    operation_date = pd.to_datetime(
        date,
        errors="coerce"
    )

    if pd.isna(operation_date):

        return {
            "success": False,
            "message": (
                "Please provide a valid "
                "Gap Filling date."
            ),
            "saved": None
        }

    # --------------------------------------------------------
    # FIND CUTTING
    # --------------------------------------------------------

    cutting_df = load_seedcane_cutting()

    if cutting_df.empty:

        return {
            "success": False,
            "message": (
                "No seedcane cutting records "
                "are available."
            ),
            "saved": None
        }

    if "Use Type" not in cutting_df.columns:

        cutting_df["Use Type"] = (
            "New Planting"
        )

    cutting_df["Use Type"] = (
        cutting_df["Use Type"]
        .fillna("New Planting")
        .astype(str)
        .str.strip()
    )

    cutting_df["Cutting ID"] = (
        cutting_df["Cutting ID"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    cutting = cutting_df[
        (
            cutting_df["Cutting ID"]
            == cutting_id
        )
        &
        (
            cutting_df["Season"]
            .astype(str)
            .str.strip()
            == season
        )
        &
        (
            cutting_df["Use Type"]
            .str.lower()
            == "gap filling"
        )
    ]

    if cutting.empty:

        return {
            "success": False,
            "message": (
                f"{cutting_id} is not a valid "
                f"Gap Filling cutting record "
                f"for season {season}."
            ),
            "saved": None
        }

    cutting_row = (
        cutting.iloc[0]
    )

    # --------------------------------------------------------
    # DESTINATION SUBFIELD
    # --------------------------------------------------------

    destination_field = str(
        cutting_row.get(
            "Destination Field",
            ""
        )
    ).strip().upper()

    valid_subfields = {
        str(item["Field"])
        .strip()
        .upper()
        for item in get_destination_subfields(
            destination_field,
            season
        )
    }

    if destination_subfield not in valid_subfields:

        return {
            "success": False,
            "message": (
                f"{destination_subfield} is not a "
                f"registered sub-field of "
                f"{destination_field} for "
                f"season {season}."
            ),
            "saved": None
        }

    # --------------------------------------------------------
    # BUNDLES USED
    # --------------------------------------------------------

    try:

        bundles_used = float(
            bundles_used
        )

    except (
        TypeError,
        ValueError
    ):

        return {
            "success": False,
            "message": (
                "Bundles Used must be "
                "a valid number."
            ),
            "saved": None
        }

    if bundles_used <= 0:

        return {
            "success": False,
            "message": (
                "Bundles Used must be "
                "greater than zero."
            ),
            "saved": None
        }

    # --------------------------------------------------------
    # PREVENT USING MORE THAN THE CUTTING
    # --------------------------------------------------------

    bundles_cut = float(
        pd.to_numeric(
            cutting_row.get(
                "Bundles Cut",
                0
            ),
            errors="coerce"
        ) or 0
    )

    already_used = (
        get_gapfilling_used_bundles(
            cutting_id,
            season
        )
    )

    remaining_bundles = max(
        bundles_cut - already_used,
        0
    )

    if bundles_used > remaining_bundles:

        return {
            "success": False,
            "message": (
                f"This operation uses "
                f"{bundles_used:.2f} bundles, "
                f"but only "
                f"{remaining_bundles:.2f} bundles "
                f"remain from cutting "
                f"{cutting_id}."
            ),
            "saved": None
        }

    # --------------------------------------------------------
    # ESTIMATED TONNES
    # --------------------------------------------------------

    estimated_tons = round(
        bundles_used
        * SEEDCANE_BUNDLE_TONS,
        2
    )

    # --------------------------------------------------------
    # LABOUR
    # --------------------------------------------------------

    def positive_number(
        value,
        field_name
    ):

        try:

            number = float(
                value or 0
            )

        except (
            TypeError,
            ValueError
        ):

            raise ValueError(
                f"{field_name} must be "
                f"a valid number."
            )

        if number < 0:

            raise ValueError(
                f"{field_name} cannot "
                f"be negative."
            )

        return number

    try:

        capitao = positive_number(
            capitao,
            "Capitao"
        )

        seedcane_choppers = positive_number(
            seedcane_choppers,
            "Seedcane Choppers"
        )

        planters = positive_number(
            planters,
            "Planters"
        )

        mandays = positive_number(
            mandays,
            "Mandays"
        )

    except ValueError as exc:

        return {
            "success": False,
            "message": str(exc),
            "saved": None
        }

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    df = load_seedcane_gapfilling()

    gapfilling_id = (
        generate_gapfilling_id()
    )

    new_row = {

        "Gap Filling ID":
            gapfilling_id,

        "Date":
            operation_date.strftime(
                "%Y-%m-%d"
            ),

        "Season":
            season,

        "Cutting ID":
            cutting_id,

        "Source Field":
            str(
                cutting_row.get(
                    "Source Field",
                    ""
                )
            ).strip().upper(),

        "Destination Field":
            destination_field,

        "Destination Subfield":
            destination_subfield,

        "Bundles Used":
            round(
                bundles_used,
                2
            ),

        "Estimated Tons":
            estimated_tons,

        "Capitao":
            round(
                capitao,
                2
            ),

        "Seedcane Choppers":
            round(
                seedcane_choppers,
                2
            ),

        "Planters":
            round(
                planters,
                2
            ),

        "Mandays":
            round(
                mandays,
                2
            ),

        "Status":
            "Completed",

        "Notes":
            str(notes).strip()
    }

    new_df = pd.DataFrame(
        [new_row]
    )

    if df.empty:

        final_df = new_df

    else:

        final_df = pd.concat(
            [
                df,
                new_df
            ],
            ignore_index=True
        )

    os.makedirs(
        os.path.dirname(
            SEEDCANE_GAPFILLING_FILE
        ),
        exist_ok=True
    )

    final_df.to_excel(
        SEEDCANE_GAPFILLING_FILE,
        index=False
    )

    return {
        "success": True,
        "message": (
            f"Gap Filling record "
            f"{gapfilling_id} saved successfully."
        ),
        "saved": new_row
    }


def get_seedcane_gapfilling_register(
    season
):
    """
    Return Gap Filling records for the
    selected season.
    """

    df = load_seedcane_gapfilling()

    if df.empty:
        return []

    df["Season"] = (
        df["Season"]
        .astype(str)
        .str.strip()
    )

    filtered = df[
        df["Season"]
        == str(season).strip()
    ].copy()

    if filtered.empty:
        return []

    filtered["Date"] = pd.to_datetime(
        filtered["Date"],
        errors="coerce"
    )

    filtered = (
        filtered
        .sort_values(
            "Date",
            ascending=False
        )
    )

    records = []

    for _, row in filtered.iterrows():

        records.append({

            "Gap Filling ID":
                row.get(
                    "Gap Filling ID",
                    ""
                ),

            "Date": (
                row["Date"].strftime(
                    "%Y-%m-%d"
                )
                if not pd.isna(
                    row["Date"]
                )
                else ""
            ),

            "Season":
                row.get(
                    "Season",
                    ""
                ),

            "Cutting ID":
                row.get(
                    "Cutting ID",
                    ""
                ),

            "Source Field":
                row.get(
                    "Source Field",
                    ""
                ),

            "Destination Field":
                row.get(
                    "Destination Field",
                    ""
                ),

            "Destination Subfield":
                row.get(
                    "Destination Subfield",
                    ""
                ),

            "Bundles Used":
                float(
                    pd.to_numeric(
                        row.get(
                            "Bundles Used",
                            0
                        ),
                        errors="coerce"
                    ) or 0
                ),

            "Estimated Tons":
                float(
                    pd.to_numeric(
                        row.get(
                            "Estimated Tons",
                            0
                        ),
                        errors="coerce"
                    ) or 0
                ),

            "Capitao":
                float(
                    pd.to_numeric(
                        row.get(
                            "Capitao",
                            0
                        ),
                        errors="coerce"
                    ) or 0
                ),

            "Seedcane Choppers":
                float(
                    pd.to_numeric(
                        row.get(
                            "Seedcane Choppers",
                            0
                        ),
                        errors="coerce"
                    ) or 0
                ),

            "Planters":
                float(
                    pd.to_numeric(
                        row.get(
                            "Planters",
                            0
                        ),
                        errors="coerce"
                    ) or 0
                ),

            "Mandays":
                float(
                    pd.to_numeric(
                        row.get(
                            "Mandays",
                            0
                        ),
                        errors="coerce"
                    ) or 0
                ),

            "Status":
                row.get(
                    "Status",
                    ""
                ),

            "Notes":
                row.get(
                    "Notes",
                    ""
                )
        })

    return records

def get_seedcane_gapfilling_summary(season):
    """
    Return Gap Filling operational and labour
    summary for the selected season.
    """

    records = get_seedcane_gapfilling_register(
        season
    )

    if not records:

        return {
            "operations": 0,
            "bundles_used": 0,
            "estimated_tons": 0,
            "capitao": 0,
            "seedcane_choppers": 0,
            "planters": 0,
            "mandays": 0
        }

    return {

        "operations":
            len(records),

        "bundles_used":
            round(
                sum(
                    record.get(
                        "Bundles Used",
                        0
                    )
                    for record in records
                ),
                2
            ),

        "estimated_tons":
            round(
                sum(
                    record.get(
                        "Estimated Tons",
                        0
                    )
                    for record in records
                ),
                2
            ),

        "capitao":
            round(
                sum(
                    record.get(
                        "Capitao",
                        0
                    )
                    for record in records
                ),
                2
            ),

        "seedcane_choppers":
            round(
                sum(
                    record.get(
                        "Seedcane Choppers",
                        0
                    )
                    for record in records
                ),
                2
            ),

        "planters":
            round(
                sum(
                    record.get(
                        "Planters",
                        0
                    )
                    for record in records
                ),
                2
            ),

        "mandays":
            round(
                sum(
                    record.get(
                        "Mandays",
                        0
                    )
                    for record in records
                ),
                2
            )
    }

def get_seedcane_gapfilling_dashboard_summary(
    season,
    recent_limit=10
):
    """
    Build a compact management dashboard for Seedcane Gap Filling.

    The dashboard contains:
        - Overall gap filling KPIs
        - Seedcane cutting utilisation
        - Labour summary
        - Recent gap filling operations

    Detailed cutting and operation records are intentionally
    excluded from this summary.
    """

    gapfilling_summary = get_seedcane_gapfilling_summary(
        season
    )

    gapfilling_cuttings = get_gapfilling_cuttings(
        season
    )

    gapfilling_register = get_seedcane_gapfilling_register(
        season
    )

    def number(value):
        try:
            if value is None or value == "":
                return 0.0

            return float(value)

        except (ValueError, TypeError):
            return 0.0

    # ---------------------------------------------------------
    # CUTTING UTILISATION
    # ---------------------------------------------------------

    bundles_cut = 0.0
    bundles_used = 0.0
    bundles_remaining = 0.0

    fully_used = 0
    partially_used = 0
    unused = 0

    for cutting in gapfilling_cuttings:

        cut = number(
            cutting.get("Bundles Cut", 0)
        )

        used = number(
            cutting.get("Bundles Used", 0)
        )

        remaining_value = cutting.get(
            "Bundles Remaining"
        )

        if remaining_value in (
            None,
            "",
            "nan"
        ):
            remaining = max(
                0,
                cut - used
            )
        else:
            remaining = number(
                remaining_value
            )

        bundles_cut += cut
        bundles_used += used
        bundles_remaining += remaining

        # Determine utilisation status
        if cut <= 0 or used <= 0:
            unused += 1

        elif remaining <= 0:
            fully_used += 1

        else:
            partially_used += 1

    # ---------------------------------------------------------
    # UTILISATION PERCENTAGE
    # ---------------------------------------------------------

    if bundles_cut > 0:
        utilisation_percentage = (
            bundles_used / bundles_cut
        ) * 100
    else:
        utilisation_percentage = 0

    utilisation_percentage = min(
        100,
        max(0, utilisation_percentage)
    )

    # ---------------------------------------------------------
    # GAP FILLING KPIs
    # ---------------------------------------------------------

    operations = len(
        gapfilling_register
    )

    estimated_tons = 0.0
    mandays = 0.0

    for record in gapfilling_register:

        estimated_tons += number(
            record.get(
                "Estimated Tons",
                record.get(
                    "Estimated Seedcane (t)",
                    0
                )
            )
        )

        mandays += number(
            record.get(
                "Mandays",
                0
            )
        )

    # If the existing summary already provides these
    # figures, use them where available.

    if isinstance(
        gapfilling_summary,
        dict
    ):

        operations = number(
            gapfilling_summary.get(
                "operations",
                operations
            )
        )

        estimated_tons = number(
            gapfilling_summary.get(
                "estimated_tons",
                estimated_tons
            )
        )

        mandays = number(
            gapfilling_summary.get(
                "mandays",
                mandays
            )
        )

    # ---------------------------------------------------------
    # LABOUR
    # ---------------------------------------------------------

    labour = {
        "Capitao": 0,
        "Seedcane Choppers": 0,
        "Planters": 0,
        "Mandays": mandays
    }

    for record in gapfilling_register:

        labour["Capitao"] += number(
            record.get(
                "Capitao",
                record.get(
                    "Capitao Labour",
                    0
                )
            )
        )

        labour["Seedcane Choppers"] += number(
            record.get(
                "Seedcane Choppers",
                0
            )
        )

        labour["Planters"] += number(
            record.get(
                "Planters",
                0
            )
        )

    # ---------------------------------------------------------
    # RECENT OPERATIONS ONLY
    # ---------------------------------------------------------

    recent_operations = list(
        gapfilling_register
    )

    def sort_date(record):

        value = record.get(
            "Date",
            ""
        )

        try:
            return pd.to_datetime(
                value,
                errors="coerce"
            )

        except Exception:
            return pd.Timestamp.min

    recent_operations = sorted(
        recent_operations,
        key=sort_date,
        reverse=True
    )[:recent_limit]

    # ---------------------------------------------------------
    # RETURN DASHBOARD DATA
    # ---------------------------------------------------------

    return {

        "kpis": {
            "operations": int(
                operations
            ),

            "bundles_used": round(
                bundles_used,
                2
            ),

            "estimated_tons": round(
                estimated_tons,
                2
            ),

            "mandays": round(
                mandays,
                2
            )
        },

        "cutting_balance": {

            "cuttings": len(
                gapfilling_cuttings
            ),

            "bundles_cut": round(
                bundles_cut,
                2
            ),

            "bundles_used": round(
                bundles_used,
                2
            ),

            "bundles_remaining": round(
                bundles_remaining,
                2
            ),

            "utilisation_percentage": round(
                utilisation_percentage,
                1
            ),

            "fully_used": fully_used,

            "partially_used": partially_used,

            "unused": unused
        },

        "labour": labour,

        "recent_operations": recent_operations
    }

# ============================================================
# SEEDCANE HAULAGE
# ============================================================

HAULAGE_FILE = os.path.join(DATA_DIR, "seedcane_haulage.xlsx")

HAULAGE_COLUMNS = [
    "Haulage ID",
    "Date",
    "Season",
    "Cutting ID",
    "Use Type",
    "Source Field",
    "Destination Field",
    "Destination Subfield",
    "Vehicle",
    "Weighbridge Ticket",
    "Gross Weight",
    "Tare Weight",
    "Actual Tons",
    "Status",
    "Notes",
]


def ensure_seedcane_haulage_file():
    """
    Create the Seedcane Haulage Excel register if it does not exist.
    """

    if not os.path.exists(HAULAGE_FILE):

        df = pd.DataFrame(columns=HAULAGE_COLUMNS)

        df.to_excel(
            HAULAGE_FILE,
            index=False
        )

        return True

    return False


def load_seedcane_haulage():
    """
    Load the Seedcane Haulage register.

    Older/empty files are made compatible with the current
    haulage structure.
    """

    ensure_seedcane_haulage_file()

    try:
        df = pd.read_excel(HAULAGE_FILE)

    except Exception:
        df = pd.DataFrame(columns=HAULAGE_COLUMNS)

    # Ensure all expected columns exist
    for column in HAULAGE_COLUMNS:

        if column not in df.columns:
            df[column] = ""

    # Keep the standard column order
    df = df[HAULAGE_COLUMNS]

    return df


def generate_seedcane_haulage_id(df=None):
    """
    Generate the next Seedcane Haulage ID.

    Format:
        SC-HAUL-00001
        SC-HAUL-00002
        ...
    """

    if df is None:
        df = load_seedcane_haulage()

    if df.empty:
        return "SC-HAUL-00001"

    numbers = []

    for value in df["Haulage ID"].dropna():

        value = str(value).strip()

        if value.startswith("SC-HAUL-"):

            try:
                number = int(
                    value.replace("SC-HAUL-", "")
                )

                numbers.append(number)

            except ValueError:
                continue

    next_number = max(numbers, default=0) + 1

    return f"SC-HAUL-{next_number:05d}"


def get_seedcane_haulage_register(season=None):
    """
    Return the Seedcane Haulage register.

    If a season is supplied, only that season is returned.
    """

    df = load_seedcane_haulage()

    if season:
        df = df[
            df["Season"].astype(str).str.strip() == str(season).strip()
        ].copy()

    return df


def get_seedcane_cutting_for_haulage(cutting_id, season=None):
    """
    Retrieve an existing cutting record for haulage.

    The Cutting ID must already exist in the Seedcane Cutting
    register.
    """

    cutting_df = load_seedcane_cutting()

    if cutting_df.empty:
        return None

    cutting_id = str(cutting_id).strip()

    matches = cutting_df[
        cutting_df["Cutting ID"].astype(str).str.strip() == cutting_id
    ].copy()

    if season:
        matches = matches[
            matches["Season"].astype(str).str.strip()
            == str(season).strip()
        ]

    if matches.empty:
        return None

    return matches.iloc[0].to_dict()


def get_seedcane_haulage_tonnage(cutting_id, season=None):
    """
    Calculate actual tonnes already hauled for a Cutting ID.
    """

    df = load_seedcane_haulage()

    if df.empty:
        return 0.0

    df = df[
        df["Cutting ID"].astype(str).str.strip()
        == str(cutting_id).strip()
    ]

    if season:
        df = df[
            df["Season"].astype(str).str.strip()
            == str(season).strip()
        ]

    if df.empty:
        return 0.0

    return pd.to_numeric(
        df["Actual Tons"],
        errors="coerce"
    ).fillna(0).sum()


def get_seedcane_haulage_balance(cutting_id, season=None):
    """
    Return the relationship between estimated tonnes cut
    and actual tonnes hauled for a Cutting ID.

    Estimated tonnes come from the cutting register.
    Actual tonnes come from the haulage register.
    """

    cutting = get_seedcane_cutting_for_haulage(
        cutting_id,
        season=season
    )

    if not cutting:
        return None

    estimated_tons = pd.to_numeric(
        cutting.get("Estimated Tons", 0),
        errors="coerce"
    )

    if pd.isna(estimated_tons):
        estimated_tons = 0.0

    actual_tons = get_seedcane_haulage_tonnage(
        cutting_id,
        season=season
    )

    remaining_estimated = max(
        float(estimated_tons) - float(actual_tons),
        0.0
    )

    return {
        "cutting_id": cutting_id,
        "estimated_tons": round(float(estimated_tons), 3),
        "actual_tons_hauled": round(float(actual_tons), 3),
        "remaining_estimated_tons": round(
            remaining_estimated,
            3
        ),
    }

def save_seedcane_haulage(
    date,
    cutting_id,
    vehicle,
    weighbridge_ticket,
    gross_weight,
    tare_weight,
    notes="",
    season=None
):
    """
    Save one Seedcane Haulage record.

    The Cutting ID determines:
        - Season
        - Use Type
        - Source Field
        - Destination Field
        - Destination Subfield

    Actual Tons are calculated as:

        Gross Weight - Tare Weight
    """

    # --------------------------------------------------------
    # Validate Cutting ID
    # --------------------------------------------------------

    cutting = get_seedcane_cutting_for_haulage(
        cutting_id,
        season=season
    )

    if not cutting:
        raise ValueError(
            f"Cutting ID '{cutting_id}' was not found."
        )

    # --------------------------------------------------------
    # VALIDATE HAULAGE DATE AGAINST CUTTING DATE
    # --------------------------------------------------------

    haulage_date = pd.to_datetime(
        date,
        errors="coerce"
    )

    if pd.isna(haulage_date):
        raise ValueError(
            "Please provide a valid haulage date."
        )

    cutting_date = pd.to_datetime(
        cutting.get("Date"),
        errors="coerce"
    )

    if not pd.isna(cutting_date):

        if haulage_date < cutting_date:

            raise ValueError(
                "Haulage date cannot be earlier "
                "than the cutting date."
            )

    # --------------------------------------------------------
    # Validate weights
    # --------------------------------------------------------

    try:
        gross = float(gross_weight)
    except (TypeError, ValueError):
        raise ValueError(
            "Gross weight must be a valid number."
        )

    try:
        tare = float(tare_weight)
    except (TypeError, ValueError):
        raise ValueError(
            "Tare weight must be a valid number."
        )

    if gross <= 0:
        raise ValueError(
            "Gross weight must be greater than zero."
        )

    if tare < 0:
        raise ValueError(
            "Tare weight cannot be negative."
        )

    actual_tons = gross - tare

    if actual_tons <= 0:
        raise ValueError(
            "Actual tons must be greater than zero. "
            "Check Gross Weight and Tare Weight."
        )

    # --------------------------------------------------------
    # Season
    # --------------------------------------------------------

    cutting_season = str(
        cutting.get("Season", "")
    ).strip()

    if not cutting_season:
        cutting_season = season or ""

    # --------------------------------------------------------
    # Load existing register
    # --------------------------------------------------------

    df = load_seedcane_haulage()

    haulage_id = generate_seedcane_haulage_id(df)

    # --------------------------------------------------------
    # Create record
    # --------------------------------------------------------

    record = {
        "Haulage ID": haulage_id,
        "Date": date,
        "Season": cutting_season,

        "Cutting ID": str(
            cutting.get("Cutting ID", "")
        ).strip(),

        "Use Type": str(
            cutting.get("Use Type", "New Planting")
        ).strip(),

        "Source Field": str(
            cutting.get("Source Field", "")
        ).strip(),

        "Destination Field": str(
            cutting.get("Destination Field", "")
        ).strip(),

        "Destination Subfield": str(
            cutting.get("Destination Subfield", "")
        ).strip(),

        "Vehicle": str(vehicle).strip(),

        "Weighbridge Ticket": str(
            weighbridge_ticket
        ).strip(),

        "Gross Weight": round(gross, 3),

        "Tare Weight": round(tare, 3),

        "Actual Tons": round(actual_tons, 3),

        "Status": "Recorded",

        "Notes": str(notes).strip(),
    }

    # --------------------------------------------------------
    # Append
    # --------------------------------------------------------

    df = pd.concat(
        [
            df,
            pd.DataFrame([record])
        ],
        ignore_index=True
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    df.to_excel(
        HAULAGE_FILE,
        index=False
    )

    return record

# ============================================================
# SEEDCANE HAULAGE RECONCILIATION
# OPTIMISED VERSION
# ============================================================

def get_seedcane_haulage_reconciliation(
    season=None,
    use_type=None
):
    """
    Reconcile Seedcane Cutting against actual Haulage.

    IMPORTANT:
    Excel files are loaded only once.

    New Planting:
        Estimated cutting
        Actual hauled
        Remaining estimated
        Planned allocation
        Allocation balance

    Gap Filling:
        Estimated cutting
        Actual hauled
        Remaining estimated

        No planned tonnage is assumed for Gap Filling.
    """

    # ========================================================
    # LOAD FILES ONCE
    # ========================================================

    cutting_df = load_seedcane_cutting()
    haulage_df = load_seedcane_haulage()
    allocation_df = load_seedcane_allocations()

    if cutting_df.empty:
        return []

    # ========================================================
    # NORMALISE CUTTING DATA
    # ========================================================

    cutting_df["Season"] = (
        cutting_df["Season"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    if season:
        season_clean = str(season).strip()

        cutting_df = cutting_df[
            cutting_df["Season"] == season_clean
        ].copy()

    if cutting_df.empty:
        return []

    # --------------------------------------------------------
    # USE TYPE
    # --------------------------------------------------------

    if "Use Type" not in cutting_df.columns:
        cutting_df["Use Type"] = "New Planting"

    cutting_df["Use Type"] = (
        cutting_df["Use Type"]
        .fillna("New Planting")
        .astype(str)
        .str.strip()
    )

    if use_type:
        cutting_df = cutting_df[
            cutting_df["Use Type"]
            == str(use_type).strip()
        ].copy()

    if cutting_df.empty:
        return []

    # ========================================================
    # NORMALISE HAULAGE DATA
    # ========================================================

    if not haulage_df.empty:

        haulage_df["Season"] = (
            haulage_df["Season"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        if season:
            haulage_df = haulage_df[
                haulage_df["Season"] == season_clean
            ].copy()

        if "Use Type" not in haulage_df.columns:
            haulage_df["Use Type"] = "New Planting"

        haulage_df["Use Type"] = (
            haulage_df["Use Type"]
            .fillna("New Planting")
            .astype(str)
            .str.strip()
        )

    # ========================================================
    # PRE-CALCULATE ACTUAL HAULAGE
    #
    # One groupby instead of calculating repeatedly.
    # ========================================================

    haulage_totals = {}

    if not haulage_df.empty:

        haulage_df["Cutting ID"] = (
            haulage_df["Cutting ID"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        haulage_df["Actual Tons"] = pd.to_numeric(
            haulage_df["Actual Tons"],
            errors="coerce"
        ).fillna(0)

        grouped = (
            haulage_df
            .groupby(
                ["Cutting ID", "Use Type"],
                dropna=False
            )["Actual Tons"]
            .sum()
        )

        for key, value in grouped.items():

            cutting_id = str(
                key[0]
            ).strip()

            row_use_type = str(
                key[1]
            ).strip()

            haulage_totals[
                (cutting_id, row_use_type)
            ] = float(value)

    # ========================================================
    # PRE-CALCULATE NEW PLANTING ALLOCATIONS
    #
    # THIS IS THE MAJOR PERFORMANCE FIX.
    #
    # Instead of calling:
    #
    # get_cutting_allocated_tonnes()
    #
    # for every cutting record, we calculate everything once.
    # ========================================================

    allocation_totals = {}

    if not allocation_df.empty:

        allocation_df["Season"] = (
            allocation_df["Season"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        if season:
            allocation_df = allocation_df[
                allocation_df["Season"] == season_clean
            ].copy()

        if not allocation_df.empty:

            allocation_df["Source Field"] = (
                allocation_df["Source Field"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
            )

            allocation_df["Destination Field"] = (
                allocation_df["Destination Field"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
            )

            allocation_df["Status"] = (
                allocation_df["Status"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
            )

            allocation_df["Planned Tonnes"] = pd.to_numeric(
                allocation_df["Planned Tonnes"],
                errors="coerce"
            ).fillna(0)

            # Exclude cancelled allocations
            allocation_df = allocation_df[
                allocation_df["Status"] != "CANCELLED"
            ].copy()

            grouped_allocations = (
                allocation_df
                .groupby(
                    [
                        "Season",
                        "Source Field",
                        "Destination Field"
                    ],
                    dropna=False
                )["Planned Tonnes"]
                .sum()
            )

            for key, value in grouped_allocations.items():

                allocation_totals[
                    (
                        str(key[0]).strip(),
                        str(key[1]).strip().upper(),
                        str(key[2]).strip().upper()
                    )
                ] = float(value)

    # ========================================================
    # PRE-CALCULATE TOTAL CUTTING AGAINST EACH ALLOCATION
    #
    # This replaces repeated calls to:
    #
    # get_cutting_recorded_tonnes()
    # ========================================================

    cutting_allocation_totals = {}

    # Work from the already-loaded cutting dataframe.

    temp_cutting = cutting_df.copy()

    temp_cutting["Source Field"] = (
        temp_cutting["Source Field"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    temp_cutting["Destination Field"] = (
        temp_cutting["Destination Field"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    temp_cutting["Estimated Tons"] = pd.to_numeric(
        temp_cutting["Estimated Tons"],
        errors="coerce"
    ).fillna(0)

    new_planting_cutting = temp_cutting[
        temp_cutting["Use Type"].str.upper()
        == "NEW PLANTING"
    ].copy()

    if not new_planting_cutting.empty:

        grouped_cutting = (
            new_planting_cutting
            .groupby(
                [
                    "Season",
                    "Source Field",
                    "Destination Field"
                ],
                dropna=False
            )["Estimated Tons"]
            .sum()
        )

        for key, value in grouped_cutting.items():

            cutting_allocation_totals[
                (
                    str(key[0]).strip(),
                    str(key[1]).strip().upper(),
                    str(key[2]).strip().upper()
                )
            ] = float(value)

    # ========================================================
    # BUILD RECONCILIATION
    # ========================================================

    results = []

    for _, row in cutting_df.iterrows():

        cutting_id = str(
            row.get("Cutting ID", "")
        ).strip()

        row_use_type = str(
            row.get(
                "Use Type",
                "New Planting"
            )
        ).strip()

        # ----------------------------------------------------
        # ESTIMATED TONNES
        # ----------------------------------------------------

        estimated_tons = pd.to_numeric(
            row.get(
                "Estimated Tons",
                0
            ),
            errors="coerce"
        )

        if pd.isna(estimated_tons):
            estimated_tons = 0.0

        estimated_tons = float(
            estimated_tons
        )

        # ----------------------------------------------------
        # BUNDLES
        # ----------------------------------------------------

        bundles = pd.to_numeric(
            row.get(
                "Bundles Cut",
                0
            ),
            errors="coerce"
        )

        if pd.isna(bundles):
            bundles = 0.0

        bundles = float(
            bundles
        )

        # ----------------------------------------------------
        # ACTUAL HAULAGE
        # ----------------------------------------------------

        actual_hauled = haulage_totals.get(
            (
                cutting_id,
                row_use_type
            ),
            0.0
        )

        actual_hauled = float(
            actual_hauled
        )

        remaining_estimated = max(
            estimated_tons - actual_hauled,
            0
        )

        # ----------------------------------------------------
        # HAULAGE STATUS
        # ----------------------------------------------------

        if actual_hauled <= 0:

            haulage_status = "Not Hauled"

        elif actual_hauled < estimated_tons:

            haulage_status = "Partially Hauled"

        elif abs(
            actual_hauled - estimated_tons
        ) < 0.001:

            haulage_status = "Fully Hauled"

        else:

            haulage_status = "Above Estimate"

        # ====================================================
        # NEW PLANTING ALLOCATION
        # ====================================================

        planned_allocation = 0.0
        allocation_cut_remaining = 0.0
        allocation_status = "Not Applicable"

        if row_use_type.upper() == "NEW PLANTING":

            source_field = str(
                row.get(
                    "Source Field",
                    ""
                )
            ).strip().upper()

            destination_field = str(
                row.get(
                    "Destination Field",
                    ""
                )
            ).strip().upper()

            row_season = str(
                row.get(
                    "Season",
                    ""
                )
            ).strip()

            allocation_key = (
                row_season,
                source_field,
                destination_field
            )

            planned_allocation = (
                allocation_totals.get(
                    allocation_key,
                    0.0
                )
            )

            total_cut = (
                cutting_allocation_totals.get(
                    allocation_key,
                    0.0
                )
            )

            allocation_cut_remaining = max(
                planned_allocation - total_cut,
                0
            )

            if planned_allocation <= 0:

                allocation_status = (
                    "No Allocation"
                )

            elif allocation_cut_remaining <= 0:

                allocation_status = (
                    "Allocation Cut"
                )

            else:

                allocation_status = (
                    "Allocation Remaining"
                )

        # ====================================================
        # GAP FILLING
        # ====================================================

        elif row_use_type.upper() == "GAP FILLING":

            allocation_status = (
                "No Planned Requirement"
            )

        # ====================================================
        # RESULT
        # ====================================================

        results.append({

            "Cutting ID": cutting_id,

            "Date": row.get(
                "Date",
                ""
            ),

            "Season": row.get(
                "Season",
                ""
            ),

            "Use Type": row_use_type,

            "Source Field": row.get(
                "Source Field",
                ""
            ),

            "Destination Field": row.get(
                "Destination Field",
                ""
            ),

            "Destination Subfield": row.get(
                "Destination Subfield",
                ""
            ),

            "Bundles Cut": round(
                bundles,
                2
            ),

            "Estimated Tons": round(
                estimated_tons,
                3
            ),

            "Actual Tons Hauled": round(
                actual_hauled,
                3
            ),

            "Remaining Estimated Tons": round(
                remaining_estimated,
                3
            ),

            "Planned Allocation Tons": round(
                planned_allocation,
                3
            ),

            "Allocation Cut Remaining": round(
                allocation_cut_remaining,
                3
            ),

            "Haulage Status": haulage_status,

            "Allocation Status": allocation_status,

        })

    return results


# ============================================================
# SEEDCANE HAULAGE SUMMARY
# ============================================================

def get_seedcane_haulage_summary(
    season=None
):
    """
    Return summary totals for Seedcane Haulage.

    New Planting and Gap Filling are kept separate.
    """

    reconciliation = (
        get_seedcane_haulage_reconciliation(
            season=season
        )
    )

    summary = {

        "New Planting": {
            "cutting_records": 0,
            "bundles_cut": 0.0,
            "estimated_tons": 0.0,
            "actual_tons_hauled": 0.0,
        },

        "Gap Filling": {
            "cutting_records": 0,
            "bundles_cut": 0.0,
            "estimated_tons": 0.0,
            "actual_tons_hauled": 0.0,
        },

    }

    for row in reconciliation:

        use_type = row["Use Type"]

        if use_type not in summary:
            continue

        summary[use_type]["cutting_records"] += 1

        summary[use_type]["bundles_cut"] += (
            row["Bundles Cut"]
        )

        summary[use_type]["estimated_tons"] += (
            row["Estimated Tons"]
        )

        summary[use_type]["actual_tons_hauled"] += (
            row["Actual Tons Hauled"]
        )

    # --------------------------------------------------------
    # ROUND TOTALS
    # --------------------------------------------------------

    for use_type in summary:

        summary[use_type]["bundles_cut"] = round(
            summary[use_type]["bundles_cut"],
            2
        )

        summary[use_type]["estimated_tons"] = round(
            summary[use_type]["estimated_tons"],
            3
        )

        summary[use_type]["actual_tons_hauled"] = round(
            summary[use_type]["actual_tons_hauled"],
            3
        )

    return summary