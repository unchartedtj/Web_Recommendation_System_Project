"""The SUS (System Usability Scale) questionnaire blueprint: /api/sus (test case TC10)."""
from flask import Blueprint

sus_bp = Blueprint("sus", __name__, url_prefix="/api/sus")

from app.sus import routes  # noqa: E402,F401  (registers the routes)
