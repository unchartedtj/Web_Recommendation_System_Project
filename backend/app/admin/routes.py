"""Admin management of the catalogues: skills, sectors and academic units (role: system_admin).

    GET    /api/admin/skills            all skills (+ in_use count), including inactive ones
    POST   /api/admin/skills            {name, category}          → 201 (409 if the name exists)
    PUT    /api/admin/skills/<id>       {name?, category?, is_active?}
    DELETE /api/admin/skills/<id>       deleted if unused, otherwise DEACTIVATED
    (the same endpoints exist for /api/admin/sectors {name} and /api/admin/units {name})

An item that's still in use is never deleted, only deactivated, so existing data stays intact.
Every change retrains the recommendation model.

Units are special: every student must have a mark for every ACTIVE unit. Adding or
re-activating a unit therefore makes every student profile incomplete, so those two actions
need {"confirm": true}; without it the API answers 409 with the number of affected students.
"""
from flask import jsonify
from sqlalchemy import func

from app.activity import log_activity
from app.admin import admin_bp
from app.auth.decorators import current_user, role_required
from app.errors import ApiError
from app.utils import json_body
from app.extensions import db
from app.models import (AcademicUnit, Grade, InternshipOpportunity, OpportunityPrecursor,
                        OpportunitySkill, Sector, Skill, Student, StudentInterest, StudentSkill)
from app.opportunities.services import refit_model
from app.recommendations.services import profile_is_complete

ADMIN = "system_admin"


def _text(data: dict, field: str, max_len: int, errors: dict, required: bool) -> str | None:
    """Read a trimmed text field. Returns None if it wasn't sent (allowed when not required)."""
    if field not in data:
        if required:
            errors[field] = "This field is required"
        return None
    value = data[field].strip() if isinstance(data[field], str) else ""
    if not value:
        errors[field] = "This field is required"
    elif len(value) > max_len:
        errors[field] = f"Must be at most {max_len} characters"
    return value


def _check_unique_name(name_column, id_column, name: str, current_id: int | None = None):
    """409 if another row already has this name (ignoring upper/lower case)."""
    query = db.session.query(id_column).filter(func.lower(name_column) == name.lower())
    if current_id is not None:
        query = query.filter(id_column != current_id)
    if query.first():
        raise ApiError(f'"{name}" already exists', 409, {"name": "This name already exists"})


def _read_is_active(data: dict, errors: dict):
    if "is_active" in data and not isinstance(data["is_active"], bool):
        errors["is_active"] = "Must be true or false"
    return data.get("is_active")


def _get_or_404(model, item_id: int, label: str):
    item = db.session.get(model, item_id)
    if item is None:
        raise ApiError(f"{label} not found", 404)
    return item


def _counts(column) -> dict[int, int]:
    """{id: number of rows} for one foreign-key column, in one grouped query."""
    return dict(db.session.query(column, func.count()).group_by(column).all())


def _commit_and_refit(action: str, target_type: str, target_id: int, details: dict):
    log_activity(action, actor=current_user(), target_type=target_type, target_id=target_id,
                 details=details)
    db.session.commit()
    refit_model()


# ---- "in use" counts ------------------------------------------------------------------------

def skill_usage() -> dict[int, int]:
    opp, stu = _counts(OpportunitySkill.skill_id), _counts(StudentSkill.skill_id)
    return {k: opp.get(k, 0) + stu.get(k, 0) for k in set(opp) | set(stu)}


def sector_usage() -> dict[int, int]:
    opp, stu = _counts(InternshipOpportunity.sector_id), _counts(StudentInterest.sector_id)
    return {k: opp.get(k, 0) + stu.get(k, 0) for k in set(opp) | set(stu)}


def unit_usage() -> dict[int, int]:
    req, grades = _counts(OpportunityPrecursor.unit_id), _counts(Grade.unit_id)
    return {k: req.get(k, 0) + grades.get(k, 0) for k in set(req) | set(grades)}


def _skill_json(s: Skill, usage: dict) -> dict:
    return {"skill_id": s.skill_id, "name": s.name, "category": s.category,
            "is_active": s.is_active, "in_use": usage.get(s.skill_id, 0)}


def _sector_json(s: Sector, usage: dict) -> dict:
    return {"sector_id": s.sector_id, "name": s.name, "is_active": s.is_active,
            "in_use": usage.get(s.sector_id, 0)}


def _unit_json(u: AcademicUnit, usage: dict) -> dict:
    return {"unit_id": u.unit_id, "name": u.unit_name, "is_active": u.is_active,
            "in_use": usage.get(u.unit_id, 0)}


# =============================================================================
# Skills
# =============================================================================

@admin_bp.get("/skills")
@role_required(ADMIN)
def list_all_skills():
    usage = skill_usage()
    skills = Skill.query.order_by(Skill.category, Skill.name).all()
    return jsonify({"skills": [_skill_json(s, usage) for s in skills]})


@admin_bp.post("/skills")
@role_required(ADMIN)
def create_skill():
    data, errors = json_body(), {}
    name = _text(data, "name", 100, errors, required=True)
    category = _text(data, "category", 50, errors, required=True)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    _check_unique_name(Skill.name, Skill.skill_id, name)
    skill = Skill(name=name, category=category, is_active=True)
    db.session.add(skill)
    db.session.flush()
    _commit_and_refit("catalog.skill_created", "skill", skill.skill_id, {"name": name})
    return jsonify({"skill": _skill_json(skill, {})}), 201


@admin_bp.put("/skills/<int:skill_id>")
@role_required(ADMIN)
def update_skill(skill_id):
    skill = _get_or_404(Skill, skill_id, "Skill")
    data, errors = json_body(), {}
    name = _text(data, "name", 100, errors, required=False)
    category = _text(data, "category", 50, errors, required=False)
    is_active = _read_is_active(data, errors)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    if name is not None:
        _check_unique_name(Skill.name, Skill.skill_id, name, current_id=skill_id)
        skill.name = name
    if category is not None:
        skill.category = category
    if is_active is not None:
        skill.is_active = is_active
    _commit_and_refit("catalog.skill_updated", "skill", skill_id,
                      {"name": skill.name, "is_active": skill.is_active})
    return jsonify({"skill": _skill_json(skill, skill_usage())})


@admin_bp.delete("/skills/<int:skill_id>")
@role_required(ADMIN)
def delete_skill(skill_id):
    skill = _get_or_404(Skill, skill_id, "Skill")
    if skill_usage().get(skill_id):
        skill.is_active = False          # keep it for the opportunities/students that use it
        result = "deactivated"
    else:
        db.session.delete(skill)
        result = "deleted"
    _commit_and_refit(f"catalog.skill_{result}", "skill", skill_id, {"name": skill.name})
    return jsonify({"result": result, "skill_id": skill_id})


# =============================================================================
# Sectors
# =============================================================================

@admin_bp.get("/sectors")
@role_required(ADMIN)
def list_all_sectors():
    usage = sector_usage()
    sectors = Sector.query.order_by(Sector.name).all()
    return jsonify({"sectors": [_sector_json(s, usage) for s in sectors]})


@admin_bp.post("/sectors")
@role_required(ADMIN)
def create_sector():
    data, errors = json_body(), {}
    name = _text(data, "name", 100, errors, required=True)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    _check_unique_name(Sector.name, Sector.sector_id, name)
    sector = Sector(name=name, is_active=True)
    db.session.add(sector)
    db.session.flush()
    _commit_and_refit("catalog.sector_created", "sector", sector.sector_id, {"name": name})
    return jsonify({"sector": _sector_json(sector, {})}), 201


@admin_bp.put("/sectors/<int:sector_id>")
@role_required(ADMIN)
def update_sector(sector_id):
    sector = _get_or_404(Sector, sector_id, "Sector")
    data, errors = json_body(), {}
    name = _text(data, "name", 100, errors, required=False)
    is_active = _read_is_active(data, errors)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    if name is not None:
        _check_unique_name(Sector.name, Sector.sector_id, name, current_id=sector_id)
        sector.name = name
    if is_active is not None:
        sector.is_active = is_active
    _commit_and_refit("catalog.sector_updated", "sector", sector_id,
                      {"name": sector.name, "is_active": sector.is_active})
    return jsonify({"sector": _sector_json(sector, sector_usage())})


@admin_bp.delete("/sectors/<int:sector_id>")
@role_required(ADMIN)
def delete_sector(sector_id):
    sector = _get_or_404(Sector, sector_id, "Sector")
    if sector_usage().get(sector_id):
        sector.is_active = False
        result = "deactivated"
    else:
        db.session.delete(sector)
        result = "deleted"
    _commit_and_refit(f"catalog.sector_{result}", "sector", sector_id, {"name": sector.name})
    return jsonify({"result": result, "sector_id": sector_id})


# =============================================================================
# Academic units
# =============================================================================

def _students_made_incomplete() -> int:
    """How many students currently have a complete profile (and would lose it)."""
    return sum(1 for s in Student.query.all() if profile_is_complete(s))


def _require_unit_confirmation(data: dict):
    """Adding or re-activating a unit means every student must enter a new mark."""
    if data.get("confirm") is not True:
        affected = _students_made_incomplete()
        raise ApiError(
            f"This makes every student profile incomplete until they enter a mark for the new "
            f"unit ({affected} students with a complete profile are affected). "
            f"Send confirm: true to continue.",
            409, {"confirm": "Confirmation required"}, extra={"affected_students": affected})


@admin_bp.get("/units")
@role_required(ADMIN)
def list_all_units():
    usage = unit_usage()
    units = AcademicUnit.query.order_by(AcademicUnit.unit_name).all()
    return jsonify({"units": [_unit_json(u, usage) for u in units],
                    "students_with_complete_profile": _students_made_incomplete()})


@admin_bp.post("/units")
@role_required(ADMIN)
def create_unit():
    data, errors = json_body(), {}
    name = _text(data, "name", 200, errors, required=True)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    _check_unique_name(AcademicUnit.unit_name, AcademicUnit.unit_id, name)
    affected = _students_made_incomplete()
    _require_unit_confirmation(data)
    unit = AcademicUnit(unit_name=name, is_active=True)
    db.session.add(unit)
    db.session.flush()
    _commit_and_refit("catalog.unit_created", "unit", unit.unit_id,
                      {"name": name, "profiles_made_incomplete": affected})
    return jsonify({"unit": _unit_json(unit, {}), "profiles_made_incomplete": affected}), 201


@admin_bp.put("/units/<int:unit_id>")
@role_required(ADMIN)
def update_unit(unit_id):
    unit = _get_or_404(AcademicUnit, unit_id, "Unit")
    data, errors = json_body(), {}
    name = _text(data, "name", 200, errors, required=False)
    is_active = _read_is_active(data, errors)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    if is_active is True and not unit.is_active:
        _require_unit_confirmation(data)          # re-activating: everyone needs a mark again
    if name is not None:
        _check_unique_name(AcademicUnit.unit_name, AcademicUnit.unit_id, name, current_id=unit_id)
        unit.unit_name = name
    if is_active is not None:
        unit.is_active = is_active
    _commit_and_refit("catalog.unit_updated", "unit", unit_id,
                      {"name": unit.unit_name, "is_active": unit.is_active})
    return jsonify({"unit": _unit_json(unit, unit_usage())})


@admin_bp.delete("/units/<int:unit_id>")
@role_required(ADMIN)
def delete_unit(unit_id):
    unit = _get_or_404(AcademicUnit, unit_id, "Unit")
    if unit_usage().get(unit_id):
        unit.is_active = False                    # keep the marks and requirements that use it
        result = "deactivated"
    else:
        db.session.delete(unit)
        result = "deleted"
    _commit_and_refit(f"catalog.unit_{result}", "unit", unit_id, {"name": unit.unit_name})
    return jsonify({"result": result, "unit_id": unit_id})
