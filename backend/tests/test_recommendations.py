"""API tests: grade helper, recommendation generation (incl. TC04), and retraining."""
import pytest

from app.auth.services import create_user_with_profile
from app.models import GradeProfile, Recommendation
from tests.conftest import auth_header, login, register_and_login

GENERATE = "/api/recommendations/generate"


@pytest.fixture
def student_token(client, seeded, student_payload):
    return register_and_login(client, student_payload)


def full_marks(seeded, default=60, overrides=None):
    """A complete grade body {unit_id: mark} for all 12 units; override by unit name."""
    marks = {str(uid): default for uid in seeded.values()}
    for name, mark in (overrides or {}).items():
        marks[str(seeded[name])] = mark
    return marks


def submit(client, token, marks):
    return client.post("/api/grades", json=marks, headers=auth_header(token))


# ---- Grades helper ------------------------------------------------------------------------

def test_submit_grades_creates_profile(client, student_token, seeded):
    res = submit(client, student_token, full_marks(seeded))
    assert res.status_code == 201
    assert res.get_json()["units_graded"] == 12
    assert GradeProfile.query.count() == 1


@pytest.mark.parametrize("mark", [150, -1, "abc"])
def test_submit_grades_rejects_invalid_marks(client, student_token, seeded, mark):
    res = submit(client, student_token,
                 full_marks(seeded, overrides={"Object Oriented Programming": mark}))
    assert res.status_code == 400
    assert str(seeded["Object Oriented Programming"]) in res.get_json()["fields"]
    assert GradeProfile.query.count() == 0


# ---- Generate ------------------------------------------------------------------------------

def test_generate_returns_full_ranking_and_saves_it(client, student_token, seeded):
    submit(client, student_token, full_marks(seeded, 58, {
        "Object Oriented Programming": 92, "Data Structures and Algorithms": 88}))

    res = client.post(GENERATE, headers=auth_header(student_token))

    assert res.status_code == 200
    recs = res.get_json()["recommendations"]
    assert [r["rank"] for r in recs] == [1, 2, 3, 4, 5]
    top = recs[0]
    assert top["title"] == "Software Development Intern"  # TC07 via the API
    assert top["organization"] == "TechCorp Kenya (Demo)"
    for key in ("opportunity_id", "sector", "match_score", "match_percent",
                "avg_requirement_mark", "meets_requirements", "unmet_requirements"):
        assert key in top
    assert Recommendation.query.count() == 5


def test_unmet_requirements_are_reported(client, student_token, seeded):
    submit(client, student_token, full_marks(seeded, 75, {"Probability and Statistics I": 50}))
    recs = client.post(GENERATE, headers=auth_header(student_token)).get_json()["recommendations"]
    data = next(r for r in recs if r["title"] == "Data Analytics & AI Intern")
    assert data["meets_requirements"] is False
    assert data["unmet_requirements"][0] == {
        "unit_id": seeded["Probability and Statistics I"], "unit": "Probability and Statistics I",
        "importance": "essential", "required": 60.0, "your_mark": 50.0}
    assert recs[-1]["title"] == "Data Analytics & AI Intern"  # the only ineligible one → last


def test_generate_twice_replaces_previous_rows(client, student_token, seeded):
    submit(client, student_token, full_marks(seeded))
    client.post(GENERATE, headers=auth_header(student_token))
    client.post(GENERATE, headers=auth_header(student_token))
    assert Recommendation.query.count() == 5


def test_uses_latest_grade_profile(client, student_token, seeded):
    submit(client, student_token, full_marks(seeded, 55, {
        "Object Oriented Programming": 95, "Data Structures and Algorithms": 95}))
    submit(client, student_token, full_marks(seeded, 55, {
        "Computer Networks": 95, "Operating Systems": 95}))
    recs = client.post(GENERATE, headers=auth_header(student_token)).get_json()["recommendations"]
    assert recs[0]["title"] == "Networking & IT Support Intern"


# ---- TC04 --------------------------------------------------------------------------------

def test_tc04_eleven_of_twelve_units_returns_400_and_writes_nothing(client, student_token, seeded):
    marks = full_marks(seeded)
    del marks[str(seeded["Artificial Intelligence"])]
    submit(client, student_token, marks)

    res = client.post(GENERATE, headers=auth_header(student_token))

    assert res.status_code == 400
    body = res.get_json()
    assert body["error"] == "Grade profile is incomplete"
    assert body["fields"]["missing_units"] == [
        {"unit_id": seeded["Artificial Intelligence"], "unit_name": "Artificial Intelligence"}]
    assert Recommendation.query.count() == 0


def test_tc04_failed_generation_keeps_previous_results(client, student_token, seeded):
    submit(client, student_token, full_marks(seeded))
    client.post(GENERATE, headers=auth_header(student_token))
    before = [(r.opportunity_id, r.rank) for r in Recommendation.query.order_by(Recommendation.rank)]

    incomplete = full_marks(seeded)
    del incomplete[str(seeded["Object Oriented Programming"])]
    submit(client, student_token, incomplete)  # the latest profile is now incomplete
    assert client.post(GENERATE, headers=auth_header(student_token)).status_code == 400

    after = [(r.opportunity_id, r.rank) for r in Recommendation.query.order_by(Recommendation.rank)]
    assert after == before


def test_generate_with_no_grades_lists_every_unit(client, student_token):
    res = client.post(GENERATE, headers=auth_header(student_token))
    assert res.status_code == 400
    assert len(res.get_json()["fields"]["missing_units"]) == 12


def test_partner_cannot_generate(client, seeded, partner_payload):
    token = register_and_login(client, partner_payload)
    assert client.post(GENERATE, headers=auth_header(token)).status_code == 403


# ---- Saved results -----------------------------------------------------------------------

def test_get_returns_saved_snapshot(client, student_token, seeded):
    submit(client, student_token, full_marks(seeded, 70))
    generated = client.post(GENERATE, headers=auth_header(student_token)).get_json()["recommendations"]

    res = client.get("/api/recommendations", headers=auth_header(student_token))

    body = res.get_json()
    assert res.status_code == 200
    assert body["generated_at"] is not None
    assert [(r["opportunity_id"], r["rank"], r["match_score"]) for r in body["recommendations"]] == \
           [(r["opportunity_id"], r["rank"], r["match_score"]) for r in generated]


def test_get_before_generating_is_empty(client, student_token):
    body = client.get("/api/recommendations", headers=auth_header(student_token)).get_json()
    assert body == {"generated_at": None, "recommendations": []}


# ---- Retrain -------------------------------------------------------------------------------

def test_admin_can_retrain(client, seeded):
    create_user_with_profile({"email": "admin@strathmore.edu", "password": "Admin1234",
                              "role": "system_admin", "name": "Admin"})
    token = login(client, "admin@strathmore.edu", "Admin1234")

    res = client.post("/api/admin/model/retrain", headers=auth_header(token))

    assert res.status_code == 200
    body = res.get_json()
    assert body["n_opportunities"] == 5
    idf = {u["unit_name"]: u["idf"] for u in body["idf"]}
    assert len(idf) == 12
    assert idf["Database Systems"] < idf["Computer Networks"]
    assert body["fitted_at"]


def test_student_cannot_retrain(client, student_token):
    assert client.post("/api/admin/model/retrain",
                       headers=auth_header(student_token)).status_code == 403
