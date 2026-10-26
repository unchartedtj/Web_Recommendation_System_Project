"""SUS questionnaire (test case TC10): scoring, one response per user, admin results."""
import csv
import io

import pytest

from app.models import SusResponse
from app.seed.catalog import DEFAULT_ADMIN, DEMO_PASSWORD
from app.sus.services import sus_score
from tests.conftest import auth_header, login, register_and_login

ALL_3 = [3] * 10
BEST = [5, 1] * 5          # agree with every positive (odd) item, disagree with every negative one
WORST = [1, 5] * 5


def body(answers, **extra):
    return {**{f"q{i}": a for i, a in enumerate(answers, start=1)}, **extra}


@pytest.fixture
def student(client, seeded):
    return register_and_login(client, {
        "role": "student", "email": "stu@strathmore.edu", "password": "Passw0rd123",
        "confirm_password": "Passw0rd123", "admission_no": "70001", "first_name": "Stu",
        "last_name": "Dent", "course": "BBIT", "year_of_study": 3})


@pytest.fixture
def partner(client, seeded):
    return login(client, "info@techcorp.co.ke", DEMO_PASSWORD)


@pytest.fixture
def admin(client, seeded):
    return login(client, DEFAULT_ADMIN["name"], DEFAULT_ADMIN["password"])


@pytest.mark.parametrize("answers,expected", [
    (ALL_3, 50.0), (BEST, 100.0), (WORST, 0.0),
    ([4, 2, 4, 2, 4, 2, 4, 2, 4, 2], 75.0),
    ([5, 2, 4, 1, 4, 2, 5, 1, 4, 3], 82.5),
])
def test_sus_scoring(answers, expected):
    assert sus_score(answers) == expected


def test_questions_are_the_ten_standard_statements(client, student):
    res = client.get("/api/sus/questions", headers=auth_header(student)).get_json()
    assert len(res["questions"]) == 10
    assert res["questions"][0] == "I think that I would like to use this system frequently."
    assert res["questions"][9].startswith("I needed to learn a lot of things")


def test_submit_then_update_keeps_one_response_and_hides_the_score(client, student):
    res = client.put("/api/sus", headers=auth_header(student), json=body(ALL_3, comments="Nice"))
    assert res.status_code == 201
    assert "score" not in str(res.get_json()).lower()
    res = client.put("/api/sus", headers=auth_header(student), json=body(BEST))
    assert res.status_code == 200
    assert SusResponse.query.count() == 1
    r = SusResponse.query.one()
    assert (r.sus_score, r.role, r.comments) == (100.0, "student", None)
    mine = client.get("/api/sus/mine", headers=auth_header(student)).get_json()["response"]
    assert mine["q1"] == 5 and "sus_score" not in mine


@pytest.mark.parametrize("answers", [ALL_3[:9], [3] * 9 + [6], [3] * 9 + [0], [3] * 9 + ["3"]])
def test_all_ten_valid_answers_are_required(client, student, answers):
    res = client.put("/api/sus", headers=auth_header(student), json=body(answers))
    assert res.status_code == 400
    assert SusResponse.query.count() == 0


def test_admins_cannot_submit(client, admin):
    assert client.put("/api/sus", headers=auth_header(admin), json=body(ALL_3)).status_code == 403


def test_admin_results_mean_per_role_and_target(client, student, partner, admin):
    client.put("/api/sus", headers=auth_header(student), json=body(ALL_3))      # 50
    client.put("/api/sus", headers=auth_header(partner), json=body(BEST))       # 100
    res = client.get("/api/admin/sus", headers=auth_header(admin)).get_json()
    assert res["count"] == 2
    assert (res["mean"], res["min"], res["max"]) == (75.0, 50.0, 100.0)
    assert res["meets_target"] is True and res["target"] == 68
    assert res["by_role"] == {"student": {"count": 1, "mean": 50.0},
                              "industry_partner": {"count": 1, "mean": 100.0}}
    assert res["items"][0]["average"] == 4.0          # (3 + 5) / 2
    assert res["items"][1]["average"] == 2.0          # (3 + 1) / 2
    counts = {b["range"]: b["count"] for b in res["distribution"]}
    assert counts["50-59"] == 1 and counts["90-100"] == 1


def test_mean_below_target(client, student, admin):
    client.put("/api/sus", headers=auth_header(student), json=body(WORST))
    res = client.get("/api/admin/sus", headers=auth_header(admin)).get_json()
    assert (res["mean"], res["meets_target"]) == (0.0, False)


def test_sus_csv_export(client, student, admin):
    client.put("/api/sus", headers=auth_header(student), json=body(ALL_3, comments="Good"))
    res = client.get("/api/admin/sus/export.csv", headers=auth_header(admin))
    rows = list(csv.reader(io.StringIO(res.get_data(as_text=True))))
    assert rows[0][:12] == ["response_id", "role", "q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8",
                            "q9", "q10"]
    assert rows[0][12:] == ["sus_score", "comments", "created_at", "updated_at"]
    assert rows[1][1:13] == ["student"] + ["3"] * 10 + ["50.0"]
    assert rows[1][13] == "Good"
