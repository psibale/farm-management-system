from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

import pandas as pd

from modules.season import get_active_season

from .services import (
    get_seedcane_source_candidates,
    load_replant_requirements,
    get_seedcane_sources_for_destination,
    prepare_destination_sources,
    save_seedcane_allocations,
    get_destination_allocation_register,
    get_seedcane_allocation_summary,
    save_seedcane_cutting,
    get_seedcane_cutting_register,
    get_seedcane_cutting_summary,
    get_cutting_balance,
    get_gapfilling_cuttings,
    get_seedcane_gapfilling_register,
    get_seedcane_gapfilling_summary,
    get_seedcane_gapfilling_dashboard_summary,
    save_seedcane_gapfilling,
    ensure_seedcane_haulage_file,
    load_seedcane_haulage,
    get_seedcane_haulage_balances,
    get_seedcane_haulage_sample,
    get_seedcane_parent_field,
    get_seedcane_haulages_since_sample,
    save_seedcane_haulage,
    get_seedcane_haulage_reconciliation,
    get_seedcane_haulage_summary
)


seedcane_bp = Blueprint(
    "seedcane",
    __name__,
    url_prefix="/seedcane"
)


@seedcane_bp.route("/")
def dashboard():

    active_season = str(
        get_active_season()
    )

    season = request.args.get(
        "season",
        active_season
    )

    candidates = get_seedcane_source_candidates(
        season
    )

    requirements = load_replant_requirements(
        season
    )

    return render_template(
        "seedcane/dashboard.html",
        season=season,
        active_season=active_season,
        candidates=candidates,
        requirements=requirements.to_dict(
            orient="records"
        ) if not requirements.empty else []
    )

@seedcane_bp.route("/destination/<destination_field>")
def destination_sources(destination_field):

    active_season = str(get_active_season())

    season = request.args.get(
        "season",
        active_season
    )

    result = get_seedcane_sources_for_destination(
        destination_field,
        season
    )

    return render_template(
        "seedcane/destination_sources.html",
        season=season,
        active_season=active_season,
        destination=result["destination"],
        planned_date=result["planned_date"],
        priority=result.get("priority", ""),
        reason=result.get("reason", ""),
        sources=result["sources"]
    )

@seedcane_bp.route(
    "/allocate/<destination_field>",
    methods=["GET", "POST"]
)
def allocate(destination_field):

    active_season = str(get_active_season())

    season = request.args.get(
        "season",
        active_season
    )

    # ========================================================
    # SAVE ALLOCATION
    # ========================================================

    if request.method == "POST":

        selected_sources = request.form.getlist(
            "selected_sources"
        )

        allocations = []

        for source_field in selected_sources:

            field_name = str(
                source_field
            ).strip().upper()

            tonnes_value = request.form.get(
                f"tonnes_{field_name}",
                ""
            ).strip()

            allocations.append({
                "source_field": field_name,
                "planned_tonnes": tonnes_value
            })

        result = save_seedcane_allocations(
            destination_field,
            season,
            allocations
        )

        if result["success"]:

            flash(
                result["message"],
                "success"
            )

            if result.get("warning"):
                flash(
                    result["warning"],
                    "warning"
                )

            return redirect(
                url_for(
                    "seedcane.destination_sources",
                    destination_field=destination_field,
                    season=season
                )
            )

        flash(
            result["message"],
            "danger"
        )

    # ========================================================
    # DISPLAY ALLOCATION PAGE
    # ========================================================

    result = prepare_destination_sources(
        destination_field,
        season
    )

    return render_template(
        "seedcane/allocate.html",
        season=season,
        active_season=active_season,
        destination=result["destination"],
        planned_date=result["planned_date"],
        priority=result.get("priority", ""),
        reason=result.get("reason", ""),
        sources=result["sources"]
    )

# ============================================================
# SEEDCANE ALLOCATION REGISTER
# ============================================================

@seedcane_bp.route("/allocations")
def allocations_register():

    active_season = str(get_active_season())

    season = request.args.get(
        "season",
        active_season
    )

    register = get_destination_allocation_register(
        season
    )

    summary = get_seedcane_allocation_summary(
        register
    )

    return render_template(
        "seedcane/allocations.html",
        season=season,
        active_season=active_season,
        register=register,
        summary=summary
    )

# ============================================================
# ACTUAL SEEDCANE CUTTING
# ============================================================

# ============================================================
# SEEDCANE CUTTING REGISTER
# ============================================================

@seedcane_bp.route("/cutting")
def cutting_register():

    active_season = str(get_active_season())

    season = request.args.get(
        "season",
        active_season
    ).strip()

    # --------------------------------------------------------
    # LOAD CUTTING RECORDS
    # --------------------------------------------------------

    records = get_seedcane_cutting_register(season)

    # --------------------------------------------------------
    # SORT CUTTING IDs - NEWEST FIRST
    # --------------------------------------------------------

    def cutting_id_number(record):

        cutting_id = str(
            record.get("Cutting ID", "")
        ).strip().upper()

        try:
            return int(cutting_id.replace("SCC-", ""))

        except (ValueError, TypeError):
            return 0

    records = sorted(
        records,
        key=cutting_id_number,
        reverse=True
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = get_seedcane_cutting_summary(season)

    return render_template(
        "seedcane/cutting.html",
        season=season,
        active_season=active_season,
        records=records,
        summary=summary
    )


# ============================================================
# ADD SEEDCANE CUTTING
# ============================================================

@seedcane_bp.route(
    "/cutting/add",
    methods=["GET", "POST"]
)
def add_cutting():

    active_season = str(get_active_season())

    season = request.args.get(
        "season",
        active_season
    ).strip()

    # --------------------------------------------------------
    # SAVE CUTTING
    # --------------------------------------------------------

    if request.method == "POST":

        source_field = request.form.get(
            "source_field", ""
        ).strip().upper()

        destination_field = request.form.get(
            "destination_field", ""
        ).strip().upper()

        destination_subfield = request.form.get(
            "destination_subfield", ""
        ).strip().upper()

        date = request.form.get(
            "date", ""
        ).strip()

        use_type = request.form.get(
            "use_type",
            "New Planting"
        ).strip()

        bundles = request.form.get(
            "bundles", ""
        ).strip()

        area_cut = request.form.get(
            "area_cut", ""
        ).strip()

        notes = request.form.get(
            "notes", ""
        ).strip()

        result = save_seedcane_cutting(
            date=date,
            season=season,
            source_field=source_field,
            destination_field=destination_field,
            destination_subfield=destination_subfield,
            use_type=use_type,
            bundles=bundles,
            area_cut=area_cut,
            notes=notes
        )

        if result.get("success"):

            flash(
                result.get(
                    "message",
                    "Seedcane cutting recorded successfully."
                ),
                "success"
            )

            return redirect(
                url_for(
                    "seedcane.cutting_register",
                    season=season
                )
            )

        flash(
            result.get(
                "message",
                "Unable to record seedcane cutting."
            ),
            "danger"
        )

    # --------------------------------------------------------
    # DISPLAY FORM
    # --------------------------------------------------------

    return render_template(
        "seedcane/cutting_add.html",
        season=season,
        active_season=active_season
    )

@seedcane_bp.route(
    "/gapfilling/add",
    methods=["GET", "POST"]
)
def gapfilling_add():

    active_season = str(get_active_season())

    if request.method == "POST":

        date = request.form.get("date", "").strip()
        cutting_id = request.form.get("cutting_id", "").strip()
        destination_subfield = request.form.get(
            "destination_subfield", ""
        ).strip()

        bundles_used = request.form.get(
            "bundles_used", ""
        ).strip()

        capitao = request.form.get(
            "capitao", "0"
        ).strip()

        seedcane_choppers = request.form.get(
            "seedcane_choppers", "0"
        ).strip()

        planters = request.form.get(
            "planters", "0"
        ).strip()

        mandays = request.form.get(
            "mandays", "0"
        ).strip()

        notes = request.form.get(
            "notes", ""
        ).strip()

        result = save_seedcane_gapfilling(
            date=date,
            season=active_season,
            cutting_id=cutting_id,
            destination_subfield=destination_subfield,
            bundles_used=bundles_used,
            capitao=capitao,
            seedcane_choppers=seedcane_choppers,
            planters=planters,
            mandays=mandays,
            notes=notes
        )

        if result["success"]:

            flash(
                result["message"],
                "success"
            )

            return redirect(
                url_for(
                    "seedcane.gapfilling_summary"
                )
            )

        flash(
            result["message"],
            "danger"
        )

    # ------------------------------------------------------
    # ONLY DATA NEEDED BY THE RECORDING FORM
    # ------------------------------------------------------

    cuttings = get_gapfilling_cuttings(
        active_season
    )

    return render_template(
        "seedcane/gapfilling.html",
        season=active_season,
        cuttings=cuttings
    )

@seedcane_bp.route(
    "/gapfilling/summary"
)
def gapfilling_summary():

    active_season = str(
        get_active_season()
    )

    dashboard = (
        get_seedcane_gapfilling_dashboard_summary(
            active_season,
            recent_limit=10
        )
    )

    return render_template(
        "seedcane/gapfilling_summary.html",
        season=active_season,
        dashboard=dashboard
    )

@seedcane_bp.route(
    "/gapfilling/cutting-balance"
)
def gapfilling_cutting_balance():

    active_season = str(
        get_active_season()
    )

    cuttings = get_gapfilling_cuttings(
        active_season
    )

    return render_template(
        "seedcane/gapfilling_cutting_balance.html",
        season=active_season,
        cuttings=cuttings
    )

@seedcane_bp.route(
    "/gapfilling/register"
)
def gapfilling_register():

    active_season = str(
        get_active_season()
    )

    records = get_seedcane_gapfilling_register(
        active_season
    )

    return render_template(
        "seedcane/gapfilling_register.html",
        season=active_season,
        records=records
    )

# ============================================================
# SEEDCANE HAULAGE
# ============================================================
# ============================================================
# SEEDCANE HAULAGE REGISTER
# ============================================================

@seedcane_bp.route("/haulage")
def haulage():

    season = str(get_active_season())

    # --------------------------------------------------------
    # LOAD HAULAGE RECORDS
    # --------------------------------------------------------

    ensure_seedcane_haulage_file()

    haulage_df = load_seedcane_haulage()

    if haulage_df.empty:

        records = []
        total_loads = 0
        total_tons = 0.0

    else:

        # ----------------------------------------------------
        # FILTER ACTIVE SEASON
        # ----------------------------------------------------

        if "Season" in haulage_df.columns:

            haulage_df = haulage_df[
                haulage_df["Season"]
                .fillna("")
                .astype(str)
                .str.strip()
                == season
            ].copy()

        # ----------------------------------------------------
        # NORMALISE TONNAGE
        # ----------------------------------------------------

        actual = pd.to_numeric(
            haulage_df["Actual Tons"],
            errors="coerce"
        ).fillna(0)

        estimated = pd.to_numeric(
            haulage_df.get(
                "Estimated Tons",
                pd.Series(0, index=haulage_df.index)
            ),
            errors="coerce"
        ).fillna(0)

        # Each transaction should normally have either
        # Actual Tons or Estimated Tons populated.
        haulage_df["Recorded Tons"] = actual + estimated

        # ----------------------------------------------------
        # WEIGHT BASIS - LEGACY COMPATIBILITY
        # ----------------------------------------------------

        if "Weight Basis" not in haulage_df.columns:
            haulage_df["Weight Basis"] = ""

        for index, row in haulage_df.iterrows():

            basis = str(
                row.get("Weight Basis", "") or ""
            ).strip()

            if not basis:

                if actual.loc[index] > 0:
                    haulage_df.at[
                        index, "Weight Basis"
                    ] = "Direct Weighbridge (legacy)"

                elif estimated.loc[index] > 0:
                    haulage_df.at[
                        index, "Weight Basis"
                    ] = "Estimated (legacy)"

                else:
                    haulage_df.at[
                        index, "Weight Basis"
                    ] = "Legacy record"

        # ----------------------------------------------------
        # REGISTER AND SUMMARY
        # ----------------------------------------------------

        records = haulage_df.to_dict("records")

        total_loads = len(records)

        total_tons = float(
            haulage_df["Recorded Tons"].sum()
        )

    return render_template(
        "seedcane/haulage.html",
        season=season,
        records=records,
        total_loads=total_loads,
        total_actual_tons=round(total_tons, 3)
    )

# ============================================================
# ADD SEEDCANE HAULAGE
# ============================================================

@seedcane_bp.route(
    "/haulage/add",
    methods=["GET", "POST"]
)
def haulage_add():
    season = str(get_active_season())

    if request.method == "POST":
        try:
            result = save_seedcane_haulage(
                date=request.form.get("date", "").strip(),
                cutting_id=request.form.get("cutting_id", "").strip(),
                vehicle=request.form.get("vehicle", "").strip(),
                weighbridge_ticket=request.form.get("weighbridge_ticket", "").strip(),
                gross_weight=request.form.get("gross_weight", "").strip(),
                tare_weight=request.form.get("tare_weight", "").strip(),
                notes=request.form.get("notes", "").strip(),
                season=season,
                bundles_hauled=request.form.get("bundles_hauled", "").strip(),
                weight_basis=request.form.get("weight_basis", "Sample Average").strip(),
                record_new_sample=request.form.get("record_new_sample", ""),
                sample_bundles_weighed=request.form.get("sample_bundles_weighed", "").strip(),
                sample_net_tons=request.form.get("sample_net_tons", "").strip(),
                sample_ticket=request.form.get("sample_ticket", "").strip(),
            )
            flash(
                "Haulage recorded successfully. New sample saved for subsequent loads."
                if result.get("Sample Average Bundle Tons") != ""
                else "Seedcane haulage recorded successfully.",
                "success"
            )
            return redirect(url_for("seedcane.haulage"))
        except ValueError as error:
            flash(str(error), "danger")
        except Exception as error:
            flash(f"Unable to save haulage: {error}", "danger")

    cutting_records = get_seedcane_cutting_register(season)
    balances = get_seedcane_haulage_balances(season=season, cutting_records=cutting_records)
    cuttings = []
    for row in cutting_records:
        cutting_id = str(row.get("Cutting ID", "")).strip()
        if not cutting_id:
            continue
        balance = balances.get(cutting_id)
        if not balance:
            continue
        remaining_bundles = float(balance.get("remaining_bundles", 0) or 0)
        if remaining_bundles <= 0:
            continue
        source_field = str(row.get("Source Field", "")).strip().upper()
        parent_field = get_seedcane_parent_field(source_field)
        sample = get_seedcane_haulage_sample(source_field, season=season)
        haulages_since_sample = get_seedcane_haulages_since_sample(
            source_field,
            sample.get("sample_date") if sample else None,
            season=season,
            sample_source_field=sample.get("sample_source_field") if sample else None
        ) if sample else 0
        cuttings.append({
            "cutting_id": cutting_id,
            "date": row.get("Date", ""),
            "use_type": row.get("Use Type", "New Planting"),
            "source_field": source_field,
            "parent_field": parent_field,
            "destination_field": row.get("Destination Field", ""),
            "destination_subfield": row.get("Destination Subfield", ""),
            "bundles": row.get("Bundles Cut", 0),
            "remaining_bundles": remaining_bundles,
            "estimated_tons": balance.get("estimated_tons", 0),
            "actual_tons": balance.get("actual_tons_hauled", 0),
            "remaining_tons": balance.get("remaining_estimated_tons", 0),
            "average_bundle_tons": sample.get("average_bundle_tons", "") if sample else "",
            "sample_source_field": sample.get("sample_source_field", "") if sample else "",
            "sample_date": sample.get("sample_date", "") if sample else "",
            "sample_ticket": sample.get("sample_ticket", "") if sample else "",
            "sample_bundles": sample.get("sample_bundles", "") if sample else "",
            "sample_net_tons": sample.get("sample_net_tons", "") if sample else "",
            "sample_is_own": sample.get("is_own_sample", False) if sample else False,
            "haulages_since_sample": haulages_since_sample,
            "sample_due": bool(sample and haulages_since_sample >= 9),
            "sample_status": "Available" if sample else "No sample in this parent field",
        })

    return render_template(
        "seedcane/haulage_add.html",
        season=season,
        cuttings=cuttings
    )

# ============================================================
# SEEDCANE HAULAGE RECONCILIATION
# ============================================================

@seedcane_bp.route("/haulage/reconciliation")
def haulage_reconciliation():

    season = str(get_active_season())

    reconciliation = get_seedcane_haulage_reconciliation(
        season=season
    )

    summary = get_seedcane_haulage_summary(
        season=season
    )

    return render_template(
        "seedcane/haulage_reconciliation.html",
        season=season,
        reconciliation=reconciliation,
        summary=summary
    )