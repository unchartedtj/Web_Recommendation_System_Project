"""Account security: deactivation (and its side effects), password reset + forced change,
change password, last login."""
import pytest

from app.extensions import db
from app.models import Application, InternshipOpportunity, User
from app.seed.catalog import DEFAULT_ADMIN, DEMO_PASSWORD
from tests.conftest import auth_header, login, register_and_login

SWE = "Software Development Intern"
DEACTIVATED = "This account has been deactivated. Contact the WBL office."


def opp_id(title):
    return InternshipOpportunity.query.filter_by(title=title).one().opportunity_id


def user_id(email):
    return User.query.filter_by(email=email).one().user_id


@pytest.fixture
def admin(client, seeded):
    return login(client, DEFAULT_ADMIN["name"], DEFAULT_ADMIN["password"])


@pytest.fixture
def student(client, seeded, profile_body):
    token = register_and_login(client, {
        "role": "student", "email": "stu@strathmore.edu", "password": "Passw0rd123",
        "confirm_password": "Passw0rd123", "admission_no": "70001", "first_name": "Stu",
        "last_name": "Dent", "course": "BBIT", "year_of_study": 3})
    client.put("/api/student/profile", headers=auth_header(token),
               json=profile_body(65, skills=("Java", "Git & GitHub"), interests=("Software Development",)))
    return token


def raw_login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ---- Deactivation ------------------------------------------------------------------------------

def test_deactivated_user_cannot_log_in_and_old_token_stops_working(client, admin, student):
    res = client.patch(f"/api/admin/users/{user_id('stu@strathmore.edu')}/deactivate",
                       headers=auth_header(admin))
    assert res.status_code == 200
    res = raw_login(client, "stu@strathmore.edu", "Passw0rd123")
    assert res.status_code == 403 and res.get_json()["error"] == DEACTIVATED
    for url in ("/api/auth/me", "/api/student/profile", "/api/recommendations"):
        res = client.get(url, headers=auth_header(student))
        assert res.status_code == 401 and res.get_json()["error"] == DEACTIVATED

    # Re-activating restores access.
    client.patch(f"/api/admin/users/{user_id('stu@strathmore.edu')}/activate", headers=auth_header(admin))
    assert raw_login(client, "stu@strathmore.edu", "Passw0rd123").status_code == 200


def test_wrong_password_on_a_deactivated_account_still_says_invalid(client, admin, student):
    client.patch(f"/api/admin/users/{user_id('stu@strathmore.edu')}/deactivate", headers=auth_header(admin))
    assert raw_login(client, "stu@strathmore.edu", "WrongPass1").status_code == 401


def test_deactivating_a_partner_closes_their_open_opportunities(client, admin, student):
    pid = user_id("info@techcorp.co.ke")
    impact = client.get(f"/api/admin/users/{pid}/impact", headers=auth_header(admin)).get_json()
    assert impact == {"open_opportunities": 3, "active_applications": 0}
    res = client.patch(f"/api/admin/users/{pid}/deactivate", headers=auth_header(admin))
    assert res.get_json()["closed_opportunities"] == 3
    titles = [o["title"] for o in
              client.get("/api/opportunities", headers=auth_header(student)).get_json()["opportunities"]]
    assert SWE not in titles and len(titles) == 2                 # only NetSecure's remain
    recs = client.get("/api/recommendations", headers=auth_header(student)).get_json()
    assert SWE not in [r["title"] for r in recs["eligible"] + recs["not_eligible"]]   # retrained


def test_deactivating_a_student_withdraws_active_applications(client, admin, student):
    client.post("/api/applications", headers=auth_header(student), json={"opportunity_id": opp_id(SWE)})
    sid = user_id("stu@strathmore.edu")
    assert client.get(f"/api/admin/users/{sid}/impact", headers=auth_header(admin)).get_json()[
        "active_applications"] == 1
    res = client.patch(f"/api/admin/users/{sid}/deactivate", headers=auth_header(admin))
    assert res.get_json()["withdrawn_applications"] == 1
    a = Application.query.one()
    assert (a.status, a.status_reason) == ("withdrawn", "Account deactivated")


def test_admin_cannot_deactivate_themselves_but_can_deactivate_another_admin(client, admin):
    me = user_id(DEFAULT_ADMIN["email"])
    res = client.patch(f"/api/admin/users/{me}/deactivate", headers=auth_header(admin))
    assert res.status_code == 409 and "your own" in res.get_json()["error"]

    res = client.post("/api/admin/admins", headers=auth_header(admin),
                      json={"name": "Second Admin", "email": "second@strathmore.edu",
                            "password": "Second123"})
    assert res.status_code == 201
    second = res.get_json()["user"]["user_id"]
    assert client.patch(f"/api/admin/users/{second}/deactivate",
                        headers=auth_header(admin)).status_code == 200


def test_last_active_admin_is_protected(client, admin):
    # A second admin deactivates the default admin, leaving themselves as the only active one.
    client.post("/api/admin/admins", headers=auth_header(admin),
                json={"name": "Second Admin", "email": "second@strathmore.edu", "password": "Second123"})
    second = login(client, "second@strathmore.edu", "Second123")
    first_id = user_id(DEFAULT_ADMIN["email"])
    assert client.patch(f"/api/admin/users/{first_id}/deactivate",
                        headers=auth_header(second)).status_code == 200
    # The last active admin can't be deactivated (by themselves, the only one who could try).
    second_id = user_id("second@strathmore.edu")
    res = client.patch(f"/api/admin/users/{second_id}/deactivate", headers=auth_header(second))
    assert res.status_code == 409
    db.session.expire_all()
    assert db.session.get(User, second_id).is_active is True


# ---- Password reset + forced change -------------------------------------------------------------

def test_reset_password_forces_a_change_on_next_login(client, admin, student):
    sid = user_id("stu@strathmore.edu")
    res = client.post(f"/api/admin/users/{sid}/reset-password", headers=auth_header(admin), json={})
    temp = res.get_json()["temporary_password"]
    assert res.status_code == 200 and len(temp) >= 8

    assert raw_login(client, "stu@strathmore.edu", "Passw0rd123").status_code == 401   # old one gone
    res = raw_login(client, "stu@strathmore.edu", temp)
    assert res.status_code == 200 and res.get_json()["user"]["must_change_password"] is True
    token = res.get_json()["access_token"]
    res = client.get("/api/student/profile", headers=auth_header(token))
    assert res.status_code == 403 and res.get_json()["code"] == "password_change_required"
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 200

    res = client.post("/api/auth/change-password", headers=auth_header(token),
                      json={"current_password": temp, "new_password": "NewPass123",
                            "confirm_password": "NewPass123"})
    assert res.status_code == 200 and res.get_json()["user"]["must_change_password"] is False
    assert client.get("/api/student/profile", headers=auth_header(token)).status_code == 200


def test_reset_with_a_weak_temporary_password_is_rejected(client, admin, student):
    sid = user_id("stu@strathmore.edu")
    res = client.post(f"/api/admin/users/{sid}/reset-password", headers=auth_header(admin),
                      json={"temporary_password": "short"})
    assert res.status_code == 400


@pytest.mark.parametrize("body,field", [
    ({"current_password": "Wrong1234", "new_password": "NewPass123", "confirm_password": "NewPass123"},
     "current_password"),
    ({"current_password": "Passw0rd123", "new_password": "short", "confirm_password": "short"},
     "new_password"),
    ({"current_password": "Passw0rd123", "new_password": "nonumbers", "confirm_password": "nonumbers"},
     "new_password"),
    ({"current_password": "Passw0rd123", "new_password": "NewPass123", "confirm_password": "Other123"},
     "confirm_password"),
    ({"current_password": "Passw0rd123", "new_password": "Passw0rd123", "confirm_password": "Passw0rd123"},
     "new_password"),
])
def test_change_password_validation(client, student, body, field):
    res = client.post("/api/auth/change-password", headers=auth_header(student), json=body)
    assert res.status_code == 400 and field in res.get_json()["fields"]


def test_change_password_then_log_in_with_the_new_one(client, student):
    res = client.post("/api/auth/change-password", headers=auth_header(student),
                      json={"current_password": "Passw0rd123", "new_password": "Better456",
                            "confirm_password": "Better456"})
    assert res.status_code == 200
    assert raw_login(client, "stu@strathmore.edu", "Better456").status_code == 200


def test_login_records_last_login(client, seeded):
    login(client, "info@techcorp.co.ke", DEMO_PASSWORD)
    db.session.expire_all()
    assert User.query.filter_by(email="info@techcorp.co.ke").one().last_login_at is not None


def test_users_list_filters_by_role(client, admin, student):
    body = client.get("/api/admin/users?role=industry_partner", headers=auth_header(admin)).get_json()
    assert body["total"] == 2 and all(u["role"] == "industry_partner" for u in body["items"])
