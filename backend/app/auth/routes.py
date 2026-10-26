from datetime import datetime, timezone

from flask import jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import func

from app.activity import log_activity, log_and_commit
from app.auth import auth_bp
from app.auth.services import create_user_with_profile, serialize_user
from app.auth.validators import validate_login, validate_password, validate_registration
from app.errors import ApiError
from app.utils import json_body
from app.extensions import db
from app.models import SystemAdmin, User

INVALID_CREDENTIALS = "Invalid email or password"
DEACTIVATED = "This account has been deactivated. Contact the WBL office."


def _find_login_user(identifier: str) -> User | None:
    
    if "@" in identifier:
        return User.query.filter_by(email=identifier).first()
    return (User.query.join(SystemAdmin)                          # only users with an admin row
            .filter(func.lower(SystemAdmin.name) == identifier)   # identifier is already lowercase
            .order_by(SystemAdmin.admin_id)                       # if two share a name, the oldest wins
            .first())


@auth_bp.post("/register")
def register():
    """Create account  as either a student or industry partner."""
    # 1. Check every field; `errors` is {} if everything is fine.
    data, errors = validate_registration(json_body())
    if errors:
        raise ApiError("Validation failed", 400, errors)

    # 2. Save the user + profile (raises a 409 ApiError for a duplicate email/admission no).
    user = create_user_with_profile(data)
    log_and_commit("auth.registered", actor=user, target_type="user", target_id=user.user_id,
                   details={"role": user.role.value})
    # 3. 201 Created, with the new user's public details (never the password hash).
    return jsonify({"message": "Registration successful", "user": serialize_user(user)}), 201


@auth_bp.post("/login")
def login():
    """Check email and  password and hand back a JWT access token."""
    data, errors = validate_login(json_body())
    if errors:
        raise ApiError("Validation failed", 400, errors)

    user = _find_login_user(data["email"])   # None if no such email / admin username
    # One generic message for an unknown email or a wrong password, so the
    # endpoint can't be used to find out which emails are registered.
    if user is None or not user.check_password(data["password"]):
        raise ApiError(INVALID_CREDENTIALS, 401)
    # Only AFTER the password check, so this message can't reveal which accounts exist.
    if not user.is_active:
        raise ApiError(DEACTIVATED, 403)

    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    log_and_commit("auth.login", actor=user, target_type="user", target_id=user.user_id)

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
    """Return the logged-in user's details using the React app."""
    # get_jwt_identity() reads the user id we put into the token at login.
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:  # token is valid but the account was deleted
        raise ApiError("User not found", 401)
    return jsonify({"user": serialize_user(user)}), 200


@auth_bp.post("/change-password")
@jwt_required()
def change_password():
    """Any logged-in user changes their own password (also required after an admin reset)."""
    user = db.session.get(User, int(get_jwt_identity()))
    data = json_body()
    current = data.get("current_password") if isinstance(data.get("current_password"), str) else ""
    new = data.get("new_password") if isinstance(data.get("new_password"), str) else ""
    confirm = data.get("confirm_password") if isinstance(data.get("confirm_password"), str) else ""

    errors = {}
    if not current:
        errors["current_password"] = "This field is required"
    elif not user.check_password(current):
        errors["current_password"] = "Your current password is incorrect"
    if not new:
        errors["new_password"] = "This field is required"
    elif msg := validate_password(new):                     # same rules as registration
        errors["new_password"] = msg
    elif current and new == current:
        errors["new_password"] = "Choose a password different from your current one"
    if "new_password" not in errors and new != confirm:
        errors["confirm_password"] = "Passwords do not match"
    if errors:
        raise ApiError("Validation failed", 400, errors)

    user.set_password(new)
    user.must_change_password = False
    log_activity("auth.password_changed", actor=user, target_type="user", target_id=user.user_id)
    db.session.commit()
    return jsonify({"message": "Password changed", "user": serialize_user(user)})
