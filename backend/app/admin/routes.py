"""Admin management of the preset skills and sectors lists (role: system_admin).

    GET    /api/admin/skills            all skills, including inactive ones
    POST   /api/admin/skills            {name, category}          → 201 (409 if the name exists)
    PUT    /api/admin/skills/<id>       {name?, category?, is_active?}
    DELETE /api/admin/skills/<id>       deleted if unused, otherwise DEACTIVATED
    (the same four endpoints exist for /api/admin/sectors, with just {name, is_active?})

An item that's still in use (by an opportunity or a student) is never deleted, only
deactivated, so existing data stays intact. Every change retrains the recommendation
model, because the lists affect what the engine can score. (The admin UI comes later.)
"""
from flask import jsonify, request
from sqlalchemy import func

from app.admin import admin_bp
from app.auth.decorators import role_required
from app.errors import ApiError
from app.extensions import db
from app.models import (InternshipOpportunity, OpportunitySkill, Sector, Skill, StudentInterest,
                        StudentSkill)
from app.opportunities.services import refit_model

ADMIN = "system_admin"


def _json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    return data


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


def _check_unique_name(model, id_column, name: str, current_id: int | None = None):
    """409 if another row already has this name (ignoring upper/lower case)."""
    query = model.query.filter(func.lower(model.name) == name.lower())
    if current_id is not None:
        query = query.filter(id_column != current_id)
    if query.first():
        raise ApiError(f'"{name}" already exists', 409, {"name": "This name already exists"})


def _read_is_active(data: dict, errors: dict):
    if "is_active" in data and not isinstance(data["is_active"], bool):
        errors["is_active"] = "Must be true or false"
    return data.get("is_active")


def _skill_json(s: Skill) -> dict:
    return {"skill_id": s.skill_id, "name": s.name, "category": s.category,
            "is_active": s.is_active}


def _sector_json(s: Sector) -> dict:
    return {"sector_id": s.sector_id, "name": s.name, "is_active": s.is_active}


def _get_or_404(model, item_id: int, label: str):
    item = db.session.get(model, item_id)
    if item is None:
        raise ApiError(f"{label} not found", 404)
    return item


def _commit_and_refit():
    db.session.commit()
    refit_model()


# =============================================================================
# Skills
# =============================================================================

@admin_bp.get("/skills")
@role_required(ADMIN)
def list_all_skills():
    skills = Skill.query.order_by(Skill.category, Skill.name).all()
    return jsonify({"skills": [_skill_json(s) for s in skills]})


@admin_bp.post("/skills")
@role_required(ADMIN)
def create_skill():
    data, errors = _json_body(), {}
    name = _text(data, "name", 100, errors, required=True)
    category = _text(data, "category", 50, errors, required=True)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    _check_unique_name(Skill, Skill.skill_id, name)
    skill = Skill(name=name, category=category, is_active=True)
    db.session.add(skill)
    _commit_and_refit()
    return jsonify({"skill": _skill_json(skill)}), 201


@admin_bp.put("/skills/<int:skill_id>")
@role_required(ADMIN)
def update_skill(skill_id):
    skill = _get_or_404(Skill, skill_id, "Skill")
    data, errors = _json_body(), {}
    name = _text(data, "name", 100, errors, required=False)
    category = _text(data, "category", 50, errors, required=False)
    is_active = _read_is_active(data, errors)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    if name is not None:
        _check_unique_name(Skill, Skill.skill_id, name, current_id=skill_id)
        skill.name = name
    if category is not None:
        skill.category = category
    if is_active is not None:
        skill.is_active = is_active
    _commit_and_refit()
    return jsonify({"skill": _skill_json(skill)})


@admin_bp.delete("/skills/<int:skill_id>")
@role_required(ADMIN)
def delete_skill(skill_id):
    skill = _get_or_404(Skill, skill_id, "Skill")
    in_use = (OpportunitySkill.query.filter_by(skill_id=skill_id).first() is not None
              or StudentSkill.query.filter_by(skill_id=skill_id).first() is not None)
    if in_use:
        skill.is_active = False          # keep it for the opportunities/students that use it
        result = "deactivated"
    else:
        db.session.delete(skill)
        result = "deleted"
    _commit_and_refit()
    return jsonify({"result": result, "skill_id": skill_id})


# =============================================================================
# Sectors
# =============================================================================

@admin_bp.get("/sectors")
@role_required(ADMIN)
def list_all_sectors():
    sectors = Sector.query.order_by(Sector.name).all()
    return jsonify({"sectors": [_sector_json(s) for s in sectors]})


@admin_bp.post("/sectors")
@role_required(ADMIN)
def create_sector():
    data, errors = _json_body(), {}
    name = _text(data, "name", 100, errors, required=True)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    _check_unique_name(Sector, Sector.sector_id, name)
    sector = Sector(name=name, is_active=True)
    db.session.add(sector)
    _commit_and_refit()
    return jsonify({"sector": _sector_json(sector)}), 201


@admin_bp.put("/sectors/<int:sector_id>")
@role_required(ADMIN)
def update_sector(sector_id):
    sector = _get_or_404(Sector, sector_id, "Sector")
    data, errors = _json_body(), {}
    name = _text(data, "name", 100, errors, required=False)
    is_active = _read_is_active(data, errors)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    if name is not None:
        _check_unique_name(Sector, Sector.sector_id, name, current_id=sector_id)
        sector.name = name
    if is_active is not None:
        sector.is_active = is_active
    _commit_and_refit()
    return jsonify({"sector": _sector_json(sector)})


@admin_bp.delete("/sectors/<int:sector_id>")
@role_required(ADMIN)
def delete_sector(sector_id):
    sector = _get_or_404(Sector, sector_id, "Sector")
    in_use = (InternshipOpportunity.query.filter_by(sector_id=sector_id).first() is not None
              or StudentInterest.query.filter_by(sector_id=sector_id).first() is not None)
    if in_use:
        sector.is_active = False
        result = "deactivated"
    else:
        db.session.delete(sector)
        result = "deleted"
    _commit_and_refit()
    return jsonify({"result": result, "sector_id": sector_id})
