"""The transcripts blueprint: students upload their transcript PDF, admins verify the marks.

(See app/auth/__init__.py for what a Blueprint is.)
"""
from flask import Blueprint

transcripts_bp = Blueprint("transcripts", __name__, url_prefix="/api")

from app.transcripts import routes  # noqa: E402,F401  (registers the routes)
