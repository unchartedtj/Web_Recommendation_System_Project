"""Units catalog, public opportunity browsing, and partner opportunity management.

Endpoints in this file (all under /api):
    GET   /units                                  any logged-in user
    GET   /skills                                 any logged-in user (grouped by category)
    GET   /sectors                                any logged-in user
    GET   /opportunities                          any logged-in user (open, deadline not passed)
                                                  ?search= &sector_id= &skill_id= &sort=newest|deadline|best_match
    GET   /opportunities/<id>                     any logged-in user (open ones only;
                                                  students also get a "my_match" block)
    POST  /partner/opportunities                  partner: create
    GET   /partner/opportunities                  partner: list MY opportunities
    GET   /partner/opportunities/<id>             partner: one of mine (for the Edit form)
    PUT   /partner/opportunities/<id>             partner: edit one of mine
    PATCH /partner/opportunities/<id>/close       partner: close one of mine

@jwt_required()          → any logged-in user may call it (else 401)
@role_required(PARTNER)  → only industry partners may call it (else 401 / 403)
"""
from datetime import date

from flask import jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from sqlalchemy import func, or_

from app.auth.decorators import current_partner, current_user, role_required
from app.errors import ApiError
from app.extensions import db
from app.models import (AcademicUnit, IndustryPartner, InternshipOpportunity, OpportunitySkill,
                        OpportunityStatus, Sector, Skill)
from app.recommendations.services import (latest_marks, match_details, profile_is_complete,
                                          student_skill_ids)
from services.recommendation_engine import get_engine
from app.opportunities import opportunities_bp
from app.opportunities.services import (active_sector_ids, active_skill_ids, active_unit_ids,
                                        close_opportunity, save_opportunity,
                                        serialize_opportunity, serialize_unit,
                                        skills_by_category)
from app.opportunities.validators import validate_opportunity

PARTNER = "industry_partner"


def _json_body() -> dict:
    """Read the request body as JSON. Anything that isn't a JSON object → 400."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    return data


def _validated_body() -> dict:
    """Read AND validate an opportunity body. Any problem → 400 with field errors."""
    data, errors = validate_opportunity(_json_body(), active_unit_ids(), active_skill_ids(),
                                        active_sector_ids())
    if errors:
        raise ApiError("Validation failed", 400, errors)
    return data


def _own_opportunity(opportunity_id: int) -> InternshipOpportunity:
    """Fetch an opportunity the logged-in partner owns: 404 if it doesn't exist,
    403 if it belongs to another partner."""
    opportunity = db.session.get(InternshipOpportunity, opportunity_id)   # look up by primary key
    if opportunity is None:
        raise ApiError("Opportunity not found", 404)
    # The ownership check: the opportunity's partner must be the logged-in partner.
    if opportunity.partner_id != current_partner().partner_id:
        raise ApiError("You can only manage your own opportunities", 403)
    return opportunity


# ---- Any logged-in user -----------------------------------------------------------

@opportunities_bp.get("/units")
@jwt_required()
def list_units():
    """The unit catalogue (used for the requirement dropdown on the Post Opportunity form)."""
    # Alphabetical: unit_id order isn't meaningful, because units reused across
    # catalogue changes keep their original ids.
    units = AcademicUnit.query.filter_by(is_active=True).order_by(AcademicUnit.unit_name).all()
    return jsonify({"units": [serialize_unit(u) for u in units]})


@opportunities_bp.get("/skills")
@jwt_required()
def list_skills():
    """The preset skills, grouped by category (for the partner form and the student profile)."""
    skills = Skill.query.filter_by(is_active=True).all()
    return jsonify({"categories": skills_by_category(skills)})


@opportunities_bp.get("/sectors")
@jwt_required()
def list_sectors():
    """The preset sectors (an internship's sector, and a student's career-interest options)."""
    sectors = Sector.query.filter_by(is_active=True).order_by(Sector.name).all()
    return jsonify({"sectors": [{"sector_id": s.sector_id, "name": s.name} for s in sectors]})


SORTS = ("newest", "deadline", "best_match")


def _int_param(name: str):
    """Read an optional whole-number query parameter (e.g. ?sector_id=3). Bad value → 400."""
    raw = request.args.get(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise ApiError(f"{name} must be a number", 400, {name: "Must be a number"})


def _student_context():
    """If the caller is a student with a COMPLETE profile, return
    (student, live match results {opportunity_id: result}, marks, skill ids); otherwise None."""
    if get_jwt().get("role") != "student":
        return None
    student = current_user().student
    if student is None:
        return None
    marks = latest_marks(student.student_id)
    if not profile_is_complete(student, marks):
        return None
    matches = get_engine().score_student(student.student_id)
    if matches is None:
        return None
    return student, matches, marks, student_skill_ids(student)


@opportunities_bp.get("/opportunities")
@jwt_required()
def browse_opportunities():
    """Use case: Browse Opportunities.

    Only open opportunities whose deadline hasn't passed. Optional filters:
      search    – text in the title OR the company name (upper/lower case ignored)
      sector_id – only this sector
      skill_id  – only opportunities that require this skill
      sort      – newest (default) | deadline (soonest first) | best_match (students with a
                  complete profile; otherwise falls back to newest, and the reply says so)
    Students with a complete profile also get their match_percent on each item.
    """
    search = request.args.get("search", "").strip()
    sector_id, skill_id = _int_param("sector_id"), _int_param("skill_id")
    sort = request.args.get("sort", "newest").strip() or "newest"
    if sort not in SORTS:
        raise ApiError(f"sort must be one of {', '.join(SORTS)}", 400, {"sort": "Invalid sort"})

    query = (InternshipOpportunity.query.join(IndustryPartner)
             .filter(InternshipOpportunity.status == OpportunityStatus.OPEN)
             # No deadline, or a deadline today or later.
             .filter(or_(InternshipOpportunity.application_deadline.is_(None),
                         InternshipOpportunity.application_deadline >= date.today())))
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(or_(func.lower(InternshipOpportunity.title).like(like),
                                 func.lower(IndustryPartner.organization_name).like(like)))
    if sector_id is not None:
        query = query.filter(InternshipOpportunity.sector_id == sector_id)
    if skill_id is not None:
        # .any(...) = "has at least one required-skill row with this skill".
        query = query.filter(InternshipOpportunity.skills.any(OpportunitySkill.skill_id == skill_id))

    context = _student_context()
    if sort == "best_match" and context is None:
        sort = "newest"                     # best match needs a complete student profile

    if sort == "deadline":
        # Soonest first; opportunities without a deadline go last.
        query = query.order_by(InternshipOpportunity.application_deadline.is_(None),
                               InternshipOpportunity.application_deadline,
                               InternshipOpportunity.opportunity_id)
    else:
        query = query.order_by(InternshipOpportunity.date_posted.desc(),
                               InternshipOpportunity.opportunity_id.desc())
    rows = query.all()

    items = []
    for o in rows:
        item = serialize_opportunity(o)
        if context:
            match = context[1].get(o.opportunity_id)
            if match:
                item.update({"match_score": match["match_score"],
                             "match_percent": match["match_percent"],
                             "meets_requirements": match["meets_requirements"],
                             "match_rank": match["rank"]})
        items.append(item)
    if sort == "best_match":
        # The engine's own order: eligible first, then by match score.
        items.sort(key=lambda i: i.get("match_rank", 10**6))

    return jsonify({"opportunities": items, "sort": sort, "profile_complete": context is not None})


# <int:opportunity_id> captures the number in the URL and passes it to the function.
@opportunities_bp.get("/opportunities/<int:opportunity_id>")
@jwt_required()
def view_opportunity(opportunity_id):
    """Use case: View Internship Details. Closed or unknown opportunities → 404.

    A student with a complete profile also gets "my_match": their score breakdown and a
    side-by-side comparison of the requirements with their own marks and skills.
    """
    o = db.session.get(InternshipOpportunity, opportunity_id)
    if o is None or o.status != OpportunityStatus.OPEN:
        raise ApiError("Opportunity not found", 404)

    body = {"opportunity": serialize_opportunity(o), "profile_complete": False}
    context = _student_context()
    if context:
        _student, matches, marks, skill_ids = context
        match = matches.get(o.opportunity_id)
        if match:
            body["profile_complete"] = True
            body["my_match"] = {
                key: match[key] for key in (
                    "match_score", "match_percent", "breakdown", "meets_requirements",
                    "unmet_requirements", "missing_essential_skills",
                    "missing_desirable_skills", "interest_match")
            } | match_details(o, marks, skill_ids)    # adds units[] and skills[]
    return jsonify(body)


# ---- Industry partner: own opportunities --------------------------------------------

@opportunities_bp.post("/partner/opportunities")
@role_required(PARTNER)
def create_opportunity():
    """Post a new opportunity. The logged-in partner becomes its owner."""
    data = _validated_body()
    opportunity = save_opportunity(data, partner=current_partner())
    return jsonify({"message": "Opportunity posted",
                    "opportunity": serialize_opportunity(opportunity)}), 201


@opportunities_bp.get("/partner/opportunities")
@role_required(PARTNER)
def my_opportunities():
    """The "My Opportunities" table: only this partner's rows, open AND closed."""
    rows = (InternshipOpportunity.query.filter_by(partner_id=current_partner().partner_id)
            .order_by(InternshipOpportunity.date_posted.desc(),
                      InternshipOpportunity.opportunity_id.desc()).all())
    return jsonify({"opportunities": [serialize_opportunity(o) for o in rows]})


@opportunities_bp.get("/partner/opportunities/<int:opportunity_id>")
@role_required(PARTNER)
def get_my_opportunity(opportunity_id):
    """Used by the Edit form (includes closed opportunities, unlike the public view)."""
    return jsonify({"opportunity": serialize_opportunity(_own_opportunity(opportunity_id))})


@opportunities_bp.put("/partner/opportunities/<int:opportunity_id>")
@role_required(PARTNER)
def update_opportunity(opportunity_id):
    """Edit details and REPLACE the requirement list."""
    opportunity = _own_opportunity(opportunity_id)  # ownership checked before validation
    data = _validated_body()
    opportunity = save_opportunity(data, opportunity=opportunity)
    return jsonify({"message": "Opportunity updated",
                    "opportunity": serialize_opportunity(opportunity)})


@opportunities_bp.patch("/partner/opportunities/<int:opportunity_id>/close")
@role_required(PARTNER)
def close(opportunity_id):
    """Close an opportunity: hidden from students and removed from recommendations."""
    opportunity = close_opportunity(_own_opportunity(opportunity_id))
    return jsonify({"message": "Opportunity closed",
                    "opportunity": serialize_opportunity(opportunity)})
