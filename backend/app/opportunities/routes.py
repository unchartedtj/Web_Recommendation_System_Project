"""Units catalog, public opportunity browsing, and partner opportunity management.

Endpoints in this file (all under /api):
    GET   /units                                  any logged-in user
    GET   /opportunities                          any logged-in user (open ones only)
    GET   /opportunities/<id>                     any logged-in user (open ones only)
    POST  /partner/opportunities                  partner: create
    GET   /partner/opportunities                  partner: list MY opportunities
    GET   /partner/opportunities/<id>             partner: one of mine (for the Edit form)
    PUT   /partner/opportunities/<id>             partner: edit one of mine
    PATCH /partner/opportunities/<id>/close       partner: close one of mine

@jwt_required()          → any logged-in user may call it (else 401)
@role_required(PARTNER)  → only industry partners may call it (else 401 / 403)
"""
from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app.auth.decorators import current_partner, role_required
from app.errors import ApiError
from app.extensions import db
from app.models import AcademicUnit, InternshipOpportunity, OpportunityStatus
from app.opportunities import opportunities_bp
from app.opportunities.services import (active_unit_ids, close_opportunity, save_opportunity,
                                        serialize_opportunity, serialize_unit)
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
    data, errors = validate_opportunity(_json_body(), active_unit_ids())
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


@opportunities_bp.get("/opportunities")
@jwt_required()
def browse_opportunities():
    """Use case: Browse Opportunities (open ones only, newest first)."""
    rows = (InternshipOpportunity.query.filter_by(status=OpportunityStatus.OPEN)
            # .desc() = descending (newest first); id breaks ties between same-time posts.
            .order_by(InternshipOpportunity.date_posted.desc(),
                      InternshipOpportunity.opportunity_id.desc()).all())
    return jsonify({"opportunities": [serialize_opportunity(o) for o in rows]})


# <int:opportunity_id> captures the number in the URL and passes it to the function.
@opportunities_bp.get("/opportunities/<int:opportunity_id>")
@jwt_required()
def view_opportunity(opportunity_id):
    """Use case: View Internship Details. Closed opportunities are hidden (404)."""
    o = db.session.get(InternshipOpportunity, opportunity_id)
    if o is None or o.status != OpportunityStatus.OPEN:
        raise ApiError("Opportunity not found", 404)
    return jsonify({"opportunity": serialize_opportunity(o)})


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
