"""The admin blueprint: everything under /api/admin (role: system_admin).

    routes.py      catalogues: skills, sectors, units
    dashboard.py   overview + activity log
    placements.py  placement records (TC09)
    records.py     students, partners, opportunities
    users.py       accounts: activate/deactivate, reset password, create admin
    crud.py        create / edit / delete students, partners, internships, accounts
    model.py       the model page
    reports.py     the reports page: placement rate by course, match vs outcome, pay

(See app/auth/__init__.py for what a Blueprint is.)
"""
from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Imported at the BOTTOM on purpose: these modules need `admin_bp` to exist first.
from app.admin import crud, dashboard, model, placements, records, reports, routes, users  # noqa: E402,F401
