"""Read-only student and partner records, and all opportunities (with close / reopen).

    GET   /api/admin/students?search=&year=&profile_complete=&placement_status=
    GET   /api/admin/students/<id>
    GET   /api/admin/partners?search=
    GET   /api/admin/partners/<id>
    GET   /api/admin/opportunities?partner_id=&sector_id=&status=&search=
    PATCH /api/admin/opportunities/<id>/close
    PATCH /api/admin/opportunities/<id>/reopen   only if the deadline is in the future (or none)
                                                 and slots remain
"""
from datetime import date

from flask import jsonify
from sqlalchemy import func, or_

from app.activity import log_activity
from app.admin import admin_bp
from app.admin.common import (ADMIN, bool_arg, choice_arg, int_arg, iso, paginate,
                              paginate_list, str_arg)
from app.applications.services import serialize_student_application, status_counts
from app.auth.decorators import current_user, role_required
from app.errors import ApiError
from app.extensions import db
from app.models import (AcademicUnit, ApplicationStatus, IndustryPartner, InternshipOpportunity,
                        OpportunityStatus, PlacementRecord, PlacementStatus, Recommendation,
                        Student, User)
from app.opportunities.services import close_opportunity, refit_model
from app.recommendations.routes import serialize_recommendation
from app.recommendations.services import latest_marks, profile_is_complete

PLACEMENT_FILTERS = ("none",) + PlacementStatus.ALL


def _latest_placement(student: Student) -> PlacementRecord | None:
    return (PlacementRecord.query.filter_by(student_id=student.student_id)
            .order_by(PlacementRecord.created_at.desc()).first())


def _placement_json(p: PlacementRecord | None) -> dict | None:
    if p is None:
        return None
    return {"placement_id": p.placement_id, "status": p.status, "start_date": iso(p.start_date),
            "end_date": iso(p.end_date), "company": p.opportunity.partner.organization_name,
            "internship": p.opportunity.title, "status_reason": p.status_reason}


# ---- Students -------------------------------------------------------------------------------

def _student_row(s: Student) -> dict:
    p = _latest_placement(s)
    return {
        "student_id": s.student_id, "user_id": s.user_id,
        "name": f"{s.first_name} {s.last_name}", "email": s.user.email,
        "admission_no": s.admission_no, "course": s.course, "year_of_study": s.year_of_study,
        "is_active": s.user.is_active,
        "profile_complete": profile_is_complete(s),
        "profile_updated_at": iso(s.profile_updated_at),
        "applications": len(s.applications),
        "placement_status": p.status if p else None,
    }


@admin_bp.get("/students")
@role_required(ADMIN)
def list_students():
    query = Student.query.join(User)
    search = str_arg("search").lower()
    if search:
        like = f"%{search}%"
        full_name = func.lower(func.concat(Student.first_name, " ", Student.last_name))
        query = query.filter(or_(full_name.like(like), Student.admission_no.like(like),
                                 func.lower(User.email).like(like)))
    year = int_arg("year")
    if year is not None:
        query = query.filter(Student.year_of_study == year)
    rows = [_student_row(s) for s in query.order_by(Student.last_name, Student.first_name)]

    # These two filters depend on computed values, so they're applied in Python.
    complete = bool_arg("profile_complete")
    if complete is not None:
        rows = [r for r in rows if r["profile_complete"] == complete]
    placement = choice_arg("placement_status", PLACEMENT_FILTERS)
    if placement:
        rows = [r for r in rows if (r["placement_status"] or "none") == placement]
    return jsonify(paginate_list(rows))


@admin_bp.get("/students/<int:student_id>")
@role_required(ADMIN)
def student_detail(student_id):
    s = db.session.get(Student, student_id)
    if s is None:
        raise ApiError("Student not found", 404)
    marks = latest_marks(s.student_id)
    units = {u.unit_id: u.unit_name for u in AcademicUnit.query.all()}
    recs = (Recommendation.query.filter_by(student_id=s.student_id)
            .order_by(Recommendation.rank).limit(5).all())
    return jsonify({"student": {
        **_student_row(s),
        "grades": sorted(({"unit_id": uid, "unit": units.get(uid), "mark": mark}
                          for uid, mark in marks.items()), key=lambda g: g["unit"] or ""),
        "skills": sorted(sk.skill.name for sk in s.skills),
        "interests": sorted(i.sector.name for i in s.interests),
        "top_recommendations": [serialize_recommendation(r) for r in recs],
        "applications_list": [serialize_student_application(a) for a in
                              sorted(s.applications, key=lambda a: a.application_date, reverse=True)],
        "placement": _placement_json(_latest_placement(s)),
    }})


# ---- Partners -------------------------------------------------------------------------------

def _partner_row(p: IndustryPartner) -> dict:
    opps = p.opportunities
    placements = PlacementRecord.query.join(InternshipOpportunity).filter(
        InternshipOpportunity.partner_id == p.partner_id).count()
    return {
        "partner_id": p.partner_id, "user_id": p.user_id,
        "organization_name": p.organization_name, "contact_person": p.contact_person,
        "phone": p.phone, "email": p.user.email, "is_active": p.user.is_active,
        "opportunities": len(opps),
        "open_opportunities": sum(1 for o in opps if o.status == OpportunityStatus.OPEN),
        "placements": placements,
    }


@admin_bp.get("/partners")
@role_required(ADMIN)
def list_partners():
    query = IndustryPartner.query.join(User)
    search = str_arg("search").lower()
    if search:
        like = f"%{search}%"
        query = query.filter(or_(func.lower(IndustryPartner.organization_name).like(like),
                                 func.lower(IndustryPartner.contact_person).like(like),
                                 func.lower(User.email).like(like)))
    return jsonify(paginate(query.order_by(IndustryPartner.organization_name), _partner_row))


@admin_bp.get("/partners/<int:partner_id>")
@role_required(ADMIN)
def partner_detail(partner_id):
    p = db.session.get(IndustryPartner, partner_id)
    if p is None:
        raise ApiError("Partner not found", 404)
    counts = status_counts([o.opportunity_id for o in p.opportunities])
    return jsonify({"partner": {
        **_partner_row(p),
        "opportunity_list": [_opportunity_row(o, counts) for o in
                             sorted(p.opportunities, key=lambda o: o.date_posted, reverse=True)],
    }})


# ---- Opportunities --------------------------------------------------------------------------

def _opportunity_row(o: InternshipOpportunity, counts: dict) -> dict:
    c = counts.get(o.opportunity_id) or {s: 0 for s in ApplicationStatus.ALL}
    return {
        "opportunity_id": o.opportunity_id, "title": o.title, "status": o.status,
        "partner_id": o.partner_id, "organization_name": o.partner.organization_name,
        "sector_id": o.sector_id, "sector": o.sector.name if o.sector else None,
        "location": o.location, "slots": o.slots, "slots_filled": c[ApplicationStatus.ACCEPTED],
        "applicants": sum(c.values()), "application_counts": c,
        "application_deadline": iso(o.application_deadline), "date_posted": iso(o.date_posted),
        "can_reopen": _reopen_problem(o, c) is None,
    }


def _reopen_problem(o: InternshipOpportunity, counts: dict) -> str | None:
    """Why this opportunity can't be reopened, or None if it can."""
    if o.status == OpportunityStatus.OPEN:
        return "This opportunity is already open"
    if o.application_deadline is not None and o.application_deadline <= date.today():
        return "The application deadline has passed. The partner must set a new deadline first."
    if counts.get(ApplicationStatus.ACCEPTED, 0) >= o.slots:
        return "All slots are already filled"
    return None


@admin_bp.get("/opportunities")
@role_required(ADMIN)
def list_opportunities():
    query = InternshipOpportunity.query.join(IndustryPartner)
    partner_id = int_arg("partner_id")
    if partner_id is not None:
        query = query.filter(InternshipOpportunity.partner_id == partner_id)
    sector_id = int_arg("sector_id")
    if sector_id is not None:
        query = query.filter(InternshipOpportunity.sector_id == sector_id)
    status = choice_arg("status", (OpportunityStatus.OPEN, OpportunityStatus.CLOSED))
    if status:
        query = query.filter(InternshipOpportunity.status == status)
    search = str_arg("search").lower()
    if search:
        like = f"%{search}%"
        query = query.filter(or_(func.lower(InternshipOpportunity.title).like(like),
                                 func.lower(IndustryPartner.organization_name).like(like)))
    query = query.order_by(InternshipOpportunity.date_posted.desc(),
                           InternshipOpportunity.opportunity_id.desc())
    page = paginate(query, lambda o: o)
    counts = status_counts([o.opportunity_id for o in page["items"]])
    page["items"] = [_opportunity_row(o, counts) for o in page["items"]]
    return jsonify(page)


def _get_opportunity(opportunity_id: int) -> InternshipOpportunity:
    o = db.session.get(InternshipOpportunity, opportunity_id)
    if o is None:
        raise ApiError("Opportunity not found", 404)
    return o


@admin_bp.patch("/opportunities/<int:opportunity_id>/close")
@role_required(ADMIN)
def admin_close_opportunity(opportunity_id):
    o = _get_opportunity(opportunity_id)
    if o.status == OpportunityStatus.CLOSED:
        raise ApiError("This opportunity is already closed", 409)
    close_opportunity(o, actor=current_user())      # commits and retrains
    counts = status_counts([o.opportunity_id])
    return jsonify({"message": "Opportunity closed", "opportunity": _opportunity_row(o, counts)})


@admin_bp.patch("/opportunities/<int:opportunity_id>/reopen")
@role_required(ADMIN)
def admin_reopen_opportunity(opportunity_id):
    o = _get_opportunity(opportunity_id)
    counts = status_counts([o.opportunity_id])
    problem = _reopen_problem(o, counts[o.opportunity_id])
    if problem:
        raise ApiError(problem, 409)
    o.status = OpportunityStatus.OPEN
    log_activity("opportunity.reopened", actor=current_user(), target_type="opportunity",
                 target_id=o.opportunity_id, details={"title": o.title})
    db.session.commit()
    refit_model()
    return jsonify({"message": "Opportunity reopened",
                    "opportunity": _opportunity_row(o, status_counts([o.opportunity_id]))})

