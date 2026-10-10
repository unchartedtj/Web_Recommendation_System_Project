"""Recommendations and model retraining.

Endpoints in this file (all under /api):
    POST /recommendations/generate     student: run the engine and save the results
    GET  /recommendations              student: the saved results (refreshed if out of date)
    POST /admin/model/retrain          system admin: refit the models, see the IDF weights

(Students enter grades, skills and interests through PUT /api/student/profile,
which also generates recommendations. The old temporary POST /api/grades was removed.)
"""
from flask import jsonify

from app.auth.decorators import current_student, role_required
from app.errors import ApiError
from app.models import AcademicUnit, Recommendation, Skill
from app.recommendations import recommendations_bp
from app.recommendations.services import (latest_marks, match_details, profile_is_complete,
                                          student_skill_ids)
from services.recommendation_engine import IncompleteGradesError, get_engine

STUDENT, ADMIN = "student", "system_admin"


def serialize_recommendation(r: Recommendation) -> dict:
    """One saved result. Opportunity details are current; the scores are the snapshot
    taken when the results were generated."""
    missing = r.missing_skills or {}
    o = r.opportunity
    return {
        "rank": r.rank,
        "opportunity_id": r.opportunity_id,
        "title": o.title,
        "organization": o.partner.organization_name,
        "sector_id": o.sector_id,
        "sector": o.sector.name if o.sector else None,
        "location": o.location,
        "duration_months": o.duration_months,
        "slots": o.slots,
        "application_deadline": o.application_deadline.isoformat() if o.application_deadline else None,
        "status": o.status,  # may have closed since generation
        "match_score": r.match_score,
        "match_percent": round(r.match_score * 100, 2),
        "breakdown": {
            "grade_score": r.grade_score,
            "skill_score": r.skill_score,
            "interest_score": r.interest_score,
        },
        "avg_requirement_mark": (None if r.avg_requirement_mark is None
                                 else float(r.avg_requirement_mark)),
        "meets_requirements": r.meets_requirements,
        "unmet_requirements": r.unmet_requirements or [],
        "missing_essential_skills": missing.get("essential", []),
        "missing_desirable_skills": missing.get("desirable", []),
        "interest_match": r.interest_match,
    }


def _saved_rows(student_id: int) -> list[Recommendation]:
    return (Recommendation.query.filter_by(student_id=student_id)
            .order_by(Recommendation.rank).all())


@recommendations_bp.post("/recommendations/generate")
@role_required(STUDENT)
def generate():
    """Run the recommendation engine for the logged-in student (from their saved profile)."""
    student = current_student()
    try:
        results = get_engine().generate_recommendations(student.student_id)
    except IncompleteGradesError as err:
        # TC04: nothing was written; tell the student exactly which units to fix.
        raise ApiError("Grade profile is incomplete", 400,
                       {"missing_units": err.missing, "invalid_units": err.invalid})
    return jsonify({"recommendations": results})


@recommendations_bp.get("/recommendations")
@role_required(STUDENT)
def saved_recommendations():
    """The student's results, split into two lists, each sorted by match score (best first):
        eligible      – the student meets every ESSENTIAL minimum mark
        not_eligible  – below at least one essential minimum ("Below minimum requirements")
    Each item also has units[] and skills[] for the "Why this match?" section.

    Regenerated automatically if they're older than the student's profile or older than
    the model (e.g. a partner posted or changed an opportunity since).
    """
    student = current_student()
    engine = get_engine()
    rows = _saved_rows(student.student_id)
    saved_at = rows[0].generated_at if rows else None

    engine.ensure_fresh()                                     # refit first if the model is stale
    outdated = student.profile_updated_at is not None and (
        saved_at is None
        or saved_at < student.profile_updated_at              # profile changed since
        # Model changed. "<=" because both times are stored to the whole second: a refit in
        # the same second as the saved results must still count as newer.
        or (engine.fitted_at() is not None and saved_at <= engine.fitted_at()))
    profile_complete = True
    if outdated:
        try:
            engine.generate_recommendations(student.student_id)
            rows = _saved_rows(student.student_id)
        except IncompleteGradesError:
            profile_complete = False                          # keep whatever was saved before
    marks = latest_marks(student.student_id)
    if not profile_is_complete(student, marks):
        profile_complete = False                              # never saved / incomplete profile

    # Add the "Why this match?" comparison (the student's marks and skills vs requirements).
    skill_ids = student_skill_ids(student)
    items = []
    for r in rows:
        item = serialize_recommendation(r)
        item.update(match_details(r.opportunity, marks, skill_ids))
        items.append(item)
    # Best score first within each list (rank breaks exact ties the engine's way).
    by_score = lambda i: (-i["match_score"], i["rank"])     # noqa: E731

    return jsonify({
        # All rows from one run share the same timestamp; None if never generated.
        "generated_at": rows[0].generated_at.isoformat() + "Z" if rows else None,
        "profile_updated_at": (student.profile_updated_at.isoformat() + "Z"
                               if student.profile_updated_at else None),
        "profile_complete": profile_complete,
        "eligible": sorted([i for i in items if i["meets_requirements"]], key=by_score),
        "not_eligible": sorted([i for i in items if not i["meets_requirements"]], key=by_score),
    })


@recommendations_bp.post("/admin/model/retrain")
@role_required(ADMIN)
def retrain():
    """Admin: refit both models now and show the learnt IDF weight of each unit and skill."""
    model = get_engine().update_model()
    units = {u.unit_id: u.unit_name for u in AcademicUnit.query.filter(
        AcademicUnit.unit_id.in_(model["vocabulary"]))}
    skills = {s.skill_id: s.name for s in Skill.query.filter(
        Skill.skill_id.in_(model["skill_vocabulary"]))}
    return jsonify({
        "model_type": model["model_type"],
        "fitted_at": model["fitted_at"],
        "n_opportunities": len(model["opportunity_ids"]),
        # zip pairs each id with its IDF weight (same order in both lists).
        "idf": [{"unit_id": uid, "unit_name": units.get(uid), "idf": round(float(w), 6)}
                for uid, w in zip(model["vocabulary"], model["idf"])],
        "skill_idf": [{"skill_id": sid, "name": skills.get(sid), "idf": round(float(w), 6)}
                      for sid, w in zip(model["skill_vocabulary"], model["skill_idf"])],
    })
