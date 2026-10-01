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
    get_seedcane_cutting_for_haulage,
    get_seedcane_haulage_balance,
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

    total_loads = len(records)

    total_actual_tons = (
        pd.to_numeric(
            haulage_df["Actual Tons"],
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
    """
    Record actual Seedcane Haulage against an existing Cutting ID.
    """

    season = get_active_season()

    ensure_seedcane_haulage_file()

    if request.method == "POST":

        try:
            date = request.form.get("date", "").strip()
            cutting_id = request.form.get(
                "cutting_id",
                ""
            ).strip()

            vehicle = request.form.get(
                "vehicle",
                ""
            ).strip()

            weighbridge_ticket = request.form.get(
                "weighbridge_ticket",
                ""
            ).strip()

            gross_weight = request.form.get(
                "gross_weight",
                ""
            ).strip()

            tare_weight = request.form.get(
                "tare_weight",
                ""
            ).strip()

            notes = request.form.get(
                "notes",
                ""
            ).strip()

            if not date:
                raise ValueError(
                    "Date is required."
                )

            if not cutting_id:
                raise ValueError(
                    "Please select a Cutting ID."
                )

            if not vehicle:
                raise ValueError(
                    "Vehicle is required."
                )

            if not weighbridge_ticket:
                raise ValueError(
                    "Weighbridge Ticket is required."
                )

            save_seedcane_haulage(
                date=date,
                cutting_id=cutting_id,
                vehicle=vehicle,
                weighbridge_ticket=weighbridge_ticket,
                gross_weight=gross_weight,
                tare_weight=tare_weight,
                notes=notes,
                season=season
            )

            flash(
                "Seedcane haulage recorded successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "seedcane.haulage"
                )
            )

        except ValueError as e:

            flash(
                str(e),
                "danger"
            )

        except Exception as e:

            flash(
                f"Unable to save haulage: {e}",
                "danger"
            )

    # --------------------------------------------------------
    # GET: Load available cutting records
    # --------------------------------------------------------

    cutting_records = get_seedcane_cutting_register(
        season
    )

    cuttings = []

    for row in cutting_records:

        cutting_id = str(
            row.get("Cutting ID", "")
        ).strip()

        if not cutting_id:
            continue

        balance = get_seedcane_haulage_balance(
            cutting_id,
            season=season
        )

        if not balance:
            continue

        remaining = float(
            balance.get(
                "remaining_estimated_tons",
                0
            ) or 0
        )

        # Do not show fully hauled cuttings
        if remaining <= 0:
            continue

        cuttings.append({
            "cutting_id": cutting_id,

            "date": row.get(
                "Date",
                ""
            ),

            "use_type": row.get(
                "Use Type",
                "New Planting"
            ),

            "source_field": row.get(
                "Source Field",
                ""
            ),

            "destination_field": row.get(
                "Destination Field",
                ""
            ),

            "destination_subfield": row.get(
                "Destination Subfield",
                ""
            ),

            "bundles": row.get(
                "Bundles Cut",
                0
            ),

            "estimated_tons": balance.get(
                "estimated_tons",
                0
            ),

            "actual_tons": balance.get(
                "actual_tons_hauled",
                0
            ),

            "remaining_tons": remaining
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