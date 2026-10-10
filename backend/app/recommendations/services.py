"""Helpers that explain a match to a student ("Why this match?").

match_details() compares ONE opportunity's requirements with a student's marks and skills:
    units:  [{unit_id, unit, importance, min_mark, my_mark, met}]      → the ✓ / ✗ unit table
    skills: [{skill_id, skill, importance, i_have}]                    → have / missing chips
It's used by the recommendations page, the internship details page, and the dashboard.
"""
from app.models import AcademicUnit, GradeProfile, RequirementImportance


def latest_marks(student_id: int) -> dict[int, float]:
    """The student's most recent mark per unit, {unit_id: mark} (empty if none saved)."""
    profile = (GradeProfile.query.filter_by(student_id=student_id)
               .order_by(GradeProfile.submission_date.desc(), GradeProfile.profile_id.desc())
               .first())
    return {g.unit_id: float(g.grade_value) for g in profile.grades} if profile else {}


def student_skill_ids(student) -> set[int]:
    """Ids of the active skills the student selected."""
    return {s.skill_id for s in student.skills if s.skill.is_active}


def profile_is_complete(student, marks: dict[int, float] | None = None) -> bool:
    """Complete = a mark for every active unit + at least one skill + at least one interest.
    (The same rule the profile page uses.)"""
    marks = latest_marks(student.student_id) if marks is None else marks
    active_units = {u.unit_id for u in AcademicUnit.query.filter_by(is_active=True)}
    has_all_marks = bool(active_units) and active_units <= set(marks)
    has_skill = any(s.skill.is_active for s in student.skills)
    has_interest = any(i.sector.is_active for i in student.interests)
    return has_all_marks and has_skill and has_interest


def match_details(opportunity, marks: dict[int, float], skill_ids: set[int]) -> dict:
    """Side-by-side comparison of an opportunity's requirements with the student's profile."""
    def importance_first(item_importance, name):
        # Essential first, then alphabetical (False sorts before True).
        return (item_importance != RequirementImportance.ESSENTIAL, name)

    units = []
    for p in sorted(opportunity.precursors, key=lambda p: importance_first(p.importance,
                                                                           p.unit.unit_name)):
        if not p.unit.is_active:
            continue
        my_mark = marks.get(p.unit_id)
        min_mark = None if p.min_mark is None else float(p.min_mark)
        units.append({
            "unit_id": p.unit_id,
            "unit": p.unit.unit_name,
            "importance": p.importance,
            "min_mark": min_mark,
            "my_mark": my_mark,
            # ✓ if there's no minimum, or the student's mark reaches it.
            "met": my_mark is not None and (min_mark is None or my_mark >= min_mark),
        })

    skills = [{
        "skill_id": s.skill_id,
        "skill": s.skill.name,
        "importance": s.importance,
        "i_have": s.skill_id in skill_ids,
    } for s in sorted(opportunity.skills, key=lambda s: importance_first(s.importance, s.skill.name))
        if s.skill.is_active]

    return {"units": units, "skills": skills}
