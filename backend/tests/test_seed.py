"""`flask seed-data` must be safe to run more than once, and must clean up old data."""
from app.auth.services import create_user_with_profile
from app.extensions import db
from app.models import (AcademicUnit, Grade, GradeProfile, IndustryPartner, InternshipOpportunity,
                        OpportunityPrecursor)
from app.seed import catalog
from app.seed.seeder import seed_all


def counts():
    return (AcademicUnit.query.filter_by(is_active=True).count(), IndustryPartner.query.count(),
            InternshipOpportunity.query.count(), OpportunityPrecursor.query.count())


def test_seed_is_idempotent(app):
    seed_all()
    first = counts()
    seed_all()
    assert counts() == first == (12, 2, 5, 15)
    assert sorted(u.unit_name for u in AcademicUnit.query) == sorted(catalog.UNITS)


def test_seed_cleans_up_an_older_catalogue(app, student_payload):
    # Leftovers from an older catalogue:
    #  - "Legacy Retired Unit": only used by a retired demo opportunity → deleted with it
    #  - "Legacy Graded Unit": has a student's grade → kept but deactivated
    #  - "Database Systems" with an old code → reused by name, code cleared
    retired_unit = AcademicUnit(unit_code="OLD-1", unit_name="Legacy Retired Unit")
    graded = AcademicUnit(unit_code="OLD-2", unit_name="Legacy Graded Unit")
    reused = AcademicUnit(unit_code="OLD-3", unit_name="Database Systems")
    db.session.add_all([retired_unit, graded, reused])
    db.session.commit()

    student = create_user_with_profile({**student_payload, "year_of_study": 3}).student
    profile = GradeProfile(student_id=student.student_id)
    db.session.add(profile)
    db.session.flush()
    db.session.add(Grade(profile_id=profile.profile_id, unit_id=graded.unit_id, grade_value=70))

    # A demo partner (as an earlier seed would have created it) with a retired opportunity.
    techcorp = create_user_with_profile({**catalog.PARTNERS["techcorp"], "role": "industry_partner",
                                         "password": catalog.DEMO_PASSWORD}).industry_partner
    retired = InternshipOpportunity(partner_id=techcorp.partner_id, title="Retired Demo Intern",
                                    slots=1, status="open")
    db.session.add(retired)
    db.session.flush()
    db.session.add(OpportunityPrecursor(opportunity_id=retired.opportunity_id,
                                        unit_id=retired_unit.unit_id))
    db.session.commit()

    summary = seed_all()

    assert summary["removed_opportunities"] == 1
    assert db.session.get(InternshipOpportunity, retired.opportunity_id) is None
    assert db.session.get(AcademicUnit, retired_unit.unit_id) is None     # freed, then deleted
    assert db.session.get(AcademicUnit, graded.unit_id).is_active is False  # kept for its grade
    kept = db.session.get(AcademicUnit, reused.unit_id)                   # reused by name
    assert (kept.unit_code, kept.is_active) == (None, True)
    assert counts() == (12, 2, 5, 15)


def test_seed_cli_command(app):
    result = app.test_cli_runner().invoke(args=["seed-data"])
    assert result.exit_code == 0, result.output
    assert "Seed complete" in result.output
