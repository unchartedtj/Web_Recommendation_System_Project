"""Auth endpoints: register, login, me.

Each function below handles one URL. The decorator above it says which HTTP method
and path, e.g. @auth_bp.post("/register") = POST /api/auth/register
(the /api/auth prefix comes from the blueprint in app/auth/__init__.py).

Routes stay thin on purpose: they read the request, call a validator, call a
service, and return JSON. The actual rules live in validators.py and services.py.
"""
from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.auth import auth_bp
from app.auth.services import create_user_with_profile, serialize_user
from app.auth.validators import validate_login, validate_registration
from app.errors import ApiError
from app.extensions import db
from app.models import User

INVALID_CREDENTIALS = "Invalid email or password"


def _json_body() -> dict:
    """Read the request body as JSON. Anything that isn't a JSON object → 400."""
    data = request.get_json(silent=True)   # silent=True: return None instead of crashing
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    return data


@auth_bp.post("/register")
def register():
    """Sign up as a student or industry partner."""
    # 1. Check every field; `errors` is {} if everything is fine.
    data, errors = validate_registration(_json_body())
    if errors:
        raise ApiError("Validation failed", 400, errors)

    # 2. Save the user + profile (raises a 409 ApiError for a duplicate email/admission no).
    user = create_user_with_profile(data)
    # 3. 201 Created, with the new user's public details (never the password hash).
    return jsonify({"message": "Registration successful", "user": serialize_user(user)}), 201


@auth_bp.post("/login")
def login():
    """Check email + password and hand back a JWT access token."""
    data, errors = validate_login(_json_body())
    if errors:
        raise ApiError("Validation failed", 400, errors)

    user = User.query.filter_by(email=data["email"]).first()   # None if no such email
    # One generic message for an unknown email or a wrong password, so the
    # endpoint can't be used to find out which emails are registered.
    if user is None or not user.check_password(data["password"]):
        raise ApiError(INVALID_CREDENTIALS, 401)

    # A JWT is a signed "ticket" the browser sends with later requests to prove who it is.
    # JWT "sub" must be a string. user_id and role also go in as custom claims
    # so the frontend can route by role without another request.
    token = create_access_token(
        identity=str(user.user_id),
        additional_claims={"user_id": user.user_id, "role": user.role.value},
    )
    return jsonify({"access_token": token, "user": serialize_user(user)}), 200


@auth_bp.get("/me")
@jwt_required()   # rejects the request with 401 unless a valid token is sent
def me():
    """Return the logged-in user's details (the React app calls this on page load)."""
    # get_jwt_identity() reads the user id we put into the token at login.
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:  # token is valid but the account was deleted
        raise ApiError("User not found", 401)
    return jsonify({"user": serialize_user(user)}), 200
