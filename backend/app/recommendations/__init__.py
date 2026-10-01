"""The recommendations blueprint: /api/grades, /api/recommendations and /api/admin/model/retrain.

(See app/auth/__init__.py for what a Blueprint is.)
"""
from flask import Blueprint

recommendations_bp = Blueprint("recommendations", __name__, url_prefix="/api")

# Imported at the BOTTOM on purpose: routes.py needs `recommendations_bp` to exist first.
from app.recommendations import routes  # noqa: E402,F401  (registers the routes)
