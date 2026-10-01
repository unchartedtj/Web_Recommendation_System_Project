"""The opportunities blueprint: /api/units, /api/opportunities and /api/partner/opportunities.

(See app/auth/__init__.py for what a Blueprint is.)
"""
from flask import Blueprint

opportunities_bp = Blueprint("opportunities", __name__, url_prefix="/api")

# Imported at the BOTTOM on purpose: routes.py needs `opportunities_bp` to exist first.
from app.opportunities import routes  # noqa: E402,F401  (registers the routes)
