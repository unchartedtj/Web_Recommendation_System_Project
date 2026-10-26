"""Placement records (test case TC09).

    GET   /api/admin/placements?status=&partner_id=&sector_id=&search=&page=&per_page=
    GET   /api/admin/placements/<id>            full detail incl. the application snapshot
    PATCH /api/admin/placements/<id>            {status?, start_date?, end_date?, reason?}
    GET   /api/admin/placements/export.csv      same filters, as a CSV file

Status flow:
    confirmed ──► ongoing ──► completed
        └────────────┴──────► terminated (a reason is required)
completed and terminated are final.
"""
from datetime import datetime, timezone

from flask import jsonify, request
from sqlalchemy import func, or_

from app.activity import log_activity
from app.admin import admin_bp
from app.admin.common import (ADMIN, choice_arg, csv_response, int_arg, iso, paginate,
                              parse_date, str_arg)
from app.auth.decorators import current_user, role_required
from app.errors import ApiError
from app.extensions import db
from app.models import (Application, IndustryPartner, InternshipOpportunity, PlacementRecord,
                        PlacementStatus, Student)

C, O, D, T = (PlacementStatus.CONFIRMED, PlacementStatus.ONGOING, PlacementStatus.COMPLETED,
              PlacementStatus.TERMINATED)
TRANSITIONS = {C: {O, T}, O: {D, T}, D: set(), T: set()}
REASON_MAX = 255


def _filtered_query():
    query = (PlacementRecord.query.join(Student)
             .join(InternshipOpportunity, PlacementRecord.opportunity_id == InternshipOpportunity.opportunity_id)
             .join(IndustryPartner, InternshipOpportunity.partner_id == IndustryPartner.partner_id))
    status = choice_arg("status", PlacementStatus.ALL)
    if status:
        query = query.filter(PlacementRecord.status == status)
    partner_id = int_arg("partner_id")
    if partner_id is not None:
        query = query.filter(IndustryPartner.partner_id == partner_id)
    sector_id = int_arg("sector_id")
    if sector_id is not None:
        query = query.filter(InternshipOpportunity.sector_id == sector_id)
    search = str_arg("search").lower()
    if search:
        like = f"%{search}%"
        full_name = func.lower(func.concat(Student.first_name, " ", Student.last_name))
        query = query.filter(or_(full_name.like(like), Student.admission_no.like(like),
                                 func.lower(IndustryPartner.organization_name).like(like),
                                 func.lower(InternshipOpportunity.title).like(like)))
    return query.order_by(PlacementRecord.created_at.desc(), PlacementRecord.placement_id.desc())


def placement_row(p: PlacementRecord) -> dict:
    s, o = p.student, p.opportunity
    score = p.application.match_score_at_apply if p.application else None
    return {
        "placement_id": p.placement_id,
        "status": p.status,
        "status_reason": p.status_reason,
        "start_date": iso(p.start_date),
        "end_date": iso(p.end_date),
        "created_at": iso(p.created_at),
        "updated_at": iso(p.updated_at),
        "student": {"student_id": s.student_id, "name": f"{s.first_name} {s.last_name}",
                    "admission_no": s.admission_no, "course": s.course},
        "company": {"partner_id": o.partner_id, "name": o.partner.organization_name},
        "opportunity": {"opportunity_id": o.opportunity_id, "title": o.title,
                        "sector": o.sector.name if o.sector else None},
        "match_percent_at_apply": None if score is None else round(score * 100, 2),
        "allowed_next": sorted(TRANSITIONS[p.status]),
    }


def _get(placement_id: int) -> PlacementRecord:
    p = db.session.get(PlacementRecord, placement_id)
    if p is None:
        raise ApiError("Placement not found", 404)
    return p


@admin_bp.get("/placements")
@role_required(ADMIN)
def list_placements():
    return jsonify(paginate(_filtered_query(), placement_row))


@admin_bp.get("/placements/export.csv")
@role_required(ADMIN)
def export_placements():
    header = ["placement_id", "student", "admission_no", "company", "internship", "sector",
              "status", "start_date", "end_date", "match_percent_at_apply", "status_reason",
              "created_at"]
    rows = []
    for p in _filtered_query().all():
        r = placement_row(p)
        rows.append([r["placement_id"], r["student"]["name"], r["student"]["admission_no"],
                     r["company"]["name"], r["opportunity"]["title"], r["opportunity"]["sector"],
                     r["status"], r["start_date"] or "", r["end_date"] or "",
                     r["match_percent_at_apply"] if r["match_percent_at_apply"] is not None else "",
                     r["status_reason"] or "", r["created_at"]])
    return csv_response("placements.csv", header, rows)


@admin_bp.get("/placements/<int:placement_id>")
@role_required(ADMIN)
def placement_detail(placement_id):
    p = _get(placement_id)
    a: Application = p.application
    return jsonify({"placement": {
        **placement_row(p),
        "student_email": p.student.user.email,
        "application": None if a is None else {
            "application_id": a.application_id,
            "application_date": iso(a.application_date),
            "motivation_note": a.motivation_note,
            "meets_requirements_at_apply": a.meets_requirements_at_apply,
            "snapshot": a.profile_snapshot,
        },
    }})


@admin_bp.patch("/placements/<int:placement_id>")
@role_required(ADMIN)
def update_placement(placement_id):
    p = _get(placement_id)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)

    errors = {}
    new_status = data.get("status", p.status) or p.status
    if new_status not in PlacementStatus.ALL:
        errors["status"] = f"Must be one of {', '.join(PlacementStatus.ALL)}"
    start = parse_date(data["start_date"], "start_date", errors) if "start_date" in data else p.start_date
    end = parse_date(data["end_date"], "end_date", errors) if "end_date" in data else p.end_date
    reason = data.get("reason")
    if reason is not None and not isinstance(reason, str):
        errors["reason"] = "Must be text"
        reason = None
    reason = (reason or "").strip() or None
    if reason and len(reason) > REASON_MAX:
        errors["reason"] = f"At most {REASON_MAX} characters"
    if errors:
        raise ApiError("Validation failed", 400, errors)

    # 1. Is the status change allowed? (Final statuses can't be edited at all.)
    if p.status in (D, T):
        raise ApiError(f"This placement is already {p.status} and can't be changed", 409)
    if new_status != p.status and new_status not in TRANSITIONS[p.status]:
        raise ApiError(f"A placement can't go from {p.status} to {new_status}", 409)

    # 2. The rules for the new status and the dates.
    if new_status == T and not reason:
        errors["reason"] = "A reason is required to terminate a placement"
    if new_status in (O, D) and start is None:
        errors["start_date"] = "A start date is required once the placement is ongoing"
    if start and end and end <= start:
        errors["end_date"] = "The end date must be after the start date"
    if errors:
        raise ApiError("Validation failed", 400, errors)

    old = {"status": p.status, "start_date": iso(p.start_date), "end_date": iso(p.end_date)}
    p.status, p.start_date, p.end_date = new_status, start, end
    if reason or new_status == T:
        p.status_reason = reason
    p.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    log_activity("placement.updated", actor=current_user(), target_type="placement",
                 target_id=p.placement_id,
                 details={"from": old, "to": {"status": new_status, "start_date": iso(start),
                                              "end_date": iso(end)}, "reason": reason})
    db.session.commit()
    return jsonify({"message": "Placement updated", "placement": placement_row(p)})
