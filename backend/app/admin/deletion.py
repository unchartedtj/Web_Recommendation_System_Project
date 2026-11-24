"""Permanently deleting students, partners and internships (admin only).

Placement records and applications aren't removed automatically by the database, so they are
deleted first, in the right order: placements → applications → the record itself.
Nothing is committed here; the caller commits (and retrains the model when internships go).
"""
from app.activity import log_activity
from app.extensions import db
from app.models import Application, InternshipOpportunity, PlacementRecord, User, UserRole


def _delete_placements_and_applications(applications) -> tuple[int, int]:
    placements = apps = 0
    for a in list(applications):
        if a.placement_record is not None:
            db.session.delete(a.placement_record)
            placements += 1
        db.session.delete(a)
        apps += 1
    db.session.flush()
    return placements, apps


def delete_opportunity(o: InternshipOpportunity, actor) -> dict:
    title = o.title
    placements, apps = _delete_placements_and_applications(
        Application.query.filter_by(opportunity_id=o.opportunity_id).all())
    log_activity("opportunity.deleted", actor=actor, target_type="opportunity",
                 target_id=o.opportunity_id,
                 details={"title": title, "applications": apps, "placements": placements})
    db.session.delete(o)
    db.session.flush()
    return {"applications": apps, "placements": placements}


def delete_student(student, actor) -> dict:
    user = student.user
    # Placements for this student (normally one), then their applications.
    own_placements = PlacementRecord.query.filter_by(student_id=student.student_id).all()
    placements = len(own_placements)
    for p in own_placements:
        db.session.delete(p)
    db.session.flush()
    for a in student.applications:          # forget the deleted placements in memory too
        db.session.expire(a, ["placement_record"])
    _, apps = _delete_placements_and_applications(student.applications)
    db.session.expire(student, ["applications", "placement_records"])   # already deleted above
    log_activity("user.deleted", actor=actor, target_type="user", target_id=user.user_id,
                 details={"email": user.email, "role": "student",
                          "name": f"{student.first_name} {student.last_name}", "applications": apps})
    # Deleting the user also deletes the student profile, grades, skills, interests,
    # recommendations (relationship cascades).
    db.session.delete(user)
    db.session.flush()
    return {"applications": apps, "placements": placements}


def delete_partner(partner, actor) -> dict:
    user = partner.user
    totals = {"opportunities": 0, "applications": 0, "placements": 0}
    for o in list(partner.opportunities):
        counts = delete_opportunity(o, actor)
        totals["opportunities"] += 1
        totals["applications"] += counts["applications"]
        totals["placements"] += counts["placements"]
    db.session.expire(partner, ["opportunities"])                       # already deleted above
    log_activity("user.deleted", actor=actor, target_type="user", target_id=user.user_id,
                 details={"email": user.email, "role": "industry_partner",
                          "organization": partner.organization_name, **totals})
    db.session.delete(user)
    db.session.flush()
    return totals


def delete_admin(user: User, actor) -> dict:
    log_activity("user.deleted", actor=actor, target_type="user", target_id=user.user_id,
                 details={"email": user.email, "role": "system_admin"})
    db.session.delete(user)
    db.session.flush()
    return {}


def delete_account(user: User, actor) -> dict:
    """Delete any kind of account, with everything that belongs to it."""
    if user.role == UserRole.STUDENT and user.student:
        return delete_student(user.student, actor)
    if user.role == UserRole.INDUSTRY_PARTNER and user.industry_partner:
        return delete_partner(user.industry_partner, actor)
    return delete_admin(user, actor)
