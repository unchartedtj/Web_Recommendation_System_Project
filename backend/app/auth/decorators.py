"""Role-based access helpers for protected endpoints.

A decorator is a function that wraps another function to add behaviour before it runs.
Writing
    @role_required("industry_partner")
    def create_opportunity(): ...
means: "before create_opportunity runs, check the caller is a logged-in industry partner".
"""
from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.errors import ApiError
from app.extensions import db
from app.models import User


def role_required(*roles: str):
    """Require a valid JWT whose `role` claim is one of `roles`.

    Missing or invalid token → 401 (via the JWT loaders); wrong role → 403.
    `*roles` accepts any number of roles, e.g. role_required("student", "system_admin").
    """
    def decorator(fn):
        @wraps(fn)   # keeps the original function's name (Flask needs unique names per route)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()                  # 1. is there a valid token? (else 401)
            if get_jwt().get("role") not in roles:   # 2. is it the right role? (else 403)
                raise ApiError("You do not have permission to perform this action", 403)
            return fn(*args, **kwargs)               # 3. all good: run the real route
        return wrapper
    return decorator


def current_user() -> User:
    """The User who sent this request (found from the id inside their token)."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:  # token is valid but the account was deleted
        raise ApiError("User not found", 401)
    return user


def current_partner():
    """The IndustryPartner row of the logged-in user."""
    partner = current_user().industry_partner
    if partner is None:
        raise ApiError("Industry partner profile not found", 403)
    return partner


def current_student():
    """The Student row of the logged-in user."""
    student = current_user().student
    if student is None:
        raise ApiError("Student profile not found", 403)
    return student
