"""Applications (student side) and candidates (partner side).

Endpoints in this file (all under /api):
    POST  /applications                                   student: apply
    GET   /applications/mine?status=                      student: my applications (+ placement)
    PATCH /applications/<id>/withdraw                     student: withdraw my application
    GET   /partner/opportunities/<id>/candidates?status=  partner: applicants to MY opportunity
    PATCH /partner/applications/<id>                      partner: shortlist / accept / reject

The rules themselves are in services.py; these functions only read the request,
call the service and send back JSON.
"""
from flask import jsonify, request

from app.applications import applications_bp
from app.applications.services import (apply, partner_decide, serialize_candidate,
                                       serialize_student_application, status_counts, withdraw)
from app.auth.decorators import current_partner, current_student, role_required
from app.errors import ApiError
from app.utils import json_body
from app.extensions import db
from app.models import Application, ApplicationStatus, InternshipOpportunity

STUDENT, PARTNER = "student", "industry_partner"


def _status_filter():
    """Optional ?status= filter. Unknown status → 400."""
    status = request.args.get("status", "").strip()
    if not status:
        return None
    if status not in ApplicationStatus.ALL:
        raise ApiError("Unknown status", 400,
                       {"status": f"Must be one of {', '.join(ApplicationStatus.ALL)}"})
    return status


# ---- Student ------------------------------------------------------------------------------

@applications_bp.post("/applications")
@role_required(STUDENT)
def create_application():
    data = json_body()
    application = apply(current_student(), data.get("opportunity_id"),
                        note=data.get("motivation_note"),
                        acknowledge_below_minimum=data.get("acknowledge_below_minimum") is True)
    return jsonify({"message": "Application submitted",
                    "application": serialize_student_application(application)}), 201


@applications_bp.get("/applications/mine")
@role_required(STUDENT)
def my_applications():
    """The student's applications (newest first), with the placement for an accepted one."""
    query = Application.query.filter_by(student_id=current_student().student_id)
    status = _status_filter()
    if status:
        query = query.filter_by(status=status)
    rows = query.order_by(Application.application_date.desc(),
                          Application.application_id.desc()).all()
    return jsonify({"applications": [serialize_student_application(a) for a in rows]})


@applications_bp.patch("/applications/<int:application_id>/withdraw")
@role_required(STUDENT)
def withdraw_application(application_id):
    application = withdraw(current_student(), application_id)
    return jsonify({"message": "Application withdrawn",
                    "application": serialize_student_application(application)})


# ---- Industry partner ---------------------------------------------------------------------

@applications_bp.get("/partner/opportunities/<int:opportunity_id>/candidates")
@role_required(PARTNER)
def candidates(opportunity_id):
    """Applicants to one of the partner's opportunities, best match first."""
    opportunity = db.session.get(InternshipOpportunity, opportunity_id)
    if opportunity is None:
        raise ApiError("Opportunity not found", 404)
    if opportunity.partner_id != current_partner().partner_id:
        raise ApiError("You can only view candidates for your own opportunities", 403)

    status = _status_filter()
    query = Application.query.filter_by(opportunity_id=opportunity_id)
    if status:
        query = query.filter_by(status=status)
    rows = sorted(query.all(), key=lambda a: (-(a.match_score_at_apply or 0), a.application_id))
    counts = status_counts([opportunity_id])[opportunity_id]
    return jsonify({
        "opportunity": {
            "opportunity_id": opportunity.opportunity_id,
            "title": opportunity.title,
            "status": opportunity.status,
            "slots": opportunity.slots,
            "slots_filled": counts[ApplicationStatus.ACCEPTED],
            "application_deadline": (opportunity.application_deadline.isoformat()
                                     if opportunity.application_deadline else None),
        },
        "counts": {**counts, "all": sum(counts.values())},
        "candidates": [serialize_candidate(a) for a in rows],
    })


@applications_bp.patch("/partner/applications/<int:application_id>")
@role_required(PARTNER)
def decide(application_id):
    application = partner_decide(current_partner(), application_id, json_body())
    return jsonify({"message": f"Application {application.status}",
                    "application": serialize_candidate(application)})
