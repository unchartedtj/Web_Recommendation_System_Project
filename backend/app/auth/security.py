"""Checks applied to EVERY request that carries a token.

1. Deactivated (or deleted) accounts: their tokens are rejected (401), even ones issued
   before the account was deactivated. flask-jwt-extended calls the "blocklist" check for
   every protected endpoint, so no route has to remember to do it.
2. "Must change password" (after an admin reset): every API call except the few needed to
   change the password is refused (403, code "password_change_required").
"""
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.extensions import db, jwt
from app.models import User

DEACTIVATED = "This account has been deactivated. Contact the WBL office."
# Endpoints a user who must change their password may still call.
ALLOWED_DURING_PASSWORD_CHANGE = {"/api/auth/me", "/api/auth/change-password",
                                  "/api/auth/login", "/api/auth/register", "/api/health"}


def _user_from_payload(jwt_payload) -> User | None:
    try:
        return db.session.get(User, int(jwt_payload["sub"]))
    except (KeyError, TypeError, ValueError):
        return None


def register_security(app):

    @jwt.token_in_blocklist_loader
    def _token_blocked(_jwt_header, jwt_payload) -> bool:
        user = _user_from_payload(jwt_payload)
        return user is None or not user.is_active

    @jwt.revoked_token_loader
    def _revoked(_jwt_header, _jwt_payload):
        return jsonify({"error": DEACTIVATED, "fields": {}, "code": "account_deactivated"}), 401

    @app.before_request
    def _require_password_change():
        if not request.path.startswith("/api/") or request.path in ALLOWED_DURING_PASSWORD_CHANGE:
            return None
        if request.method == "OPTIONS":            # CORS pre-flight checks carry no token
            return None
        try:
            verify_jwt_in_request(optional=True)    # no token → nothing to check here
            identity = get_jwt_identity()
        except Exception:
            return None                             # bad/expired token: the route itself answers
        if identity is None:
            return None
        user = db.session.get(User, int(identity))
        if user is not None and user.must_change_password:
            return jsonify({"error": "You must change your password before continuing.",
                            "fields": {}, "code": "password_change_required"}), 403
        return None
