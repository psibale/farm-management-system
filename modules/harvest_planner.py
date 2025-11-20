# modules/harvest_planner.py
import os
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import math

DATA_FOLDER = Path(os.getenv("AI_DATA_DIR", "data"))

# Configurable defaults
MATURITY_MONTHS = 12
DEFAULT_MILL_WEEKLY_CAPACITY = 2500.0  # tons per week (adjust to your mill)
WEEK_DAYS = 7

# --- Helpers ---
def safe_read_excel(fname):
    p = DATA_FOLDER / fname
    if p.exists():
        try:
            df = pd.read_excel(p)
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            print(f"Failed to read {p}: {e}")
    return None

def parse_date(d):
    if pd.isna(d):
        return None
    if isinstance(d, datetime):
        return d.date()
    try:
        return pd.to_datetime(d).date()
    except Exception:
        return None

# --- Load all relevant datasets ---
def load_all():
    files = {
        "fields": "field_polygons.xlsx",        # must contain Field, Area_ha, Stress (0-100)
        "planting": "planting_records.xlsx",    # must contain Field, Planting Date (or Date)
        "harvesting": "harvesting_records.xlsx",# must contain Field, Harvest Date (or Date)
        "yield": "yield_data.xlsx",             # must contain Field, TCH (or Yield)
        "fertilizer": "fertilizer.xlsx",       # optional
        "irrigation": "irrigation.xlsx",       # optional
    }
    data = {}
    for k, v in files.items():
        data[k] = safe_read_excel(v)
    return data

# --- Estimate TCH for a field using history + simple adjustments ---
def estimate_tch_for_field(field, data):
    """
    field: field id (value as in files)
    data: dict returned by load_all()
    Returns estimated TCH (tons cane per hectare)
    """
    # Base from historical yields
    yield_df = data.get("yield")
    base_tch = None
    if yield_df is not None and "Field" in yield_df.columns:
        try:
            hist = yield_df[yield_df["Field"] == field]
            # look for column names that look like yield: 'TCH', 'Yield', 'Yield (Tons)', etc.
            col = None
            for c in ["TCH", "Yield", "Yield (Tons)", "Yield_Tons", "Yield_tch"]:
                if c in hist.columns:
                    col = c
                    break
            if col is None:
                # fallback to numeric columns excluding Field and Date
                numeric_cols = [c for c in hist.columns if pd.api.types.is_numeric_dtype(hist[c]) and c.lower() != "field"]
                col = numeric_cols[0] if numeric_cols else None
            if col:
                # Weighted recent mean (recent larger weight)
                hist_vals = hist[col].dropna().astype(float).tolist()
                if len(hist_vals) > 0:
                    # weight last value 0.6, remaining 0.4 equally
                    if len(hist_vals) == 1:
                        base_tch = float(hist_vals[-1])
                    else:
                        recent = hist_vals[-1]
                        older_mean = float(pd.Series(hist_vals[:-1]).mean()) if len(hist_vals[:-1])>0 else recent
                        base_tch = recent*0.6 + older_mean*0.4
        except Exception:
            base_tch = None

    # fallback default if no history
    if base_tch is None:
        base_tch = 80.0  # conservative baseline TCH, adjust to your typical farm

    # Adjust for fertilizer records (if available)
    fert_df = data.get("fertilizer")
    fert_factor = 1.0
    if fert_df is not None and "Field" in fert_df.columns:
        f = fert_df[fert_df["Field"] == field]
        if not f.empty:
            # simple heuristic: if any fertilizer applied in current season -> small boost
            fert_factor = 1.05

    # Adjust for irrigation (if available)
    irr_df = data.get("irrigation")
    irr_factor = 1.0
    if irr_df is not None and "Field" in irr_df.columns:
        irr = irr_df[irr_df["Field"] == field]
        if not irr.empty:
            # if many irrigation events recently -> small boost
            recent_count = len(irr)
            if recent_count >= 5:
                irr_factor = 1.10
            elif recent_count >= 2:
                irr_factor = 1.04

    # Adjust for stress level from field_polygons
    fields_df = data.get("fields")
    stress_factor = 1.0
    if fields_df is not None and "Field" in fields_df.columns:
        row = fields_df[fields_df["Field"] == field]
        if not row.empty:
            # Accept stress column names 'Stress', 'Stress Level'
            sc = None
            for c in ["Stress", "Stress Level", "stress", "stress_level"]:
                if c in row.columns:
                    sc = c
                    break
            if sc:
                try:
                    stress = float(row.iloc[0][sc])
                    if stress <= 25:
                        stress_factor = 1.08
                    elif stress <= 50:
                        stress_factor = 1.03
                    elif stress <= 75:
                        stress_factor = 0.95
                    else:
                        stress_factor = 0.88
                except Exception:
                    stress_factor = 1.0

    est_tch = base_tch * fert_factor * irr_factor * stress_factor
    return round(est_tch, 2)

# --- Estimate harvest date (12 months after planting or last harvest) ---
def estimate_harvest_date_for_field(field, data, maturity_months=MATURITY_MONTHS):
    planting_df = data.get("planting")
    harvesting_df = data.get("harvesting")
    last_event = None

    # check last harvest first (ratoon)
    if harvesting_df is not None and "Field" in harvesting_df.columns:
        dfh = harvesting_df[harvesting_df["Field"] == field]
        if not dfh.empty:
            # pick the latest harvest date column
            date_cols = [c for c in dfh.columns if "date" in c.lower() or "harvest" in c.lower()]
            if date_cols:
                try:
                    last_dates = pd.to_datetime(dfh[date_cols[0]], errors="coerce").dropna()
                    if not last_dates.empty:
                        last_event = last_dates.max().date()
                except Exception:
                    pass
            else:
                # attempt find any datetime-like column
                for c in dfh.columns:
                    if pd.api.types.is_datetime64_any_dtype(dfh[c]) or "date" in c.lower():
                        last_dates = pd.to_datetime(dfh[c], errors="coerce").dropna()
                        if not last_dates.empty:
                            last_event = last_dates.max().date()
                            break

    # if no last harvest, use planting date
    if last_event is None and planting_df is not None and "Field" in planting_df.columns:
        dfn = planting_df[planting_df["Field"] == field]
        if not dfn.empty:
            date_cols = [c for c in dfn.columns if "date" in c.lower() or "plant" in c.lower()]
            if date_cols:
                try:
                    pdates = pd.to_datetime(dfn[date_cols[0]], errors="coerce").dropna()
                    if not pdates.empty:
                        last_event = pdates.max().date()
                except Exception:
                    pass

    if last_event is None:
        return None

    # add maturity months
    try:
        # approximate months as 30 days each
        est = last_event + timedelta(days=int(maturity_months * 30))
        return est
    except Exception:
        return None

# --- Generate plan (fields list with estimates) ---
def generate_field_estimates(data):
    fields_df = data.get("fields")
    # if fields list not available, try from planting/yield tables
    if fields_df is None or "Field" not in fields_df.columns:
        # collect unique fields from planting, harvesting, yield
        fields = set()
        for k in ("planting", "harvesting", "yield"):
            df = data.get(k)
            if df is not None and "Field" in df.columns:
                fields.update(df["Field"].dropna().unique().tolist())
        # create a minimal fields_df
        fields_df = pd.DataFrame({"Field": list(fields)})
        fields_df["Area_ha"] = 3.0
        fields_df["Stress"] = 50.0

    estimates = []
    for _, row in fields_df.iterrows():
        field = row.get("Field")
        if pd.isna(field):
            continue
        try:
            area = float(row.get("Area_ha") if "Area_ha" in row.index else row.get("Area") if "Area" in row.index else row.get("Area (ha)", 1.0))
        except Exception:
            area = 1.0

        stress = None
        for sc in ("Stress", "Stress Level", "stress", "stress_level"):
            if sc in row.index:
                try:
                    stress = float(row.get(sc))
                except Exception:
                    stress = None
                break

        tch = estimate_tch_for_field(field, data)
        est_date = estimate_harvest_date_for_field(field, data)
        # weeks/months age
        age_days = None
        if est_date:
            # compute approximate planting/ratoon date by subtracting maturity months
            event_date = est_date - timedelta(days=MATURITY_MONTHS*30)
            age_days = (datetime.today().date() - event_date).days
        est_tons = round(tch * area, 2)

        estimates.append({
            "Field": field,
            "Area_ha": round(area, 3),
            "Stress": round(stress,2) if stress is not None else None,
            "Est_TCH": tch,
            "Est_Tons": est_tons,
            "Est_Harvest_Date": est_date,
        })
    # sort by estimated harvest date
    estimates = sorted(estimates, key=lambda x: (x["Est_Harvest_Date"] or datetime.max.date()))
    return estimates

# --- Build weekly schedule by assigning fields into weeks respecting mill capacity ---
def build_weekly_schedule(estimates, weekly_capacity=DEFAULT_MILL_WEEKLY_CAPACITY, start_from=None):
    # choose start date: earliest estimated harvest date if not provided
    est_dates = [e["Est_Harvest_Date"] for e in estimates if e["Est_Harvest_Date"]]
    if not est_dates:
        return []

    if start_from is None:
        start = min(est_dates)
    else:
        start = start_from

    # create week bins (dict: week_start_date -> {capacity_left, fields})
    schedule = []
    # convert estimates to prioritized list: earlier date first, but increase priority for high stress
    prioritized = sorted(estimates, key=lambda e: ((e["Est_Harvest_Date"] or datetime.max.date()), - (e["Stress"] or 0)))

    # mapping week_start -> remaining capacity and assigned fields
    weeks = []
    # We'll grow weeks as needed
    for field in prioritized:
        tons = field["Est_Tons"] or 0.0
        assigned = False
        # iterate existing weeks
        for w in weeks:
            if w["remaining"] >= tons:
                w["fields"].append(field)
                w["remaining"] -= tons
                assigned = True
                break
        if not assigned:
            # create new week starting at next available week start
            # week index equals len(weeks)
            week_start = start + timedelta(days=WEEK_DAYS * len(weeks))
            week_end = week_start + timedelta(days=WEEK_DAYS-1)
            w = {
                "start": week_start,
                "end": week_end,
                "capacity": weekly_capacity,
                "remaining": max(0.0, weekly_capacity - tons),
                "fields": [field]
            }
            weeks.append(w)
    # convert weeks to schedule format
    schedule = []
    for w in weeks:
        total_assigned = w["capacity"] - w["remaining"]
        schedule.append({
            "Week_Start": w["start"],
            "Week_End": w["end"],
            "Target_Tons": round(w["capacity"],2),
            "Assigned_Tons": round(total_assigned,2),
            "Remaining_Tons": round(w["remaining"],2),
            "Assigned_Fields": [f["Field"] for f in w["fields"]],
            "Fields_Details": w["fields"]
        })
    return schedule

