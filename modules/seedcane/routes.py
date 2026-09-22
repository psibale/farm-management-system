from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

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
    get_cutting_balance
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