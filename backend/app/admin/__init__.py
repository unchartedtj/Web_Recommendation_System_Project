"""The admin blueprint: /api/admin/skills and /api/admin/sectors (preset-list management).

(See app/auth/__init__.py for what a Blueprint is.)
"""
from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Imported at the BOTTOM on purpose: routes.py needs `admin_bp` to exist first.
from app.admin import routes  # noqa: E402,F401  (registers the routes)
