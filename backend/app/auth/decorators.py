"""Role-based access helpers for protected endpoints."""
from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.errors import ApiError
from app.extensions import db
from app.models import User


def role_required(*roles: str):
    """Require a valid JWT whose `role` claim is one of `roles`.

    Missing or invalid token → 401 (via the JWT loaders); wrong role → 403.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if get_jwt().get("role") not in roles:
                raise ApiError("You do not have permission to perform this action", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def current_user() -> User:
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:  # token is valid but the account was deleted
        raise ApiError("User not found", 401)
    return user


def current_partner():
    partner = current_user().industry_partner
    if partner is None:
        raise ApiError("Industry partner profile not found", 403)
    return partner


def current_student():
    student = current_user().student
    if student is None:
        raise ApiError("Student profile not found", 403)
    return student
