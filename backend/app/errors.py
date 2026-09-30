"""Consistent JSON error responses.

Every error the API returns has the shape:
    {"error": "<human readable message>", "fields": {"<field>": "<message>", ...}}
`fields` is empty ({}) when the error is not tied to specific inputs.
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException

from app.extensions import jwt


class ApiError(Exception):
    """Raise anywhere in a request to return a JSON error with the given status."""

    def __init__(self, message: str, status_code: int = 400, fields: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.fields = fields or {}


def error_response(message: str, status_code: int, fields: dict | None = None):
    return jsonify({"error": message, "fields": fields or {}}), status_code


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        return error_response(err.message, err.status_code, err.fields)

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        # Covers 404, 405, and malformed JSON (400) raised by Flask/Werkzeug.
        return error_response(err.description or err.name, err.code)

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        app.logger.exception("Unhandled error: %s", err)
        return error_response("An unexpected error occurred", 500)

    # --- Flask-JWT-Extended failures, rewritten into the same shape (all 401) ---
    @jwt.unauthorized_loader
    def missing_token(reason):
        return error_response("Authentication required", 401)

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error_response("Invalid token", 401)

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return error_response("Token has expired", 401)
