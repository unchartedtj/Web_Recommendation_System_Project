"""Grade submission (temporary helper), recommendations, and model retraining.

Endpoints in this file (all under /api):
    POST /grades                       student: submit marks {unit_id: mark}
    POST /recommendations/generate     student: run the engine and save the results
    GET  /recommendations              student: read the saved results
    POST /admin/model/retrain          system admin: refit the model, see IDF weights
"""
from flask import jsonify, request

from app.auth.decorators import current_student, role_required
from app.errors import ApiError
from app.extensions import db
from app.models import AcademicUnit, Grade, GradeProfile, Recommendation
from app.recommendations import recommendations_bp
from services.recommendation_engine import IncompleteGradesError, get_engine

STUDENT, ADMIN = "student", "system_admin"


@recommendations_bp.post("/grades")
@role_required(STUDENT)
def submit_grades():
    """TEMPORARY helper until the grade input UI exists.

    Body: {"<unit_id>": mark, ...}. Creates a NEW grade profile each time. The engine
    always uses the latest one, so earlier submissions are kept as history.
    Example body: {"1": 78, "2": 64.5, "3": 90, ...}
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        raise ApiError("Body must be a JSON object of {unit_id: mark}", 400)

    active = {u.unit_id for u in AcademicUnit.query.filter_by(is_active=True)}
    errors, marks = {}, {}
    # Check each (unit id, mark) pair. `continue` skips to the next pair once one
    # problem is found, so each unit gets at most one error message.
    for key, value in data.items():
        try:
            unit_id = int(key)            # JSON keys are always text, e.g. "5" → 5
        except (TypeError, ValueError):
            errors[str(key)] = "Unit id must be a number"
            continue
        if unit_id not in active:
            errors[str(key)] = "Unknown or inactive unit"
            continue
        try:
            if isinstance(value, bool):   # true/false are not marks
                raise ValueError
            mark = float(value)
        except (TypeError, ValueError):
            errors[str(key)] = "Mark must be a number"
            continue
        if not 0 <= mark <= 100:
            errors[str(key)] = "Mark must be between 0 and 100"
            continue
        marks[unit_id] = round(mark, 2)   # the DB column holds 2 decimal places
    if errors:
        raise ApiError("Validation failed", 400, errors)

    student = current_student()
    try:
        # One transaction: the profile row plus one Grade row per unit.
        profile = GradeProfile(student_id=student.student_id)
        db.session.add(profile)
        db.session.flush()                # get profile.profile_id for the grade rows
        for unit_id, mark in marks.items():
            db.session.add(Grade(profile_id=profile.profile_id, unit_id=unit_id, grade_value=mark))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({"message": "Grades saved", "profile_id": profile.profile_id,
                    "units_graded": len(marks)}), 201


@recommendations_bp.post("/recommendations/generate")
@role_required(STUDENT)
def generate():
    """Run the recommendation engine for the logged-in student."""
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
    """The results saved by the last generate call (best match first)."""
    rows = (Recommendation.query.filter_by(student_id=current_student().student_id)
            .order_by(Recommendation.rank).all())
    return jsonify({
        # All rows from one run share the same timestamp; None if never generated.
        "generated_at": rows[0].generated_at.isoformat() + "Z" if rows else None,
        "recommendations": [{
            "rank": r.rank,
            "opportunity_id": r.opportunity_id,
            # These come from the linked opportunity (via the relationship), so they're current.
            "title": r.opportunity.title,
            "organization": r.opportunity.partner.organization_name,
            "sector": r.opportunity.sector,
            "status": r.opportunity.status,  # may have closed since generation
            # These are the snapshot stored at generation time.
            "match_score": r.match_score,
            "match_percent": round(r.match_score * 100, 2),
            "avg_requirement_mark": (None if r.avg_requirement_mark is None
                                     else float(r.avg_requirement_mark)),
            "meets_requirements": r.meets_requirements,
            "unmet_requirements": r.unmet_requirements or [],
        } for r in rows],
    })


@recommendations_bp.post("/admin/model/retrain")
@role_required(ADMIN)
def retrain():
    """Admin: refit the model now and show the learnt IDF weight of each unit."""
    model = get_engine().update_model()
    # Look up unit names for the ids in the vocabulary.
    units = {u.unit_id: u for u in AcademicUnit.query.filter(
        AcademicUnit.unit_id.in_(model["vocabulary"]))}
    return jsonify({
        "model_type": model["model_type"],
        "fitted_at": model["fitted_at"],
        "n_opportunities": len(model["opportunity_ids"]),
        # zip pairs each unit id with its IDF weight (same order in both lists).
        "idf": [{
            "unit_id": uid,
            "unit_name": units[uid].unit_name if uid in units else None,
            "idf": round(float(w), 6),
        } for uid, w in zip(model["vocabulary"], model["idf"])],
    })
