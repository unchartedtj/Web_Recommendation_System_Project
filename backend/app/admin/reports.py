"""The admin Reports page.

    GET /api/admin/reports
        placement_rate   students placed, per course (+ an overall total)
        match_outcomes   the match % students had when they applied, per application status
        pay              internships by pay type (unpaid / paid / stipend) with KSh amounts
    GET /api/admin/reports/placement-rate.csv · match-outcomes.csv · pay.csv   (CSV downloads)

A student counts as "placed" when they have a confirmed, ongoing or completed placement
(a terminated placement doesn't count).
"""
from flask import jsonify
from sqlalchemy import case, func

from app.admin import admin_bp
from app.admin.common import ADMIN, csv_response
from app.auth.decorators import role_required
from app.extensions import db
from app.models import (Application, ApplicationStatus, CompensationType, InternshipOpportunity,
                        OpportunityStatus, PlacementRecord, PlacementStatus, Student)
from app.recommendations.services import profile_is_complete

PLACED = (PlacementStatus.CONFIRMED, PlacementStatus.ONGOING, PlacementStatus.COMPLETED)


def _percent(part: int, whole: int) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def _placement_rate() -> dict:
    placed_ids = {sid for (sid,) in db.session.query(PlacementRecord.student_id)
                  .filter(PlacementRecord.status.in_(PLACED)).distinct()}
    groups: dict[str, dict] = {}
    for s in Student.query.all():
        g = groups.setdefault(s.course or "Unknown",
                              {"students": 0, "complete_profiles": 0, "placed": 0})
        g["students"] += 1
        g["complete_profiles"] += profile_is_complete(s)
        g["placed"] += s.student_id in placed_ids
    rows = [{"course": course, **g, "rate_percent": _percent(g["placed"], g["students"])}
            for course, g in sorted(groups.items())]
    total = {k: sum(r[k] for r in rows) for k in ("students", "complete_profiles", "placed")}
    total["rate_percent"] = _percent(total["placed"], total["students"])
    return {"rows": rows, "total": total}


def _pct(value) -> float | None:
    return None if value is None else round(float(value) * 100, 1)


def _match_outcomes() -> list[dict]:
    score = Application.match_score_at_apply
    stats = {status: rest for status, *rest in db.session.query(
        Application.status, func.count(), func.avg(score), func.min(score), func.max(score),
    ).group_by(Application.status)}
    rows = []
    for status in ApplicationStatus.ALL:          # every status, even with 0 applications
        n, avg, low, high = stats.get(status, (0, None, None, None))
        rows.append({"status": status, "applications": n, "avg_match_percent": _pct(avg),
                     "min_match_percent": _pct(low), "max_match_percent": _pct(high)})
    return rows


def _pay() -> list[dict]:
    O = InternshipOpportunity
    stats = {t: (n, open_n, avg, low, high) for t, n, open_n, avg, low, high in db.session.query(
        O.compensation_type, func.count(),
        func.sum(case((O.status == OpportunityStatus.OPEN, 1), else_=0)),
        func.avg(O.compensation_amount), func.min(O.compensation_amount),
        func.max(O.compensation_amount),
    ).group_by(O.compensation_type)}
    rows = []
    for t in CompensationType.ALL:
        n, open_n, avg, low, high = stats.get(t, (0, 0, None, None, None))
        rows.append({"type": t, "internships": n, "open": int(open_n or 0),
                     "avg_amount": None if avg is None else round(float(avg)),
                     "min_amount": low, "max_amount": high})
    return rows


@admin_bp.get("/reports")
@role_required(ADMIN)
def reports():
    return jsonify({"placement_rate": _placement_rate(), "match_outcomes": _match_outcomes(),
                    "pay": _pay()})


# ---- CSV exports (one file per report) -----------------------------------------------------

@admin_bp.get("/reports/placement-rate.csv")
@role_required(ADMIN)
def export_placement_rate():
    rate = _placement_rate()
    header = ["course", "students", "complete_profiles", "placed", "placement_rate_percent"]
    rows = [[r["course"], r["students"], r["complete_profiles"], r["placed"], r["rate_percent"]]
            for r in rate["rows"]]
    t = rate["total"]
    rows.append(["All students", t["students"], t["complete_profiles"], t["placed"], t["rate_percent"]])
    return csv_response("placement_rate_by_course.csv", header, rows)


@admin_bp.get("/reports/match-outcomes.csv")
@role_required(ADMIN)
def export_match_outcomes():
    header = ["outcome", "applications", "avg_match_percent", "min_match_percent",
              "max_match_percent"]
    rows = [[r["status"], r["applications"], r["avg_match_percent"], r["min_match_percent"],
             r["max_match_percent"]] for r in _match_outcomes()]
    return csv_response("match_vs_outcome.csv", header, rows)


@admin_bp.get("/reports/pay.csv")
@role_required(ADMIN)
def export_pay():
    header = ["pay_type", "internships", "open", "avg_ksh_per_month", "min_ksh_per_month",
              "max_ksh_per_month"]
    rows = [[r["type"], r["internships"], r["open"], r["avg_amount"], r["min_amount"],
             r["max_amount"]] for r in _pay()]
    return csv_response("internship_pay.csv", header, rows)
