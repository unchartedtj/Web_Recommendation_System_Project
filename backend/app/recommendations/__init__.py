from flask import Blueprint

recommendations_bp = Blueprint("recommendations", __name__, url_prefix="/api")

from app.recommendations import routes  # noqa: E402,F401  (registers the routes)
