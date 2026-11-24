"""Business rules for applications and placements.

All the rules live here (not in the routes), so they're the same wherever they're used:
the API, the seed command and the tests.

Status flow:
    pending ──► shortlisted ──► accepted   (partner)  → a placement record is created
       │             │      └─► rejected   (partner)
       └─────────────┴────────► withdrawn  (student, or automatically)
accepted, rejected and withdrawn are FINAL: they never change again.
"""
from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.activity import log_activity
from app.errors import ApiError
from app.utils import iso, parse_date
from app.extensions import db
from app.models import (Application, ApplicationStatus, InternshipOpportunity, OpportunityStatus,
                        PlacementRecord, PlacementStatus)
from app.opportunities.services import refit_model
from app.recommendations.services import (latest_marks, match_details, profile_is_complete,
                                          student_skill_ids)
from services.recommendation_engine import get_engine

NOTE_MAX = 500
REASON_MAX = 255
REASON_PLACED_ELSEWHERE = "Placed in another internship"
REASON_POSITIONS_FILLED = "All positions filled"

# Partner actions: which statuses each action is allowed from, and the status it leads to.
PARTNER_ACTIONS = {
    "shortlist": ((ApplicationStatus.PENDING,), ApplicationStatus.SHORTLISTED),
    "accept": (ApplicationStatus.ACTIVE, ApplicationStatus.ACCEPTED),
    "reject": (ApplicationStatus.ACTIVE, ApplicationStatus.REJECTED),
}


def _now() -> datetime:
    """Current UTC time without timezone info (how every timestamp in this project is stored)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_open_for_applications(o: InternshipOpportunity) -> bool:
    return (o.status == OpportunityStatus.OPEN and
            (o.application_deadline is None or o.application_deadline >= date.today()))


def has_placement(student_id: int) -> bool:
    """Does the student already hold an accepted application (a placement)?"""
    return Application.query.filter_by(student_id=student_id,
                                       status=ApplicationStatus.ACCEPTED).first() is not None


def student_application_lookup(student) -> tuple[dict, bool]:
    """({opportunity_id: {"application_id", "status"}}, has_placement) for one student.
    Used to show "Applied" tags and the right Apply button state."""
    lookup = {a.opportunity_id: {"application_id": a.application_id, "status": a.status}
              for a in Application.query.filter_by(student_id=student.student_id)}
    placed = any(a["status"] == ApplicationStatus.ACCEPTED for a in lookup.values())
    return lookup, placed


# ---- Student: apply / withdraw -----------------------------------------------------------

def apply(student, opportunity_id, note=None, acknowledge_below_minimum=False) -> Application:
    """Use case: Apply for Internship. Every rule is checked BEFORE anything is saved."""
    # 1. The note is optional, at most 500 characters.
    if note is not None and not isinstance(note, str):
        raise ApiError("Validation failed", 400, {"motivation_note": "Must be text"})
    note = (note or "").strip() or None
    if note and len(note) > NOTE_MAX:
        raise ApiError("Validation failed", 400,
                       {"motivation_note": f"At most {NOTE_MAX} characters"})

    # 2. The opportunity must exist and still accept applications.
    valid_id = isinstance(opportunity_id, int) and not isinstance(opportunity_id, bool)
    opportunity = db.session.get(InternshipOpportunity, opportunity_id) if valid_id else None
    if opportunity is None:
        raise ApiError("Opportunity not found", 404)
    if not _is_open_for_applications(opportunity):
        raise ApiError("Applications for this internship have closed", 409)

    # 3. The profile must be complete (marks for every unit, skills and interests).
    marks = latest_marks(student.student_id)
    if not profile_is_complete(student, marks):
        raise ApiError("Complete your profile before applying", 409)

    # 4. Only one placement per student.
    if has_placement(student.student_id):
        raise ApiError("You already have a confirmed placement", 409)

    # 5. One application per internship (also after withdrawing).
    if Application.query.filter_by(student_id=student.student_id,
                                   opportunity_id=opportunity.opportunity_id).first():
        raise ApiError("You have already applied to this internship", 409)

    # 6. A fresh match for this opportunity (the engine refits first if it's out of date).
    match = (get_engine().score_student(student.student_id) or {}).get(opportunity.opportunity_id)
    if match is None:
        raise ApiError("Applications for this internship have closed", 409)

    # 7. Below an essential minimum → the student must confirm they understand.
    if not match["meets_requirements"] and acknowledge_below_minimum is not True:
        raise ApiError(
            "You don't meet all the minimum requirements for this internship", 409,
            {"acknowledge_below_minimum": "Please confirm you understand you're below the minimum"},
            extra={"unmet_requirements": match["unmet_requirements"]},
        )

    # 8. Save the application with a frozen snapshot of the match.
    snapshot = {
        "captured_at": iso(_now()),
        **{key: match[key] for key in (
            "match_score", "match_percent", "breakdown", "meets_requirements",
            "unmet_requirements", "missing_essential_skills", "missing_desirable_skills",
            "interest_match")},
        **match_details(opportunity, marks, student_skill_ids(student)),   # units[], skills[]
        "interests": sorted(i.sector.name for i in student.interests if i.sector.is_active),
    }
    now = _now()
    application = Application(
        student_id=student.student_id, opportunity_id=opportunity.opportunity_id,
        status=ApplicationStatus.PENDING, motivation_note=note, profile_snapshot=snapshot,
        match_score_at_apply=match["match_score"],
        meets_requirements_at_apply=match["meets_requirements"],
        application_date=now, updated_at=now,
    )
    db.session.add(application)
    try:
        db.session.flush()
        log_activity("application.submitted", actor=student.user_id, target_type="application",
                     target_id=application.application_id,
                     details={"opportunity": opportunity.title,
                              "match_percent": match["match_percent"],
                              "below_minimum": not match["meets_requirements"]})
        db.session.commit()
    except IntegrityError:
        # Two requests at the same moment: the unique constraint stops the second one.
        db.session.rollback()
        raise ApiError("You have already applied to this internship", 409)
    return application


def _get_application(application_id: int) -> Application:
    application = db.session.get(Application, application_id)
    if application is None:
        raise ApiError("Application not found", 404)
    return application


def _not_allowed(application: Application) -> ApiError:
    return ApiError(f"This application is already {application.status}", 409)


def _set_status(application: Application, status: str, reason: str | None = None, actor=None):
    """Change the status and log it. actor=None means the system did it automatically."""
    log_activity(f"application.{status}", actor=actor, target_type="application",
                 target_id=application.application_id,
                 details={"from": application.status, "reason": reason})
    now = _now()
    application.status = status
    application.status_reason = reason
    application.updated_at = now
    if status in ApplicationStatus.FINAL:
        application.decided_at = now


def withdraw(student, application_id: int) -> Application:
    """The student withdraws their own pending or shortlisted application."""
    application = _get_application(application_id)
    if application.student_id != student.student_id:
        raise ApiError("You can only withdraw your own applications", 403)
    if application.status not in ApplicationStatus.ACTIVE:
        raise _not_allowed(application)
    _set_status(application, ApplicationStatus.WITHDRAWN, actor=student.user_id)
    db.session.commit()
    return application


def withdraw_all_active(student_id: int, reason: str, actor=None) -> int:
    """Withdraw every pending/shortlisted application of a student (e.g. account deactivated).
    Doesn't commit. Returns how many were withdrawn."""
    active = Application.query.filter(Application.student_id == student_id,
                                      Application.status.in_(ApplicationStatus.ACTIVE)).all()
    for application in active:
        _set_status(application, ApplicationStatus.WITHDRAWN, reason, actor=actor)
    return len(active)


# ---- Partner: shortlist / accept / reject ---------------------------------------------------


def partner_decide(partner, application_id: int, data: dict) -> Application:
    """Use case: Review Candidates. The partner shortlists, accepts or rejects an application
    to one of THEIR opportunities."""
    application = _get_application(application_id)
    if application.opportunity.partner_id != partner.partner_id:
        raise ApiError("You can only manage applications to your own opportunities", 403)

    # Validate the request body.
    action = data.get("action")
    if action not in PARTNER_ACTIONS:
        raise ApiError("Validation failed", 400,
                       {"action": "Must be 'shortlist', 'accept' or 'reject'"})
    errors = {}
    reason = data.get("reason")
    if reason is not None and not isinstance(reason, str):
        errors["reason"] = "Must be text"
        reason = None
    reason = (reason or "").strip() or None
    if reason and len(reason) > REASON_MAX:
        errors["reason"] = f"At most {REASON_MAX} characters"
    start = parse_date(data.get("start_date"), "start_date", errors)
    end = parse_date(data.get("end_date"), "end_date", errors)
    if start and end and end <= start:
        errors["end_date"] = "The end date must be after the start date"
    if errors:
        raise ApiError("Validation failed", 400, errors)

    allowed_from, new_status = PARTNER_ACTIONS[action]
    if application.status not in allowed_from:
        raise _not_allowed(application)

    if action == "accept":
        return _accept(application, start, end, actor=partner.user_id)
    _set_status(application, new_status, reason if action == "reject" else None,
                actor=partner.user_id)
    db.session.commit()
    return application


def _accept(application: Application, start_date, end_date, actor=None) -> Application:
    """Accept + create the placement, in ONE transaction.

    The opportunity row is locked (SELECT ... FOR UPDATE), so if two accepts happen at the same
    moment, the second waits and then sees the updated slot count.
    """
    closed_now = False
    try:
        opportunity = (db.session.query(InternshipOpportunity)
                       .filter_by(opportunity_id=application.opportunity_id)
                       .with_for_update().one())
        db.session.refresh(application)              # re-read the status after the lock
        if application.status not in ApplicationStatus.ACTIVE:
            raise _not_allowed(application)
        if has_placement(application.student_id):
            raise ApiError("This student already has a confirmed placement", 409)

        accepted = Application.query.filter_by(opportunity_id=opportunity.opportunity_id,
                                               status=ApplicationStatus.ACCEPTED).count()
        if accepted >= opportunity.slots:
            raise ApiError("All slots are filled", 409)

        # 1. Accept and create the placement record.
        _set_status(application, ApplicationStatus.ACCEPTED, actor=actor)
        placement = PlacementRecord(
            student_id=application.student_id, opportunity_id=opportunity.opportunity_id,
            application_id=application.application_id, status=PlacementStatus.CONFIRMED,
            start_date=start_date, end_date=end_date, created_at=_now())
        db.session.add(placement)
        db.session.flush()
        log_activity("placement.created", actor=actor, target_type="placement",
                     target_id=placement.placement_id,
                     details={"application_id": application.application_id,
                              "opportunity": opportunity.title})

        # 2. The student's other active applications are withdrawn automatically.
        for other in Application.query.filter(
                Application.student_id == application.student_id,
                Application.application_id != application.application_id,
                Application.status.in_(ApplicationStatus.ACTIVE)):
            _set_status(other, ApplicationStatus.WITHDRAWN, REASON_PLACED_ELSEWHERE)

        # 3. All slots filled → close the opportunity and reject everyone still waiting.
        if accepted + 1 >= opportunity.slots:
            opportunity.status = OpportunityStatus.CLOSED
            closed_now = True
            log_activity("opportunity.closed", target_type="opportunity",
                         target_id=opportunity.opportunity_id,
                         details={"title": opportunity.title, "reason": "All positions filled"})
            for other in Application.query.filter(
                    Application.opportunity_id == opportunity.opportunity_id,
                    Application.status.in_(ApplicationStatus.ACTIVE)):
                _set_status(other, ApplicationStatus.REJECTED, REASON_POSITIONS_FILLED)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    if closed_now:
        refit_model()     # the closed opportunity must leave the recommendation model
    return application


# ---- Read helpers and serialisers ---------------------------------------------------------

def status_counts(opportunity_ids) -> dict[int, dict[str, int]]:
    """{opportunity_id: {status: count}} for many opportunities, in one grouped query."""
    counts = {oid: {s: 0 for s in ApplicationStatus.ALL} for oid in opportunity_ids}
    if not counts:
        return counts
    rows = (db.session.query(Application.opportunity_id, Application.status,
                             func.count(Application.application_id))
            .filter(Application.opportunity_id.in_(list(counts)))
            .group_by(Application.opportunity_id, Application.status))
    for oid, status, n in rows:
        counts[oid][status] = n
    return counts


def _placement_dict(p: PlacementRecord | None) -> dict | None:
    if p is None:
        return None
    return {
        "placement_id": p.placement_id,
        "status": p.status,
        "start_date": iso(p.start_date),
        "end_date": iso(p.end_date),
        "created_at": iso(p.created_at),
        "organization": p.opportunity.partner.organization_name,
        "title": p.opportunity.title,
    }


def _match_percent(score) -> float | None:
    return None if score is None else round(score * 100, 2)


def serialize_student_application(a: Application) -> dict:
    """What the student sees on "My Applications"."""
    o = a.opportunity
    return {
        "application_id": a.application_id,
        "status": a.status,
        "status_reason": a.status_reason,
        "application_date": iso(a.application_date),
        "updated_at": iso(a.updated_at),
        "decided_at": iso(a.decided_at),
        "motivation_note": a.motivation_note,
        "match_score_at_apply": a.match_score_at_apply,
        "match_percent_at_apply": _match_percent(a.match_score_at_apply),
        "meets_requirements_at_apply": a.meets_requirements_at_apply,
        "opportunity": {
            "opportunity_id": o.opportunity_id,
            "title": o.title,
            "organization": o.partner.organization_name,
            "sector": o.sector.name if o.sector else None,
            "location": o.location,
            "duration_months": o.duration_months,
            "status": o.status,
            "application_deadline": iso(o.application_deadline),
        },
        "placement": _placement_dict(a.placement_record),
    }


def serialize_candidate(a: Application) -> dict:
    """What the partner sees about one applicant. The email is private until shortlisted."""
    s = a.student
    snap = a.profile_snapshot or {}
    show_email = a.status in (ApplicationStatus.SHORTLISTED, ApplicationStatus.ACCEPTED)
    return {
        "application_id": a.application_id,
        "status": a.status,
        "status_reason": a.status_reason,
        "application_date": iso(a.application_date),
        "decided_at": iso(a.decided_at),
        "motivation_note": a.motivation_note,
        "match_score": a.match_score_at_apply,
        "match_percent": _match_percent(a.match_score_at_apply),
        "meets_requirements": a.meets_requirements_at_apply,
        "breakdown": snap.get("breakdown"),
        "unmet_requirements": snap.get("unmet_requirements", []),
        "missing_essential_skills": snap.get("missing_essential_skills", []),
        "missing_desirable_skills": snap.get("missing_desirable_skills", []),
        "interest_match": snap.get("interest_match"),
        "units": snap.get("units", []),
        "skills": snap.get("skills", []),
        "interests": snap.get("interests", []),
        "student": {
            "student_id": s.student_id,
            "name": f"{s.first_name} {s.last_name}",
            "admission_no": s.admission_no,
            "course": s.course,
            "year_of_study": s.year_of_study,
            "email": s.user.email if show_email else None,
        },
        "placement": _placement_dict(a.placement_record),
    }
