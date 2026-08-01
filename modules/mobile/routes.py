from flask import Blueprint, render_template

mobile_bp = Blueprint(
    "mobile",
    __name__,
    template_folder="../../templates/mobile"
)


@mobile_bp.route("/")
def home():

    return render_template("mobile/mobile_home.html")


@mobile_bp.route("/survey")
def survey():

    return render_template("mobile/survey.html")


@mobile_bp.route("/inspection")
def inspection():

    return render_template("mobile/inspection.html")


@mobile_bp.route("/sync")
def sync():

    return render_template("mobile/sync.html")