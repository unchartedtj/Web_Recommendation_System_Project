"""Student profile endpoints (role: student).

    GET /api/student/profile   the latest grades + selected skills + career interests
    PUT /api/student/profile   save the whole profile, then generate recommendations

The profile is "one-time but editable": the first save creates it, later saves replace
it (a NEW grade profile is created each time, so older grade submissions are kept as history).
"""
from datetime import datetime, timezone

from flask import jsonify, request

from app.auth.decorators import current_student, role_required
from app.errors import ApiError
from app.extensions import db
from app.models import AcademicUnit, Grade, GradeProfile, StudentInterest, StudentSkill
from app.opportunities.services import active_sector_ids, active_skill_ids
from app.students import students_bp
from app.students.validators import validate_profile
from services.recommendation_engine import IncompleteGradesError, get_engine

STUDENT = "student"


def _active_units() -> dict[int, str]:
    """{unit_id: unit_name} for every active unit (each one needs a mark)."""
    return {u.unit_id: u.unit_name for u in AcademicUnit.query.filter_by(is_active=True)}


def serialize_profile(student) -> dict:
    """The student's current profile, as the frontend form needs it."""
    latest = (GradeProfile.query.filter_by(student_id=student.student_id)
              .order_by(GradeProfile.submission_date.desc(), GradeProfile.profile_id.desc())
              .first())
    units = _active_units()
    # Only marks for units that are still active.
    grades = ({str(g.unit_id): float(g.grade_value) for g in latest.grades if g.unit_id in units}
              if latest else {})
    skill_ids = sorted(s.skill_id for s in student.skills if s.skill.is_active)
    sector_ids = sorted(i.sector_id for i in student.interests if i.sector.is_active)
    return {
        "grades": grades,
        "skill_ids": skill_ids,
        "sector_ids": sector_ids,
        "profile_updated_at": (student.profile_updated_at.isoformat(timespec="seconds") + "Z"
                               if student.profile_updated_at else None),
        # Complete = every active unit graded + at least one skill + at least one interest.
        "is_complete": len(grades) == len(units) > 0 and bool(skill_ids) and bool(sector_ids),
    }


@students_bp.get("/profile")
@role_required(STUDENT)
def get_profile():
    return jsonify({"profile": serialize_profile(current_student())})


@students_bp.put("/profile")
@role_required(STUDENT)
def save_profile():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)

    cleaned, errors, implausible = validate_profile(
        data, _active_units(), active_skill_ids(), active_sector_ids())
    if errors:
        raise ApiError("Please fix the highlighted fields", 400, errors)
    # Every mark identical → ask the student to confirm before saving (409 Conflict).
    if implausible and data.get("confirm_implausible") is not True:
        raise ApiError(
            "All your marks are identical. Please check them, or confirm they are correct.",
            409, {"grades": "All 12 marks are identical. Is that correct?"})

    student = current_student()
    try:
        # ---- ONE transaction for the whole save ----
        # 1. A new grade profile with one Grade row per unit.
        profile = GradeProfile(student_id=student.student_id)
        db.session.add(profile)
        db.session.flush()                       # get profile.profile_id
        for unit_id, mark in cleaned["grades"].items():
            db.session.add(Grade(profile_id=profile.profile_id, unit_id=unit_id,
                                 grade_value=mark))
        # 2. Replace the skills and interests (clear, flush, then add the new ones).
        student.skills.clear()
        student.interests.clear()
        db.session.flush()
        for sid in cleaned["skill_ids"]:
            student.skills.append(StudentSkill(skill_id=sid))
        for sid in cleaned["sector_ids"]:
            student.interests.append(StudentInterest(sector_id=sid))
        # 3. Remember when the profile changed (used to know when results are out of date).
        student.profile_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.flush()
        # 4. Generate recommendations INSIDE the same transaction (commit=False).
        recommendations = get_engine().generate_recommendations(student.student_id, commit=False)
        db.session.commit()                      # everything is saved together
    except IncompleteGradesError as err:         # shouldn't happen after validation, but be safe
        db.session.rollback()
        raise ApiError("Grade profile is incomplete", 400,
                       {"missing_units": err.missing, "invalid_units": err.invalid})
    except Exception:
        db.session.rollback()                    # any failure → nothing is saved
        raise

    return jsonify({"message": "Profile saved", "profile": serialize_profile(student),
                    "recommendations": recommendations})
