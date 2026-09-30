from flask import Blueprint

opportunities_bp = Blueprint("opportunities", __name__, url_prefix="/api")

from app.opportunities import routes  # noqa: E402,F401  (registers the routes)
