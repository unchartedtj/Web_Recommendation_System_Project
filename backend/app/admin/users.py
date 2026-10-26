"""System user accounts.

    GET   /api/admin/users?role=&active=&search=
    GET   /api/admin/users/<id>/impact           what deactivating would change (for the dialog)
    PATCH /api/admin/users/<id>/deactivate
    PATCH /api/admin/users/<id>/activate
    POST  /api/admin/users/<id>/reset-password   {temporary_password?} → shown ONCE
    POST  /api/admin/admins                      {name, email, password} → a new system admin

Rules: an admin can't deactivate themselves or the last active admin.
Deactivating a partner closes their open opportunities (and retrains the model);
deactivating a student withdraws their pending/shortlisted applications.
"""
import secrets

from flask import jsonify, request
from sqlalchemy import func

from app.activity import log_activity
from app.admin import admin_bp
from app.admin.common import ADMIN, bool_arg, choice_arg, iso, paginate, str_arg
from app.applications.services import withdraw_all_active
from app.auth.decorators import current_user, role_required
from app.auth.services import create_user_with_profile
from app.auth.validators import validate_email, validate_password
from app.errors import ApiError
from app.extensions import db
from app.models import Application, ApplicationStatus, OpportunityStatus, User, UserRole
from app.opportunities.services import refit_model

ROLES = tuple(r.value for r in UserRole)
REASON_DEACTIVATED = "Account deactivated"


def user_row(u: User) -> dict:
    return {"user_id": u.user_id, "email": u.email, "role": u.role.value, "name": u.display_name,
            "is_active": u.is_active, "must_change_password": u.must_change_password,
            "last_login_at": iso(u.last_login_at), "created_at": iso(u.created_at)}


def _get_user(user_id: int) -> User:
    u = db.session.get(User, user_id)
    if u is None:
        raise ApiError("User not found", 404)
    return u


def _impact(u: User) -> dict:
    open_opps, active_apps = [], 0
    if u.role == UserRole.INDUSTRY_PARTNER and u.industry_partner:
        open_opps = [o for o in u.industry_partner.opportunities if o.status == OpportunityStatus.OPEN]
    if u.role == UserRole.STUDENT and u.student:
        active_apps = Application.query.filter(
            Application.student_id == u.student.student_id,
            Application.status.in_(ApplicationStatus.ACTIVE)).count()
    return {"open_opportunities": len(open_opps), "active_applications": active_apps,
            "_open": open_opps}


@admin_bp.get("/users")
@role_required(ADMIN)
def list_users():
    query = User.query
    role = choice_arg("role", ROLES)
    if role:
        query = query.filter(User.role == UserRole(role))
    active = bool_arg("active")
    if active is not None:
        query = query.filter(User.is_active == active)
    search = str_arg("search").lower()
    if search:
        query = query.filter(func.lower(User.email).like(f"%{search}%"))
    return jsonify(paginate(query.order_by(User.created_at.desc(), User.user_id.desc()), user_row))


@admin_bp.get("/users/<int:user_id>/impact")
@role_required(ADMIN)
def user_impact(user_id):
    impact = _impact(_get_user(user_id))
    impact.pop("_open")
    return jsonify(impact)


@admin_bp.patch("/users/<int:user_id>/deactivate")
@role_required(ADMIN)
def deactivate_user(user_id):
    admin, u = current_user(), _get_user(user_id)
    if u.user_id == admin.user_id:
        raise ApiError("You can't deactivate your own account", 409)
    if not u.is_active:
        raise ApiError("This account is already deactivated", 409)
    if u.role == UserRole.SYSTEM_ADMIN:
        active_admins = User.query.filter_by(role=UserRole.SYSTEM_ADMIN, is_active=True).count()
        if active_admins <= 1:
            raise ApiError("You can't deactivate the last active admin", 409)

    impact = _impact(u)
    closed = withdrawn = 0
    try:
        u.is_active = False
        # A deactivated partner can't manage their opportunities, so close the open ones.
        for o in impact["_open"]:
            o.status = OpportunityStatus.CLOSED
            log_activity("opportunity.closed", actor=admin, target_type="opportunity",
                         target_id=o.opportunity_id,
                         details={"title": o.title, "reason": REASON_DEACTIVATED})
            closed += 1
        if u.role == UserRole.STUDENT and u.student:
            withdrawn = withdraw_all_active(u.student.student_id, REASON_DEACTIVATED, actor=admin)
        log_activity("user.deactivated", actor=admin, target_type="user", target_id=u.user_id,
                     details={"email": u.email, "closed_opportunities": closed,
                              "withdrawn_applications": withdrawn})
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    if closed:
        refit_model()
    return jsonify({"message": "Account deactivated", "user": user_row(u),
                    "closed_opportunities": closed, "withdrawn_applications": withdrawn})


@admin_bp.patch("/users/<int:user_id>/activate")
@role_required(ADMIN)
def activate_user(user_id):
    u = _get_user(user_id)
    if u.is_active:
        raise ApiError("This account is already active", 409)
    u.is_active = True
    log_activity("user.activated", actor=current_user(), target_type="user", target_id=u.user_id,
                 details={"email": u.email})
    db.session.commit()
    return jsonify({"message": "Account activated", "user": user_row(u)})


def _generate_password() -> str:
    """A random temporary password that meets the rules (letters + a digit, 12+ chars)."""
    return f"Wbl{secrets.randbelow(10)}{secrets.token_urlsafe(9)}"


@admin_bp.post("/users/<int:user_id>/reset-password")
@role_required(ADMIN)
def reset_password(user_id):
    u = _get_user(user_id)
    data = request.get_json(silent=True) or {}
    temporary = data.get("temporary_password")
    if temporary in (None, ""):
        temporary = _generate_password()
    elif not isinstance(temporary, str) or (msg := validate_password(temporary)):
        raise ApiError("Validation failed", 400,
                       {"temporary_password": msg if isinstance(temporary, str) else "Must be text"})
    u.set_password(temporary)
    u.must_change_password = True      # they must choose their own password after logging in
    log_activity("user.password_reset", actor=current_user(), target_type="user",
                 target_id=u.user_id, details={"email": u.email})
    db.session.commit()
    # The temporary password is returned this ONE time; it's never stored in plain text.
    return jsonify({"message": "Password reset", "temporary_password": temporary,
                    "user": user_row(u)})


@admin_bp.post("/admins")
@role_required(ADMIN)
def create_admin():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    name = data.get("name").strip() if isinstance(data.get("name"), str) else ""
    email = data.get("email").strip().lower() if isinstance(data.get("email"), str) else ""
    password = data.get("password") if isinstance(data.get("password"), str) else ""
    errors = {}
    if not name:
        errors["name"] = "This field is required"
    elif len(name) > 150:
        errors["name"] = "Must be at most 150 characters"
    if not email:
        errors["email"] = "This field is required"
    elif msg := validate_email(email):
        errors["email"] = msg
    if not password:
        errors["password"] = "This field is required"
    elif msg := validate_password(password):
        errors["password"] = msg
    if errors:
        raise ApiError("Validation failed", 400, errors)

    user = create_user_with_profile({"email": email, "password": password,
                                     "role": "system_admin", "name": name})
    log_activity("user.admin_created", actor=current_user(), target_type="user",
                 target_id=user.user_id, details={"email": email})
    db.session.commit()
    return jsonify({"message": "Admin created", "user": user_row(user)}), 201

