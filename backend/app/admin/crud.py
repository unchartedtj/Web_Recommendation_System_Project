"""Admin create / edit / delete for students, industry partners, internships and accounts.

    POST   /api/admin/students              create a student account (same rules as sign-up)
    PUT    /api/admin/students/<id>         edit name, admission no, course, year, email
    DELETE /api/admin/students/<id>         delete the student and everything that is theirs
    POST   /api/admin/partners              create an industry partner account
    PUT    /api/admin/partners/<id>         edit organisation, contact person, phone, email
    DELETE /api/admin/partners/<id>         delete the partner, their internships and related data
    GET    /api/admin/opportunities/<id>    one internship (for the edit form)
    POST   /api/admin/opportunities         post an internship on behalf of a partner
    PUT    /api/admin/opportunities/<id>    edit an internship (same validation as partners)
    DELETE /api/admin/opportunities/<id>    delete an internship with its applications/placements
    DELETE /api/admin/users/<id>            delete any account (not yourself, not the last admin)
"""
from flask import jsonify

from app.activity import log_activity
from app.admin import admin_bp
from app.admin.common import ADMIN
from app.admin.deletion import delete_account, delete_opportunity, delete_partner, delete_student
from app.auth.decorators import current_user, role_required
from app.auth.services import create_user_with_profile
from app.auth.validators import validate_registration
from app.errors import ApiError
from app.extensions import db
from app.models import IndustryPartner, InternshipOpportunity, Student, User, UserRole
from app.opportunities.services import (active_sector_ids, active_skill_ids, active_unit_ids,
                                        refit_model, save_opportunity, serialize_opportunity)
from app.opportunities.validators import validate_opportunity
from app.utils import json_body

STUDENT_FIELDS = ("email", "admission_no", "first_name", "last_name", "course", "year_of_study")
PARTNER_FIELDS = ("email", "organization_name", "contact_person", "phone")
# Editing doesn't change the password, but the shared sign-up validator needs one: this
# placeholder passes the password rules and is never saved.
_KEEP_PASSWORD = "Unchanged123"


def _get(model, item_id: int, label: str):
    item = db.session.get(model, item_id)
    if item is None:
        raise ApiError(f"{label} not found", 404)
    return item


def _validate_account(role: str, data: dict) -> dict:
    cleaned, errors = validate_registration({**data, "role": role})
    if errors:
        raise ApiError("Validation failed", 400, errors)
    return cleaned


def _email_taken(email: str, user_id: int) -> bool:
    return User.query.filter(User.email == email, User.user_id != user_id).first() is not None


def _create_account(role: str) -> User:
    data = json_body()
    cleaned = _validate_account(role, data)                 # same rules as the sign-up form
    user = create_user_with_profile(cleaned)                # 409 for a duplicate email/admission no
    log_activity("user.created_by_admin", actor=current_user(), target_type="user",
                 target_id=user.user_id, details={"email": user.email, "role": role})
    db.session.commit()
    return user


# ---- Students -------------------------------------------------------------------------------

def _student_json(s: Student) -> dict:
    return {"student_id": s.student_id, "user_id": s.user_id, "email": s.user.email,
            "admission_no": s.admission_no, "first_name": s.first_name, "last_name": s.last_name,
            "course": s.course, "year_of_study": s.year_of_study}


@admin_bp.post("/students")
@role_required(ADMIN)
def create_student():
    user = _create_account("student")
    return jsonify({"message": "Student created", "student": _student_json(user.student)}), 201


@admin_bp.put("/students/<int:student_id>")
@role_required(ADMIN)
def update_student(student_id):
    s = _get(Student, student_id, "Student")
    data = {**_student_json(s), **json_body(), "password": _KEEP_PASSWORD,
            "confirm_password": _KEEP_PASSWORD}
    cleaned = _validate_account("student", {k: data.get(k) for k in
                                            (*STUDENT_FIELDS, "password", "confirm_password")})
    if _email_taken(cleaned["email"], s.user_id):
        raise ApiError("Email already in use", 409, {"email": "Email already in use"})
    if Student.query.filter(Student.admission_no == cleaned["admission_no"],
                            Student.student_id != s.student_id).first():
        raise ApiError("Admission number already registered", 409,
                       {"admission_no": "Admission number already registered"})
    s.user.email = cleaned["email"]
    for field in ("admission_no", "first_name", "last_name", "course", "year_of_study"):
        setattr(s, field, cleaned[field])
    log_activity("user.updated_by_admin", actor=current_user(), target_type="user",
                 target_id=s.user_id, details={"email": s.user.email, "role": "student"})
    db.session.commit()
    return jsonify({"message": "Student updated", "student": _student_json(s)})


@admin_bp.delete("/students/<int:student_id>")
@role_required(ADMIN)
def remove_student(student_id):
    counts = delete_student(_get(Student, student_id, "Student"), current_user())
    db.session.commit()
    return jsonify({"message": "Student deleted", **counts})


# ---- Industry partners ----------------------------------------------------------------------

def _partner_json(p: IndustryPartner) -> dict:
    return {"partner_id": p.partner_id, "user_id": p.user_id, "email": p.user.email,
            "organization_name": p.organization_name, "contact_person": p.contact_person,
            "phone": p.phone}


@admin_bp.post("/partners")
@role_required(ADMIN)
def create_partner():
    user = _create_account("industry_partner")
    return jsonify({"message": "Partner created", "partner": _partner_json(user.industry_partner)}), 201


@admin_bp.put("/partners/<int:partner_id>")
@role_required(ADMIN)
def update_partner(partner_id):
    p = _get(IndustryPartner, partner_id, "Partner")
    data = {**_partner_json(p), **json_body(), "password": _KEEP_PASSWORD,
            "confirm_password": _KEEP_PASSWORD}
    cleaned = _validate_account("industry_partner", {k: data.get(k) for k in
                                                     (*PARTNER_FIELDS, "password", "confirm_password")})
    if _email_taken(cleaned["email"], p.user_id):
        raise ApiError("Email already in use", 409, {"email": "Email already in use"})
    p.user.email = cleaned["email"]
    for field in ("organization_name", "contact_person", "phone"):
        setattr(p, field, cleaned[field])
    log_activity("user.updated_by_admin", actor=current_user(), target_type="user",
                 target_id=p.user_id, details={"email": p.user.email, "role": "industry_partner"})
    db.session.commit()
    return jsonify({"message": "Partner updated", "partner": _partner_json(p)})


@admin_bp.delete("/partners/<int:partner_id>")
@role_required(ADMIN)
def remove_partner(partner_id):
    counts = delete_partner(_get(IndustryPartner, partner_id, "Partner"), current_user())
    db.session.commit()
    if counts["opportunities"]:
        refit_model()                       # their internships left the recommendation model
    return jsonify({"message": "Partner deleted", **counts})


# ---- Internships ----------------------------------------------------------------------------

def _validated_opportunity(data: dict) -> dict:
    cleaned, errors = validate_opportunity(data, active_unit_ids(), active_skill_ids(),
                                           active_sector_ids())
    if errors:
        raise ApiError("Validation failed", 400, errors)
    return cleaned


@admin_bp.get("/opportunities/<int:opportunity_id>")
@role_required(ADMIN)
def get_opportunity(opportunity_id):
    o = _get(InternshipOpportunity, opportunity_id, "Opportunity")
    return jsonify({"opportunity": serialize_opportunity(o)})


@admin_bp.post("/opportunities")
@role_required(ADMIN)
def create_opportunity():
    data = json_body()
    partner = db.session.get(IndustryPartner, data.get("partner_id")) \
        if isinstance(data.get("partner_id"), int) else None
    errors = {} if partner else {"partner_id": "Choose the company offering this internship"}
    try:
        cleaned = _validated_opportunity(data)
    except ApiError as err:
        errors.update(err.fields)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    o = save_opportunity(cleaned, partner=partner, actor=current_user())   # commits + retrains
    return jsonify({"message": "Internship posted", "opportunity": serialize_opportunity(o)}), 201


@admin_bp.put("/opportunities/<int:opportunity_id>")
@role_required(ADMIN)
def update_opportunity(opportunity_id):
    o = _get(InternshipOpportunity, opportunity_id, "Opportunity")
    cleaned = _validated_opportunity(json_body())
    o = save_opportunity(cleaned, opportunity=o, actor=current_user())    # commits + retrains
    return jsonify({"message": "Internship updated", "opportunity": serialize_opportunity(o)})


@admin_bp.delete("/opportunities/<int:opportunity_id>")
@role_required(ADMIN)
def remove_opportunity(opportunity_id):
    counts = delete_opportunity(_get(InternshipOpportunity, opportunity_id, "Opportunity"),
                                current_user())
    db.session.commit()
    refit_model()
    return jsonify({"message": "Internship deleted", **counts})


# ---- Any account ------------------------------------------------------------------------------

@admin_bp.delete("/users/<int:user_id>")
@role_required(ADMIN)
def remove_user(user_id):
    admin, u = current_user(), _get(User, user_id, "User")
    if u.user_id == admin.user_id:
        raise ApiError("You can't delete your own account", 409)
    if u.role == UserRole.SYSTEM_ADMIN and u.is_active and User.query.filter_by(
            role=UserRole.SYSTEM_ADMIN, is_active=True).count() <= 1:
        raise ApiError("You can't delete the last active admin", 409)
    was_partner = u.role == UserRole.INDUSTRY_PARTNER
    counts = delete_account(u, admin)
    db.session.commit()
    if was_partner and counts.get("opportunities"):
        refit_model()
    return jsonify({"message": "Account deleted", **counts})
