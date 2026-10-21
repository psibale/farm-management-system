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

@seedcane_bp.route("/cutting")
def cutting_register():

    active_season = str(get_active_season())

    season = request.args.get(
        "season",
        active_season
    )

    # ------------------------------------------------------------
    # LOAD CUTTING RECORDS
    # ------------------------------------------------------------

    records = get_seedcane_cutting_register(
        season
    )

    # ------------------------------------------------------------
    # SORT CUTTING IDs
    #
    # Latest/current Cutting ID appears first.
    #
    # Example:
    # SCC-004
    # SCC-003
    # SCC-002
    # SCC-001
    # ------------------------------------------------------------

    def cutting_id_number(record):

        cutting_id = str(
            record.get("Cutting ID", "")
        ).strip()

        try:
            return int(
                cutting_id
                .replace("SCC-", "")
                .strip()
            )
        except (ValueError, TypeError):
            return 0

    records = sorted(
        records,
        key=cutting_id_number,
        reverse=True
    )

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------

    summary = get_seedcane_cutting_summary(
        season
    )

    # ------------------------------------------------------------
    # RENDER
    # ------------------------------------------------------------

    return render_template(
        "seedcane/cutting.html",
        season=season,
        active_season=active_season,
        records=records,
        summary=summary
    )


@seedcane_bp.route(
    "/cutting/add",
    methods=["GET", "POST"]
)
def add_cutting():

    active_season = str(
        get_active_season()
    )

    season = request.args.get(
        "season",
        active_season
    )

    if request.method == "POST":

        source_field = request.form.get(
            "source_field",
            ""
        ).strip().upper()

        destination_field = request.form.get(
            "destination_field",
            ""
        ).strip().upper()

        destination_subfield = request.form.get(
            "destination_subfield",
            ""
        ).strip().upper()

        date = request.form.get(
            "date",
            ""
        )

        use_type = request.form.get(
            "use_type", "New Planting"
        ).strip()

        bundles = request.form.get(
            "bundles",
            ""
        )

        area_cut = request.form.get("area_cut", "")

        notes = request.form.get(
            "notes",
            ""
        )

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

        if result["success"]:

            flash(
                result["message"],
                "success"
            )

            return redirect(
                url_for(
                    "seedcane.cutting_register",
                    season=season
                )
            )

        flash(
            result["message"],
            "danger"
        )

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

@seedcane_bp.route("/haulage")
def haulage():
    """
    Seedcane Haulage Register
    """

    season = get_active_season()

    ensure_seedcane_haulage_file()

    haulage_df = load_seedcane_haulage()

    if season:
        haulage_df = haulage_df[
            haulage_df["Season"].astype(str).str.strip()
            == str(season).strip()
        ].copy()

    records = haulage_df.to_dict("records")

    for record in records:
        measured = pd.to_numeric(record.get("Actual Tons", 0), errors="coerce")
        estimated = pd.to_numeric(record.get("Estimated Tons", 0), errors="coerce")
        record["Recorded Tons"] = (
            (0.0 if pd.isna(measured) else float(measured))
            + (0.0 if pd.isna(estimated) else float(estimated))
        )
        basis = record.get("Weight Basis", "")
        if pd.isna(basis) or not str(basis).strip():
            if not pd.isna(measured) and float(measured) > 0:
                record["Weight Basis"] = "Direct Weighbridge (legacy)"
            elif not pd.isna(estimated) and float(estimated) > 0:
                record["Weight Basis"] = "Estimated (legacy)"
            else:
                record["Weight Basis"] = "Legacy record"

    total_loads = len(records)

    total_actual_tons = (
        pd.to_numeric(
            haulage_df["Actual Tons"],
            errors="coerce"
        ).fillna(0).sum()
        + pd.to_numeric(
            haulage_df.get("Estimated Tons", pd.Series(0, index=haulage_df.index)),
            errors="coerce"
        ).fillna(0).sum()
        if not haulage_df.empty
        else 0
    )

    return render_template(
        "seedcane/haulage.html",
        season=season,
        records=records,
        total_loads=total_loads,
        total_actual_tons=round(
            float(total_actual_tons),
            3
        )
    )

@seedcane_bp.route("/haulage/add", methods=["GET", "POST"])
def haulage_add():
    """Record actual Seedcane Haulage against an existing Cutting ID."""
    season = get_active_season()

    if request.method == "POST":
        try:
            date = request.form.get("date", "").strip()
            cutting_id = request.form.get("cutting_id", "").strip()
            vehicle = request.form.get("vehicle", "").strip()
            weighbridge_ticket = request.form.get("weighbridge_ticket", "").strip()
            gross_weight = request.form.get("gross_weight", "").strip()
            tare_weight = request.form.get("tare_weight", "").strip()
            bundles_hauled = request.form.get("bundles_hauled", "").strip()
            weight_basis = request.form.get(
                "weight_basis", "Sample Average"
            ).strip()
            notes = request.form.get("notes", "").strip()

            if not date:
                raise ValueError("Date is required.")
            if not cutting_id:
                raise ValueError("Please select a Cutting ID.")
            if not vehicle:
                raise ValueError("Vehicle is required.")
            save_seedcane_haulage(
                date=date,
                cutting_id=cutting_id,
                vehicle=vehicle,
                weighbridge_ticket=weighbridge_ticket,
                gross_weight=gross_weight,
                tare_weight=tare_weight,
                notes=notes,
                season=season,
                bundles_hauled=bundles_hauled,
                weight_basis=weight_basis
            )

            flash("Seedcane haulage recorded successfully.", "success")
            return redirect(url_for("seedcane.haulage"))

        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Unable to save haulage: {e}", "danger")

    # Read the cutting register once and aggregate haulage once.
    cutting_records = get_seedcane_cutting_register(season)
    balances = get_seedcane_haulage_balances(
        season=season,
        cutting_records=cutting_records
    )

    cuttings = []
    for row in cutting_records:
        cutting_id = str(row.get("Cutting ID", "")).strip()
        if not cutting_id:
            continue

        balance = balances.get(cutting_id)
        if not balance:
            continue

        remaining_bundles = balance.get("remaining_bundles", 0)
        if remaining_bundles <= 0:
            continue

        cuttings.append({
            "cutting_id": cutting_id,
            "date": row.get("Date", ""),
            "use_type": row.get("Use Type", "New Planting"),
            "source_field": row.get("Source Field", ""),
            "destination_field": row.get("Destination Field", ""),
            "destination_subfield": row.get("Destination Subfield", ""),
            "bundles": row.get("Bundles Cut", 0),
            "remaining_bundles": remaining_bundles,
            "estimated_tons": balance["estimated_tons"],
            "actual_tons": balance["actual_tons_hauled"],
            "remaining_tons": balance["remaining_estimated_tons"],
            "average_bundle_tons": row.get("Average Bundle Tons", 3),
            "sample_bundles": row.get("Sample Bundles Weighed", ""),
            "sample_net_tons": row.get("Sample Net Tons", ""),
            "sample_ticket": row.get("Sample Ticket", ""),
        })

    return render_template(
        "seedcane/haulage_add.html",
        season=season,
        cuttings=cuttings
    )
@seedcane_bp.route("/haulage/reconciliation")
def haulage_reconciliation():

    season = get_active_season()

    reconciliation = (
        get_seedcane_haulage_reconciliation(
            season=season
        )
    )

    summary = (
        get_seedcane_haulage_summary(
            season=season
        )
    )

    return render_template(
        "seedcane/haulage_reconciliation.html",
        season=season,
        reconciliation=reconciliation,
        summary=summary
    )
