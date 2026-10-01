"""The auth blueprint: groups the /api/auth/... routes (register, login, me).

A Blueprint is a named group of routes. create_app() registers it, and every route
defined on `auth_bp` automatically gets the url_prefix, e.g. "/register" becomes
"/api/auth/register".
"""
from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Imported at the BOTTOM on purpose: routes.py needs `auth_bp` (defined above) to exist.
from app.auth import routes  # noqa: E402,F401  (registers the routes on auth_bp)
