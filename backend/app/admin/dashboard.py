"""The admin Overview page and the Activity Log.

    GET /api/admin/overview
    GET /api/admin/activity?action=&actor_user_id=&target_type=&from=&to=&page=&per_page=
"""
from datetime import datetime, time

from flask import jsonify
from sqlalchemy import func

from app.admin import admin_bp
from app.admin.common import ADMIN, int_arg, iso, paginate, parse_date, str_arg
from app.auth.decorators import role_required
from app.errors import ApiError
from app.extensions import db
from app.models import (ActivityLog, Application, ApplicationStatus, IndustryPartner,
                        InternshipOpportunity, OpportunityStatus, PlacementRecord, PlacementStatus,
                        Sector, Student)
from app.recommendations.services import profile_is_complete


def activity_row(a: ActivityLog) -> dict:
    actor = a.actor
    return {
        "log_id": a.log_id, "created_at": iso(a.created_at), "action": a.action,
        "actor": None if actor is None else {"user_id": actor.user_id, "email": actor.email,
                                             "name": actor.display_name, "role": actor.role.value},
        "target_type": a.target_type, "target_id": a.target_id, "details": a.details,
    }


def _grouped(column, allowed) -> dict[str, int]:
    counts = {s: 0 for s in allowed}
    counts.update(dict(db.session.query(column, func.count()).group_by(column).all()))
    return counts


def _avg(query) -> float | None:
    value = query.scalar()
    return None if value is None else round(float(value) * 100, 2)


@admin_bp.get("/overview")
@role_required(ADMIN)
def overview():
    students = Student.query.all()
    per_sector = (db.session.query(Sector.name, func.count(InternshipOpportunity.opportunity_id))
                  .join(InternshipOpportunity, InternshipOpportunity.sector_id == Sector.sector_id)
                  .group_by(Sector.name).order_by(Sector.name).all())
    latest = ActivityLog.query.order_by(ActivityLog.created_at.desc(),
                                        ActivityLog.log_id.desc()).limit(10).all()
    return jsonify({
        "students": {"total": len(students),
                     "complete_profiles": sum(1 for s in students if profile_is_complete(s))},
        "partners": IndustryPartner.query.count(),
        "open_opportunities": InternshipOpportunity.query.filter_by(
            status=OpportunityStatus.OPEN).count(),
        "applications": _grouped(Application.status, ApplicationStatus.ALL),
        "placements": _grouped(PlacementRecord.status, PlacementStatus.ALL),
        # Average match % at the time of applying: accepted applications vs all of them.
        "match": {
            "accepted_avg_percent": _avg(db.session.query(func.avg(Application.match_score_at_apply))
                                         .filter(Application.status == ApplicationStatus.ACCEPTED)),
            "all_avg_percent": _avg(db.session.query(func.avg(Application.match_score_at_apply))),
        },
        "opportunities_per_sector": [{"sector": name, "count": n} for name, n in per_sector],
        "recent_activity": [activity_row(a) for a in latest],
    })


@admin_bp.get("/activity")
@role_required(ADMIN)
def activity():
    query = ActivityLog.query
    action = str_arg("action")
    if action:
        # "application" matches every application.* action; a full name matches exactly.
        query = query.filter(ActivityLog.action.like(f"{action}%"))
    actor = int_arg("actor_user_id")
    if actor is not None:
        query = query.filter(ActivityLog.actor_user_id == actor)
    target_type = str_arg("target_type")
    if target_type:
        query = query.filter(ActivityLog.target_type == target_type)
    errors = {}
    start = parse_date(str_arg("from"), "from", errors)
    end = parse_date(str_arg("to"), "to", errors)
    if errors:
        raise ApiError("Validation failed", 400, errors)
    if start:
        query = query.filter(ActivityLog.created_at >= datetime.combine(start, time.min))
    if end:
        query = query.filter(ActivityLog.created_at <= datetime.combine(end, time.max))
    query = query.order_by(ActivityLog.created_at.desc(), ActivityLog.log_id.desc())
    page = paginate(query, activity_row)
    page["actions"] = [a for (a,) in db.session.query(ActivityLog.action).distinct()
                       .order_by(ActivityLog.action)]
    return jsonify(page)
