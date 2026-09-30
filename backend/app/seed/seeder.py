"""Idempotent seeding: running it twice leaves the same data (no duplicates).

Units are matched by name, partners by email and opportunities by (partner, title).
Existing rows are updated to match the catalogue. Data left over from an older
catalogue is cleaned up (see _prune_demo_opportunities and _prune_units).
"""
from datetime import date, timedelta

from app.auth.services import create_user_with_profile
from app.extensions import db
from app.models import (AcademicUnit, Grade, InternshipOpportunity, OpportunityPrecursor,
                        OpportunityStatus, User)
from app.seed import catalog
from services.recommendation_engine import get_engine


def _seed_units() -> dict[str, AcademicUnit]:
    by_name = {u.unit_name: u for u in AcademicUnit.query.all()}
    for name in catalog.UNITS:
        unit = by_name.get(name)
        if unit is None:
            unit = by_name[name] = AcademicUnit(unit_name=name)
            db.session.add(unit)
        unit.unit_code = None  # the catalogue identifies units by name only
        unit.is_active = True
    db.session.flush()
    return {name: by_name[name] for name in catalog.UNITS}


def _seed_partners() -> dict:
    partners = {}
    for key, info in catalog.PARTNERS.items():
        user = User.query.filter_by(email=info["email"]).first()
        if user is None:
            # Reuses the registration service (hashing and the user + profile transaction).
            # It commits, so seeding isn't all-or-nothing, but the seed is idempotent:
            # after a failure, just re-run it.
            user = create_user_with_profile({**info, "role": "industry_partner",
                                             "password": catalog.DEMO_PASSWORD})
        partners[key] = user.industry_partner
    return partners


def _seed_opportunities(units: dict, partners: dict) -> list[InternshipOpportunity]:
    seeded = []
    for spec in catalog.OPPORTUNITIES:
        partner = partners[spec["partner"]]
        opp = InternshipOpportunity.query.filter_by(partner_id=partner.partner_id,
                                                    title=spec["title"]).first()
        if opp is None:
            # The deadline and status are set only on first creation, so a re-seed
            # doesn't reopen or extend an opportunity someone changed.
            opp = InternshipOpportunity(partner_id=partner.partner_id, title=spec["title"],
                                        status=OpportunityStatus.OPEN,
                                        application_deadline=date.today() + timedelta(days=60))
            db.session.add(opp)
        for field in ("description", "sector", "location", "duration_months", "slots"):
            setattr(opp, field, spec[field])
        db.session.flush()

        # Re-sync requirements to exactly match the catalogue.
        opp.precursors.clear()
        db.session.flush()
        for name, importance, min_mark in spec["requirements"]:
            opp.precursors.append(OpportunityPrecursor(
                unit_id=units[name].unit_id, importance=importance, min_mark=min_mark))
        seeded.append(opp)
    return seeded


def _prune_demo_opportunities(partners: dict) -> int:
    """Delete demo-partner opportunities that are no longer in the catalogue.

    Only the seed-owned demo accounts are touched; real partners' data never is.
    """
    titles_by_partner = {}
    for spec in catalog.OPPORTUNITIES:
        titles_by_partner.setdefault(partners[spec["partner"]].partner_id, set()).add(spec["title"])
    removed = 0
    for partner_id, titles in titles_by_partner.items():
        for opp in InternshipOpportunity.query.filter_by(partner_id=partner_id):
            if opp.title not in titles:
                db.session.delete(opp)
                removed += 1
    db.session.flush()
    return removed


def _prune_units() -> tuple[int, int]:
    """Remove units that aren't in the catalogue.

    Unreferenced units are deleted. Units that still have grades or requirements are
    deactivated instead, so historical data stays intact.
    Returns (deleted, deactivated).
    """
    deleted = deactivated = 0
    for unit in AcademicUnit.query.filter(AcademicUnit.unit_name.notin_(catalog.UNITS)):
        in_use = (Grade.query.filter_by(unit_id=unit.unit_id).first() is not None or
                  OpportunityPrecursor.query.filter_by(unit_id=unit.unit_id).first() is not None)
        if in_use:
            if unit.is_active:
                unit.is_active = False
                deactivated += 1
        else:
            db.session.delete(unit)
            deleted += 1
    db.session.flush()
    return deleted, deactivated


def seed_all() -> dict:
    try:
        units = _seed_units()
        partners = _seed_partners()
        removed_opps = _prune_demo_opportunities(partners)
        opportunities = _seed_opportunities(units, partners)
        deleted_units, deactivated_units = _prune_units()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    model = get_engine().update_model()
    return {
        "units": len(catalog.UNITS),
        "partners": [p["email"] for p in catalog.PARTNERS.values()],
        "opportunities": len(opportunities),
        "requirements": sum(len(o["requirements"]) for o in catalog.OPPORTUNITIES),
        "removed_opportunities": removed_opps,
        "deleted_units": deleted_units,
        "deactivated_units": deactivated_units,
        "model_units": len(model["vocabulary"]),
        "model_opportunities": len(model["opportunity_ids"]),
    }
