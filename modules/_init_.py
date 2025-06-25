# modules/agriculture/__init__.py
from flask import Blueprint

agriculture_bp = Blueprint('agriculture', __name__, template_folder='templates')

from . import routes  # Import the routes module
