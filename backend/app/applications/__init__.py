"""The applications blueprint: students apply/withdraw, partners view candidates and decide.

(See app/auth/__init__.py for what a Blueprint is.)
"""
from flask import Blueprint

applications_bp = Blueprint("applications", __name__, url_prefix="/api")

# Imported at the BOTTOM on purpose: routes.py needs `applications_bp` to exist first.
from app.applications import routes  # noqa: E402,F401  (registers the routes)
