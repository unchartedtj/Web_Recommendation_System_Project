"""The admin blueprint: everything under /api/admin (role: system_admin).

    routes.py      catalogues: skills, sectors, units
    dashboard.py   overview + activity log
    placements.py  placement records (TC09)
    records.py     students, partners, opportunities
    users.py       accounts: activate/deactivate, reset password, create admin
    model_sus.py   the model page and SUS results (TC10)

(See app/auth/__init__.py for what a Blueprint is.)
"""
from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Imported at the BOTTOM on purpose: these modules need `admin_bp` to exist first.
from app.admin import dashboard, model_sus, placements, records, routes, users  # noqa: E402,F401
