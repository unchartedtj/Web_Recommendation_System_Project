"""API tests: recommendation generation (incl. TC04, TC07), saved results, and retraining.

These test the engine END TO END through the real API and database
(test_engine.py tests the maths alone, without a database).
Typical flow in a test: a student logs in → saves a profile with PUT /api/student/profile
(grades + skills + interests, which also generates recommendations) → we check the ranking
and the saved rows. (See the top of test_opportunities.py for how pytest works.)
"""
from datetime import datetime

import pytest

from app.auth.services import create_user_with_profile
from app.extensions import db
from app.models import Grade, GradeProfile, InternshipOpportunity, Recommendation
from app.seed.catalog import DEMO_PASSWORD
from tests.conftest import auth_header, login, register_and_login

GENERATE = "/api/recommendations/generate"
PROFILE = "/api/student/profile"
SAVED = "/api/recommendations"


@pytest.fixture
def student_token(client, seeded, student_payload):
    return register_and_login(client, student_payload)


def save_profile(client, token, body):
    return client.put(PROFILE, json=body, headers=auth_header(token))


def saved(client, token):
    """GET /api/recommendations, with the two lists joined back together
    (eligible first, then not eligible), as the page shows them."""
    body = client.get(SAVED, headers=auth_header(token)).get_json()
    return body["eligible"] + body["not_eligible"]


SWE_PROFILE = dict(default=55,
                   overrides={"Object Oriented Programming": 92,
                              "Data Structures and Algorithms": 88},
                   skills=("Java", "Git & GitHub"), interests=("Software Development",))


# ---- Generate ------------------------------------------------------------------------------

def test_tc07_profile_pointing_to_software_ranks_it_first(client, student_token, profile_body):
    """TC07 end to end: strong in the SWE units + Java/Git + the Software Development
    interest → Software Development Intern is ranked first."""
    res = save_profile(client, student_token, profile_body(**SWE_PROFILE))

    assert res.status_code == 200
    recs = res.get_json()["recommendations"]
    assert [r["rank"] for r in recs] == [1, 2, 3, 4, 5]
    top = recs[0]
    assert top["title"] == "Software Development Intern"
    assert top["organization"] == "TechCorp Kenya"
    assert top["sector"] == "Software Development"
    assert top["interest_match"] is True
    assert top["missing_essential_skills"] == []
    assert sorted(top["missing_desirable_skills"]) == ["Python", "SQL"]
    for key in ("opportunity_id", "match_score", "match_percent", "avg_requirement_mark",
                "meets_requirements", "unmet_requirements"):
        assert key in top
    # The final score is the weighted sum of the breakdown (0.60 / 0.25 / 0.15).
    b = top["breakdown"]
    expected = 0.60 * b["grade_score"] + 0.25 * b["skill_score"] + 0.15 * b["interest_score"]
    assert top["match_score"] == pytest.approx(expected, abs=1e-3)
    assert Recommendation.query.count() == 5


def test_generate_endpoint_reruns_from_the_saved_profile(client, student_token, profile_body):
    save_profile(client, student_token, profile_body(**SWE_PROFILE))

    res = client.post(GENERATE, headers=auth_header(student_token))

    assert res.status_code == 200
    assert res.get_json()["recommendations"][0]["title"] == "Software Development Intern"
    assert Recommendation.query.count() == 5          # replaced, not duplicated


def test_unmet_requirements_are_reported(client, student_token, profile_body):
    save_profile(client, student_token,
                 profile_body(75, {"Probability and Statistics I": 50}))
    recs = saved(client, student_token)
    data = next(r for r in recs if r["title"] == "Data Analytics & AI Intern")
    assert data["meets_requirements"] is False
    assert data["unmet_requirements"][0] == {
        "unit_id": data["unmet_requirements"][0]["unit_id"], "unit": "Probability and Statistics I",
        "importance": "essential", "required": 60.0, "your_mark": 50.0}
    assert recs[-1]["title"] == "Data Analytics & AI Intern"  # the only ineligible one → last


def test_uses_latest_profile(client, student_token, profile_body):
    save_profile(client, student_token, profile_body(**SWE_PROFILE))
    save_profile(client, student_token, profile_body(
        55, {"Computer Networks": 95, "Operating Systems": 95},
        skills=("Networking (Cisco)", "Linux Administration"),
        interests=("Networking & Cybersecurity",)))
    recs = saved(client, student_token)
    assert recs[0]["title"] == "Networking & IT Support Intern"
    assert GradeProfile.query.count() == 2            # older submissions are kept as history


# ---- TC04 --------------------------------------------------------------------------------

def test_tc04_generate_without_a_profile_lists_every_unit(client, student_token):
    res = client.post(GENERATE, headers=auth_header(student_token))
    assert res.status_code == 400
    assert len(res.get_json()["fields"]["missing_units"]) == 12
    assert Recommendation.query.count() == 0


def test_tc04_incomplete_latest_profile_keeps_previous_results(client, student_token,
                                                              profile_body, seeded):
    """A failed run must not wipe the student's earlier, valid results."""
    save_profile(client, student_token, profile_body())
    before = [(r.opportunity_id, r.rank) for r in Recommendation.query.order_by(Recommendation.rank)]

    # The API no longer accepts incomplete profiles, so insert one directly (11 of 12 units).
    student_id = Recommendation.query.first().student_id
    profile = GradeProfile(student_id=student_id)
    db.session.add(profile)
    db.session.flush()
    for name, uid in list(seeded.items())[:11]:
        db.session.add(Grade(profile_id=profile.profile_id, unit_id=uid, grade_value=70))
    db.session.commit()

    res = client.post(GENERATE, headers=auth_header(student_token))

    assert res.status_code == 400
    assert len(res.get_json()["fields"]["missing_units"]) == 1
    after = [(r.opportunity_id, r.rank) for r in Recommendation.query.order_by(Recommendation.rank)]
    assert after == before


def test_partner_cannot_generate(client, seeded, partner_payload):
    token = register_and_login(client, partner_payload)
    assert client.post(GENERATE, headers=auth_header(token)).status_code == 403


# ---- Saved results -------------------------------------------------------------------------

def test_get_returns_saved_snapshot(client, student_token, profile_body):
    generated = save_profile(client, student_token, profile_body(70)).get_json()["recommendations"]

    res = client.get(SAVED, headers=auth_header(student_token))

    body = res.get_json()
    assert res.status_code == 200
    assert body["generated_at"] is not None and body["profile_complete"] is True
    assert body["profile_updated_at"] is not None
    got = body["eligible"] + body["not_eligible"]
    assert sorted((r["opportunity_id"], r["match_score"]) for r in got) == \
           sorted((r["opportunity_id"], r["match_score"]) for r in generated)
    assert set(got[0]["breakdown"]) == {"grade_score", "skill_score", "interest_score"}


def test_get_before_profile_is_empty(client, student_token):
    body = client.get(SAVED, headers=auth_header(student_token)).get_json()
    assert body == {"generated_at": None, "profile_updated_at": None, "profile_complete": False,
                    "eligible": [], "not_eligible": []}


def test_get_regenerates_after_the_model_changes(client, student_token, profile_body):
    save_profile(client, student_token, profile_body(**SWE_PROFILE))
    # A partner closes an opportunity → the model is refitted → saved results are out of date.
    netsecure = login(client, "info@netsecure.co.ke", DEMO_PASSWORD)
    net = InternshipOpportunity.query.filter_by(title="Networking & IT Support Intern").one()
    # Timestamps are stored to the second, so backdate the saved results to make sure the
    # refit below is clearly newer than them.
    for r in Recommendation.query.all():
        r.generated_at = datetime(2000, 1, 1)
    db.session.commit()
    client.patch(f"/api/partner/opportunities/{net.opportunity_id}/close",
                 headers=auth_header(netsecure))

    recs = saved(client, student_token)

    assert len(recs) == 4
    assert "Networking & IT Support Intern" not in [r["title"] for r in recs]


# ---- Retrain -------------------------------------------------------------------------------

def test_admin_can_retrain_and_sees_unit_and_skill_idf(client, seeded):
    create_user_with_profile({"email": "admin@strathmore.edu", "password": "Admin1234",
                              "role": "system_admin", "name": "Root"})
    token = login(client, "admin@strathmore.edu", "Admin1234")

    res = client.post("/api/admin/model/retrain", headers=auth_header(token))

    assert res.status_code == 200
    body = res.get_json()
    assert body["n_opportunities"] == 5
    idf = {u["unit_name"]: u["idf"] for u in body["idf"]}
    assert len(idf) == 12
    assert idf["Database Systems"] < idf["Computer Networks"]
    skill_idf = {s["name"]: s["idf"] for s in body["skill_idf"]}
    assert len(skill_idf) == 17              # the 4 skills no opportunity requires are ignored
    assert skill_idf["SQL"] < skill_idf["Java"]
    assert body["fitted_at"]


def test_student_cannot_retrain(client, student_token):
    assert client.post("/api/admin/model/retrain",
                       headers=auth_header(student_token)).status_code == 403
