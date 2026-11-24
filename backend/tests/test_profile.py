"""Tests for the student profile: GET/PUT /api/student/profile (TC03, TC04).

A profile = a mark for each of the 12 units + 1 to 10 skills + 1 to 3 career interests.
Saving it also generates recommendations, all in one transaction.
(See the top of test_opportunities.py for how pytest tests and fixtures work.)
"""
import pytest

from app.models import (GradeProfile, Recommendation, Skill, Student, StudentInterest,
                        StudentSkill)
from app.extensions import db
from tests.conftest import auth_header, register_and_login

PROFILE = "/api/student/profile"


@pytest.fixture
def student_token(client, seeded, student_payload):
    return register_and_login(client, student_payload)


def put(client, token, body):
    return client.put(PROFILE, json=body, headers=auth_header(token))


def nothing_saved():
    """True if no part of a profile (or recommendations) was written."""
    return (GradeProfile.query.count() == 0 and StudentSkill.query.count() == 0
            and StudentInterest.query.count() == 0 and Recommendation.query.count() == 0)


# ---- Reading ---------------------------------------------------------------------------------

def test_new_student_profile_is_empty_and_incomplete(client, student_token):
    res = client.get(PROFILE, headers=auth_header(student_token))
    assert res.status_code == 200
    profile = res.get_json()["profile"]
    assert profile == {"grades": {}, "skill_ids": [], "sector_ids": [],
                       "profile_updated_at": None, "is_complete": False}


# ---- Saving (TC03) ---------------------------------------------------------------------------

def test_tc03_complete_profile_is_saved_and_passed_to_the_engine(client, student_token,
                                                                profile_body):
    body = profile_body()

    res = put(client, student_token, body)

    assert res.status_code == 200
    data = res.get_json()
    # Recommendations are returned AND saved.
    assert len(data["recommendations"]) == 5
    assert Recommendation.query.count() == 5
    # The profile itself was saved.
    assert GradeProfile.query.count() == 1
    assert sorted(s.skill_id for s in StudentSkill.query) == sorted(body["skill_ids"])
    assert [i.sector_id for i in StudentInterest.query] == body["sector_ids"]
    assert Student.query.one().profile_updated_at is not None
    assert data["profile"]["is_complete"] is True

    # GET returns the same profile, ready to pre-fill the form.
    saved = client.get(PROFILE, headers=auth_header(student_token)).get_json()["profile"]
    assert saved["grades"] == {k: float(v) for k, v in body["grades"].items()}
    assert saved["skill_ids"] == sorted(body["skill_ids"])
    assert saved["is_complete"] is True


def test_saving_again_replaces_skills_and_interests(client, student_token, profile_body):
    put(client, student_token, profile_body(skills=("Python", "SQL"),
                                            interests=("Data Analytics & AI",)))
    put(client, student_token, profile_body(skills=("Java",),
                                            interests=("Software Development",
                                                       "Web & Mobile Development")))
    assert StudentSkill.query.count() == 1
    assert StudentInterest.query.count() == 2
    assert GradeProfile.query.count() == 2       # a new grade profile each time (history)
    assert Recommendation.query.count() == 5     # results replaced, not duplicated


# ---- Validation (TC04): 400 listing every problem ------------------------------------------

@pytest.mark.parametrize("case,field", [
    ("missing_unit", "grades"),
    ("eleven_skills", "skill_ids"),
    ("zero_skills", "skill_ids"),
    ("zero_interests", "sector_ids"),
    ("four_interests", "sector_ids"),
    ("three_decimals", "grades.UNIT"),
    ("over_100", "grades.UNIT"),
    ("not_a_number", "grades.UNIT"),
    ("duplicate_skill", "skill_ids"),
    ("unknown_skill", "skill_ids"),
])
def test_invalid_profile_returns_400(client, student_token, profile_body, seeded, skill_ids,
                                     sector_ids, case, field):
    body = profile_body()
    oop = str(seeded["Object Oriented Programming"])
    all_skills = list(skill_ids.values())
    all_sectors = list(sector_ids.values())
    if case == "missing_unit":
        del body["grades"][oop]
    elif case == "eleven_skills":
        body["skill_ids"] = all_skills[:11]
    elif case == "zero_skills":
        body["skill_ids"] = []
    elif case == "zero_interests":
        body["sector_ids"] = []
    elif case == "four_interests":
        body["sector_ids"] = all_sectors[:4]
    elif case == "three_decimals":
        body["grades"][oop] = 100.555
    elif case == "over_100":
        body["grades"][oop] = 101
    elif case == "not_a_number":
        body["grades"][oop] = "seventy"
    elif case == "duplicate_skill":
        body["skill_ids"] = [all_skills[0], all_skills[0]]
    elif case == "unknown_skill":
        body["skill_ids"] = [999999]

    res = put(client, student_token, body)

    assert res.status_code == 400
    assert field.replace("UNIT", oop) in res.get_json()["fields"]
    assert nothing_saved()


def test_every_problem_is_listed_at_once(client, student_token, profile_body, seeded,
                                         skill_ids, sector_ids):
    body = profile_body()
    oop, dsa = str(seeded["Object Oriented Programming"]), str(seeded["Data Structures and Algorithms"])
    del body["grades"][oop]                          # missing unit
    body["grades"][dsa] = 100.555                    # too many decimals
    body["skill_ids"] = list(skill_ids.values())[:11]   # 11 skills
    body["sector_ids"] = list(sector_ids.values())[:4]  # 4 interests

    fields = put(client, student_token, body).get_json()["fields"]

    assert {"grades", f"grades.{oop}", f"grades.{dsa}", "skill_ids", "sector_ids"} <= set(fields)


def test_inactive_skill_is_rejected(client, student_token, profile_body):
    db.session.query(Skill).filter_by(name="Python").update({"is_active": False})
    db.session.commit()
    res = put(client, student_token, profile_body(skills=("Python",)))
    assert res.status_code == 400
    assert "skill_ids" in res.get_json()["fields"]


# ---- "Implausible entry" check --------------------------------------------------------------

def test_identical_marks_need_confirmation(client, student_token, profile_body, seeded):
    body = profile_body()
    body["grades"] = {str(uid): 70 for uid in seeded.values()}   # all 12 marks the same

    first = put(client, student_token, body)
    assert first.status_code == 409
    assert "grades" in first.get_json()["fields"]
    assert nothing_saved()

    body["confirm_implausible"] = True
    second = put(client, student_token, body)
    assert second.status_code == 200
    assert Recommendation.query.count() == 5


def test_partner_cannot_use_the_student_profile(client, seeded, partner_payload, profile_body):
    token = register_and_login(client, partner_payload)
    assert client.get(PROFILE, headers=auth_header(token)).status_code == 403
    assert put(client, token, profile_body()).status_code == 403
