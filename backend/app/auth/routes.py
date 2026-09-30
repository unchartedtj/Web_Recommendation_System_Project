"""Auth endpoints: register, login, me."""
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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    return data


@auth_bp.post("/register")
def register():
    data, errors = validate_registration(_json_body())
    if errors:
        raise ApiError("Validation failed", 400, errors)

    user = create_user_with_profile(data)
    return jsonify({"message": "Registration successful", "user": serialize_user(user)}), 201


@auth_bp.post("/login")
def login():
    data, errors = validate_login(_json_body())
    if errors:
        raise ApiError("Validation failed", 400, errors)

    user = User.query.filter_by(email=data["email"]).first()
    # One generic message for an unknown email or a wrong password, so the
    # endpoint can't be used to find out which emails are registered.
    if user is None or not user.check_password(data["password"]):
        raise ApiError(INVALID_CREDENTIALS, 401)

    # JWT "sub" must be a string. user_id and role also go in as custom claims
    # so the frontend can route by role without another request.
    token = create_access_token(
        identity=str(user.user_id),
        additional_claims={"user_id": user.user_id, "role": user.role.value},
    )
    return jsonify({"access_token": token, "user": serialize_user(user)}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:  # token is valid but the account was deleted
        raise ApiError("User not found", 401)
    return jsonify({"user": serialize_user(user)}), 200
