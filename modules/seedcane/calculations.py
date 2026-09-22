from datetime import datetime
import pandas as pd


MIN_SEEDCANE_AGE_MONTHS = 8
MAX_SEEDCANE_AGE_MONTHS = 10


def calculate_age_months(start_date, reference_date):
    """
    Calculate whole months between two dates.

    The reference date is normally the planned seedcane
    requirement/cutting date, NOT today's date.
    """

    if pd.isna(start_date) or pd.isna(reference_date):
        return None

    start_date = pd.to_datetime(start_date, errors="coerce")
    reference_date = pd.to_datetime(reference_date, errors="coerce")

    if pd.isna(start_date) or pd.isna(reference_date):
        return None

    months = (
        (reference_date.year - start_date.year) * 12
        + (reference_date.month - start_date.month)
    )

    # If the day has not yet been reached, remove one month.
    if reference_date.day < start_date.day:
        months -= 1

    return max(months, 0)


def seedcane_age_status(age_months):
    """
    Determine seedcane suitability based on expected age.
    """

    if age_months is None:
        return "Missing Data"

    if age_months < MIN_SEEDCANE_AGE_MONTHS:
        return "Too Young"

    if age_months <= MAX_SEEDCANE_AGE_MONTHS:
        return "Suitable"

    return "Too Old"


def get_estate(field):
    """
    Determine estate from field prefix.
    """

    field = str(field).strip().upper()

    if field.startswith("DG"):
        return "Main Estate"

    if field.startswith("L"):
        return "Liwaladzi Estate"

    if field.startswith("M"):
        return "Kasitu Estate"

    return "Unknown"