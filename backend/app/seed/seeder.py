"""Idempotent seeding: running it twice leaves the same data (no duplicates).

"Idempotent" = safe to repeat. Instead of blindly INSERTing, every step first looks
for an existing row and updates it ("upsert" = update or insert).

Units are matched by name, partners by email and opportunities by (partner, title).
Existing rows are updated to match the catalogue. Data left over from an older
catalogue is cleaned up (see _prune_demo_opportunities and _prune_units).

Order of work in seed_all():
    1. units, skills, sectors  2. demo partner accounts + default admin
    3. remove retired demo opportunities  4. create/update the 5 demo opportunities
    5. remove units no longer in the catalogue  6. commit, then retrain the model
"""
from datetime import date, datetime, timedelta, timezone

from app.auth.services import create_user_with_profile
from app.extensions import db
from app.models import (AcademicUnit, Application, ApplicationStatus, Grade, GradeProfile,
                        InternshipOpportunity,
                        OpportunityPrecursor, OpportunitySkill, OpportunityStatus, Sector, Skill,
                        StudentInterest, StudentSkill, User)
from app.seed import catalog
from services.recommendation_engine import get_engine


def _seed_units() -> dict[str, AcademicUnit]:
    """Make sure all 12 catalogue units exist and are active. Returns {name: unit}."""
    # Every unit already in the database, keyed by name, e.g. {"Database Systems": <unit>}.
    by_name = {u.unit_name: u for u in AcademicUnit.query.all()}
    for name in catalog.UNITS:
        unit = by_name.get(name)          # None if this unit isn't in the database yet
        if unit is None:
            unit = by_name[name] = AcademicUnit(unit_name=name)
            db.session.add(unit)
        unit.unit_code = None  # the catalogue identifies units by name only
        unit.is_active = True
    db.session.flush()
    return {name: by_name[name] for name in catalog.UNITS}


def _seed_skills() -> dict[str, Skill]:
    """Make sure all preset skills exist. Returns {name: skill}.

    New skills start active. An existing skill keeps its is_active value, so re-seeding
    never re-activates a skill an admin deliberately switched off.
    """
    by_name = {s.name: s for s in Skill.query.all()}
    for name, category in catalog.SKILLS:
        skill = by_name.get(name)
        if skill is None:
            skill = by_name[name] = Skill(name=name, is_active=True)
            db.session.add(skill)
        skill.category = category
    db.session.flush()
    return by_name


def _seed_sectors() -> dict[str, Sector]:
    """Make sure all preset sectors exist. Returns {name: sector}. (Same rules as skills.)"""
    by_name = {s.name: s for s in Sector.query.all()}
    for name in catalog.SECTORS:
        if name not in by_name:
            by_name[name] = Sector(name=name, is_active=True)
            db.session.add(by_name[name])
    db.session.flush()
    return by_name


def _seed_partners() -> dict:
    """Create the two demo partner accounts if missing. Returns {"techcorp": partner, ...}."""
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


def _seed_admin() -> str | None:
    """Create the default system admin (username "Admin") if no admin has that name yet.

    Returns the password if the admin was created now (so it can be printed ONCE), else None.
    An existing admin is left alone, so re-seeding never resets a password.
    """
    import secrets

    from sqlalchemy import func

    from app.auth.validators import validate_password
    from app.models import SystemAdmin

    info = catalog.DEFAULT_ADMIN
    exists = (SystemAdmin.query.filter(func.lower(SystemAdmin.name) == info["name"].lower()).first()
              or User.query.filter_by(email=info["email"]).first())
    if exists:
        return None
    password = info["password"]
    if not password or validate_password(password):
        # No (valid) password configured: generate a strong one, e.g. "Wbl-Admin-7fK2m9Qp".
        password = f"Wbl-Admin-{secrets.randbelow(10)}{secrets.token_urlsafe(8)}"
    # Same function the register endpoint and `flask create-admin` use (hashes the password,
    # creates the users row + system_admins row together).
    create_user_with_profile({"email": info["email"], "password": password,
                              "role": "system_admin", "name": info["name"]})
    return password


def _seed_demo_students(units: dict, skills: dict, sectors: dict) -> list:
    """Create the demo student accounts and (for those with one) their profile.

    A grade profile is only created if the student has none yet, so re-seeding doesn't
    pile up grade history. Skills and interests are re-synced every time.
    Returns the Student rows that have a complete profile.
    """
    complete = []
    for spec in catalog.DEMO_STUDENTS:
        user = User.query.filter_by(email=spec["email"]).first()
        if user is None:
            user = create_user_with_profile({
                "email": spec["email"], "password": catalog.DEMO_PASSWORD, "role": "student",
                **{k: spec[k] for k in ("admission_no", "first_name", "last_name", "course",
                                        "year_of_study")}})
        student = user.student
        profile = spec["profile"]
        if profile is None:
            continue

        if GradeProfile.query.filter_by(student_id=student.student_id).first() is None:
            gp = GradeProfile(student_id=student.student_id)
            db.session.add(gp)
            db.session.flush()
            for i, name in enumerate(catalog.UNITS):
                base = 56 + (i * 5) % 13            # 56..68, varied from unit to unit
                mark = profile["marks"].get(name, base)
                db.session.add(Grade(profile_id=gp.profile_id, unit_id=units[name].unit_id,
                                     grade_value=mark))
            student.profile_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        student.skills.clear()
        student.interests.clear()
        db.session.flush()
        for name in profile["skills"]:
            student.skills.append(StudentSkill(skill_id=skills[name].skill_id))
        for name in profile["interests"]:
            student.interests.append(StudentInterest(sector_id=sectors[name].sector_id))
        if student.profile_updated_at is None:
            student.profile_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        complete.append(student)
    db.session.flush()
    return complete


def _seed_opportunities(units: dict, partners: dict, skills: dict,
                        sectors: dict) -> list[InternshipOpportunity]:
    """Create or update the 5 demo opportunities, their sector, unit requirements and skills."""
    seeded = []
    for spec in catalog.OPPORTUNITIES:   # `spec` = one opportunity's details from catalog.py
        partner = partners[spec["partner"]]
        # Read the sector id BEFORE adding a new opportunity: reading it can trigger a query,
        # and SQLAlchemy would then save the half-built opportunity (with no sector) first.
        sector_id = sectors[spec["sector"]].sector_id
        # Does this partner already have an opportunity with this title?
        opp = InternshipOpportunity.query.filter_by(partner_id=partner.partner_id,
                                                    title=spec["title"]).first()
        if opp is None:
            # The deadline and status are set only on first creation, so a re-seed
            # doesn't reopen or extend an opportunity someone changed.
            opp = InternshipOpportunity(partner_id=partner.partner_id, title=spec["title"],
                                        sector_id=sector_id, status=OpportunityStatus.OPEN,
                                        application_deadline=date.today() + timedelta(days=60))
            db.session.add(opp)
        for field in ("description", "location", "duration_months", "slots"):
            setattr(opp, field, spec[field])
        opp.sector_id = sector_id
        db.session.flush()

        # Re-sync unit requirements and required skills to exactly match the catalogue.
        opp.precursors.clear()
        opp.skills.clear()
        db.session.flush()
        for name, importance, min_mark in spec["requirements"]:
            opp.precursors.append(OpportunityPrecursor(
                unit_id=units[name].unit_id, importance=importance, min_mark=min_mark))
        for name, importance in spec["skills"]:
            opp.skills.append(OpportunitySkill(skill_id=skills[name].skill_id,
                                               importance=importance))
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
                if opp.applications:
                    # Students applied to it: keep the history, just close it.
                    opp.status = OpportunityStatus.CLOSED
                else:
                    db.session.delete(opp)
                removed += 1
    db.session.flush()
    return removed


def _seed_demo_applications() -> int:
    """Create the demo applications with the real apply() rules. Safe to re-run: skips any
    that already exist, students with a placement, and closed/expired opportunities.
    Returns how many were created."""
    from app.applications.services import apply, has_placement
    from app.errors import ApiError

    by_key = {spec["key"]: spec for spec in catalog.OPPORTUNITIES}
    created = 0
    for email, key, status, note, below_minimum_ok in catalog.DEMO_APPLICATIONS:
        user = User.query.filter_by(email=email).first()
        spec = by_key[key]
        partner = User.query.filter_by(email=catalog.PARTNERS[spec["partner"]]["email"]).first()
        if user is None or user.student is None or partner is None:
            continue
        student = user.student
        opp = InternshipOpportunity.query.filter_by(
            partner_id=partner.industry_partner.partner_id, title=spec["title"]).first()
        if opp is None or has_placement(student.student_id):
            continue
        if Application.query.filter_by(student_id=student.student_id,
                                       opportunity_id=opp.opportunity_id).first():
            continue                                     # already applied (re-run)
        try:
            application = apply(student, opp.opportunity_id, note=note,
                                acknowledge_below_minimum=below_minimum_ok)
        except ApiError:
            continue                                     # e.g. closed or past its deadline
        if status == ApplicationStatus.SHORTLISTED:
            application.status = ApplicationStatus.SHORTLISTED
            db.session.commit()
        created += 1
    return created


def _prune_units() -> tuple[int, int]:
    """Remove units that aren't in the catalogue.

    Unreferenced units are deleted. Units that still have grades or requirements are
    deactivated instead, so historical data stays intact.
    Returns (deleted, deactivated).
    """
    deleted = deactivated = 0
    # Every unit whose name is NOT in the catalogue list (notin_ = SQL "NOT IN").
    for unit in AcademicUnit.query.filter(AcademicUnit.unit_name.notin_(catalog.UNITS)):
        # "In use" = at least one grade or requirement still points at this unit.
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


def seed_all(include_demo_students: bool = True) -> dict:
    """Run every seeding step, then retrain the model. Returns counts for the CLI printout.

    include_demo_students=False skips the 3 demo students (most tests use this, so their
    row counts only see the data each test creates itself).
    """
    try:
        # flush() inside each step sends the changes to MySQL; commit() at the end saves them.
        units = _seed_units()
        skills = _seed_skills()
        sectors = _seed_sectors()
        partners = _seed_partners()
        admin_password = _seed_admin()
        removed_opps = _prune_demo_opportunities(partners)
        opportunities = _seed_opportunities(units, partners, skills, sectors)
        deleted_units, deactivated_units = _prune_units()
        demo_students = (_seed_demo_students(units, skills, sectors)
                         if include_demo_students else [])
        demo_student_ids = [s.student_id for s in demo_students]
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    # The open opportunities may have changed, so retrain the recommendation model.
    engine = get_engine()
    model = engine.update_model()
    # Give the demo students with a profile fresh recommendations.
    for student_id in demo_student_ids:
        engine.generate_recommendations(student_id)
    # Demo applications need the fitted model (each one stores a match snapshot).
    applications = _seed_demo_applications() if include_demo_students else 0
    return {
        "applications": applications,
        "units": len(catalog.UNITS),
        "partners": [p["email"] for p in catalog.PARTNERS.values()],
        "students": [s["email"] for s in catalog.DEMO_STUDENTS],
        "admin_created": admin_password is not None,
        "admin_password": admin_password,      # only set when created now
        "opportunities": len(opportunities),
        "requirements": sum(len(o["requirements"]) for o in catalog.OPPORTUNITIES),
        "skills": len(catalog.SKILLS),
        "sectors": len(catalog.SECTORS),
        "skill_requirements": sum(len(o["skills"]) for o in catalog.OPPORTUNITIES),
        "model_skills": len(model["skill_vocabulary"]),
        "removed_opportunities": removed_opps,
        "deleted_units": deleted_units,
        "deactivated_units": deactivated_units,
        "model_units": len(model["vocabulary"]),
        "model_opportunities": len(model["opportunity_ids"]),
    }
