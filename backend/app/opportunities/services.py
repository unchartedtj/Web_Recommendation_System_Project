"""Opportunity persistence and serialisation."""
import logging

from app.extensions import db
from app.models import (AcademicUnit, InternshipOpportunity, OpportunityPrecursor,
                        OpportunityStatus, RequirementImportance)
from services.recommendation_engine import get_engine

log = logging.getLogger(__name__)

DETAIL_FIELDS = ("title", "description", "sector", "location",
                 "duration_months", "slots", "application_deadline")


def active_unit_ids() -> set[int]:
    return {uid for (uid,) in db.session.query(AcademicUnit.unit_id).filter_by(is_active=True)}


def _refit_model():
    """Refit the engine after any change to open opportunities.

    The DB change is already committed, so a refit failure is only logged. The engine's
    staleness check (ensure_fresh) will refit on the next recommendation request.
    """
    try:
        get_engine().update_model()
    except Exception:
        log.exception("Recommendation model refit failed; it will refit on next use")


def _replace_requirements(opportunity: InternshipOpportunity, requirements: list[dict]):
    # Delete the old rows and flush before inserting, so re-adding a unit
    # doesn't collide with the composite primary key.
    opportunity.precursors.clear()
    db.session.flush()
    for req in requirements:
        opportunity.precursors.append(OpportunityPrecursor(
            unit_id=req["unit_id"], importance=req["importance"], min_mark=req["min_mark"]))


def save_opportunity(data: dict, *, partner=None, opportunity=None) -> InternshipOpportunity:
    """Create (partner given) or update (opportunity given) the opportunity and its
    requirements in ONE transaction."""
    try:
        if opportunity is None:
            opportunity = InternshipOpportunity(partner_id=partner.partner_id,
                                                status=OpportunityStatus.OPEN)
            db.session.add(opportunity)
        for field in DETAIL_FIELDS:
            setattr(opportunity, field, data[field])
        db.session.flush()  # assigns opportunity_id for new rows
        _replace_requirements(opportunity, data["requirements"])
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    _refit_model()
    return opportunity


def close_opportunity(opportunity: InternshipOpportunity) -> InternshipOpportunity:
    if opportunity.status != OpportunityStatus.CLOSED:
        opportunity.status = OpportunityStatus.CLOSED
        db.session.commit()
        _refit_model()
    return opportunity


def serialize_opportunity(o: InternshipOpportunity) -> dict:
    # Essential requirements first, then by unit name, for consistent display.
    reqs = sorted(o.precursors, key=lambda p: (p.importance != RequirementImportance.ESSENTIAL,
                                               p.unit.unit_name))
    return {
        "opportunity_id": o.opportunity_id,
        "partner_id": o.partner_id,
        "organization_name": o.partner.organization_name if o.partner else None,
        "title": o.title,
        "description": o.description,
        "sector": o.sector,
        "location": o.location,
        "duration_months": o.duration_months,
        "slots": o.slots,
        "application_deadline": o.application_deadline.isoformat() if o.application_deadline else None,
        "status": o.status,
        "date_posted": o.date_posted.isoformat() if o.date_posted else None,
        "requirements": [{
            "unit_id": p.unit_id,
            "unit_name": p.unit.unit_name,
            "importance": p.importance,
            "min_mark": None if p.min_mark is None else float(p.min_mark),
        } for p in reqs],
    }


def serialize_unit(u: AcademicUnit) -> dict:
    return {"unit_id": u.unit_id, "unit_name": u.unit_name}
