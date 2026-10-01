"""Consistent JSON error responses.

Every error the API returns has the shape:
    {"error": "<human readable message>", "fields": {"<field>": "<message>", ...}}
`fields` is empty ({}) when the error is not tied to specific inputs.

The React forms rely on this shape: `error` is shown as a red banner and each entry
in `fields` is shown under the matching input box.

HTTP status codes used in this project:
    400 Bad Request   – the input is invalid (validation failed)
    401 Unauthorized  – not logged in, or the token is missing/invalid/expired
    403 Forbidden     – logged in, but not allowed (wrong role, or not your data)
    404 Not Found     – the thing doesn't exist
    409 Conflict      – duplicate (email or admission number already used)
    500 Server Error  – a bug or crash on our side
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException

from app.extensions import jwt


class ApiError(Exception):
    """Raise anywhere in a request to return a JSON error with the given status.

    Example: raise ApiError("Email already in use", 409, {"email": "Email already in use"})
    The handler below catches it and sends the JSON response, so route code
    doesn't have to build error responses by hand.
    """

    def __init__(self, message: str, status_code: int = 400, fields: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.fields = fields or {}


def error_response(message: str, status_code: int, fields: dict | None = None):
    """Build the (JSON body, status code) pair Flask sends back."""
    return jsonify({"error": message, "fields": fields or {}}), status_code


def register_error_handlers(app):
    """Tell Flask what to send back when each kind of error happens."""

    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        # Our own errors: use their message, status and field errors as they are.
        return error_response(err.message, err.status_code, err.fields)

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        # Covers 404, 405, and malformed JSON (400) raised by Flask/Werkzeug.
        return error_response(err.description or err.name, err.code)

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        # Any other crash: log the full details for us (in the terminal), but only show
        # a generic message to the user, so internals aren't leaked.
        app.logger.exception("Unhandled error: %s", err)
        return error_response("An unexpected error occurred", 500)

    # --- Flask-JWT-Extended failures, rewritten into the same shape (all 401) ---
    # Without these, the JWT library would reply in its own format ({"msg": ...}).

    @jwt.unauthorized_loader
    def missing_token(reason):
        # No "Authorization: Bearer ..." header was sent.
        return error_response("Authentication required", 401)

    @jwt.invalid_token_loader
    def invalid_token(reason):
        # The token was tampered with or is malformed.
        return error_response("Invalid token", 401)

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        # The token is older than JWT_ACCESS_TOKEN_EXPIRES (60 minutes by default).
        return error_response("Token has expired", 401)
