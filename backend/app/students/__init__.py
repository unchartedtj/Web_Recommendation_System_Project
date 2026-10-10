"""The students blueprint: /api/student/profile (grades + skills + career interests).

(See app/auth/__init__.py for what a Blueprint is.)
"""
from flask import Blueprint

students_bp = Blueprint("students", __name__, url_prefix="/api/student")

# Imported at the BOTTOM on purpose: routes.py needs `students_bp` to exist first.
from app.students import routes  # noqa: E402,F401  (registers the routes)
