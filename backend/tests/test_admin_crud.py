"""Admin create / edit / delete for students, partners, internships and accounts."""
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import (ActivityLog, Application, InternshipOpportunity, PlacementRecord, Student,
                        User)
from app.seed.catalog import DEFAULT_ADMIN, DEMO_PASSWORD
from tests.conftest import auth_header, login, register_and_login

SWE = "Software Development Intern"


@pytest.fixture
def admin(client, seeded):
    return login(client, DEFAULT_ADMIN["name"], DEFAULT_ADMIN["password"])


STUDENT = {"email": "new.student@strathmore.edu", "password": "12345678A", "confirm_password": "12345678A",
           "admission_no": "190001", "first_name": "Wanjiru", "last_name": "Kariuki",
           "course": "BBIT", "year_of_study": 3}
PARTNER = {"email": "hr@newco.co.ke", "password": "12345678A", "confirm_password": "12345678A",
           "organization_name": "NewCo Kenya", "contact_person": "Otieno Juma", "phone": "0712 345 678"}


def api(client, token, method, url, **body):
    res = client.open(url, method=method, headers=auth_header(token), json=body or None)
    return res.status_code, res.get_json()


def opportunity_body(seeded, skill_ids, sector_ids, **extra):
    return {"title": "Cloud Support Intern", "description": "Help run cloud services.",
            "sector_id": sector_ids["IT Support & Infrastructure"], "location": "Nairobi",
            "duration_months": 3, "slots": 2,
            "application_deadline": (date.today() + timedelta(days=30)).isoformat(),
            "requirements": [{"unit_id": seeded["Operating Systems"], "importance": "essential", "min_mark": 50},
                             {"unit_id": seeded["Computer Networks"], "importance": "desirable"}],
            "skills": [{"skill_id": skill_ids["Linux Administration"], "importance": "essential"}],
            **extra}


# ---- Students -----------------------------------------------------------------------------------

def test_admin_creates_edits_and_deletes_a_student(client, admin):
    status, body = api(client, admin, "POST", "/api/admin/students", **STUDENT)
    assert status == 201
    sid = body["student"]["student_id"]
    assert login(client, STUDENT["email"], STUDENT["password"])          # the account works

    status, body = api(client, admin, "PUT", f"/api/admin/students/{sid}",
                       course="BSc Computer Science", year_of_study=4)
    assert status == 200
    assert (body["student"]["course"], body["student"]["year_of_study"]) == ("BSc Computer Science", 4)
    assert body["student"]["email"] == STUDENT["email"]                  # unchanged fields kept

    status, _ = api(client, admin, "DELETE", f"/api/admin/students/{sid}")
    assert status == 200
    assert User.query.filter_by(email=STUDENT["email"]).first() is None
    assert db.session.get(Student, sid) is None


@pytest.mark.parametrize("change,field", [
    ({"email": "not-an-email"}, "email"), ({"year_of_study": 7}, "year_of_study"),
    ({"admission_no": "ABC"}, "admission_no"), ({"first_name": ""}, "first_name"),
])
def test_student_edit_validation(client, admin, change, field):
    sid = api(client, admin, "POST", "/api/admin/students", **STUDENT)[1]["student"]["student_id"]
    status, body = api(client, admin, "PUT", f"/api/admin/students/{sid}", **change)
    assert status == 400 and field in body["fields"]


def test_duplicate_email_and_admission_no_are_rejected(client, admin):
    api(client, admin, "POST", "/api/admin/students", **STUDENT)
    assert api(client, admin, "POST", "/api/admin/students", **STUDENT)[0] == 409
    other = {**STUDENT, "email": "other@strathmore.edu", "admission_no": "190002"}
    sid = api(client, admin, "POST", "/api/admin/students", **other)[1]["student"]["student_id"]
    status, body = api(client, admin, "PUT", f"/api/admin/students/{sid}", admission_no="190001")
    assert status == 409 and "admission_no" in body["fields"]
    status, body = api(client, admin, "PUT", f"/api/admin/students/{sid}", email=STUDENT["email"])
    assert status == 409 and "email" in body["fields"]


def test_deleting_a_student_removes_their_applications_and_placement(client, admin, profile_body):
    token = register_and_login(client, {**STUDENT, "role": "student"})
    client.put("/api/student/profile", headers=auth_header(token),
               json=profile_body(70, skills=("Java", "Git & GitHub"), interests=("Software Development",)))
    oid = InternshipOpportunity.query.filter_by(title=SWE).one().opportunity_id
    aid = client.post("/api/applications", headers=auth_header(token),
                      json={"opportunity_id": oid}).get_json()["application"]["application_id"]
    partner = login(client, "info@techcorp.co.ke", DEMO_PASSWORD)
    client.patch(f"/api/partner/applications/{aid}", headers=auth_header(partner), json={"action": "accept"})
    assert PlacementRecord.query.count() == 1

    sid = User.query.filter_by(email=STUDENT["email"]).one().student.student_id
    status, body = api(client, admin, "DELETE", f"/api/admin/students/{sid}")
    assert status == 200 and (body["applications"], body["placements"]) == (1, 1)
    assert Application.query.count() == 0 and PlacementRecord.query.count() == 0


# ---- Partners -----------------------------------------------------------------------------------

def test_admin_creates_edits_and_deletes_a_partner(client, admin):
    status, body = api(client, admin, "POST", "/api/admin/partners", **PARTNER)
    assert status == 201
    pid = body["partner"]["partner_id"]
    assert body["partner"]["phone"] == "+254712345678"                   # same phone rules as sign-up
    status, body = api(client, admin, "PUT", f"/api/admin/partners/{pid}", organization_name="NewCo Ltd")
    assert status == 200 and body["partner"]["organization_name"] == "NewCo Ltd"
    assert api(client, admin, "PUT", f"/api/admin/partners/{pid}", phone="12")[0] == 400
    assert api(client, admin, "DELETE", f"/api/admin/partners/{pid}")[0] == 200
    assert User.query.filter_by(email=PARTNER["email"]).first() is None


def test_deleting_a_partner_removes_their_internships_and_retrains(client, admin, engine):
    tech = User.query.filter_by(email="info@techcorp.co.ke").one().industry_partner
    impact = client.get(f"/api/admin/users/{tech.user_id}/impact", headers=auth_header(admin)).get_json()
    assert impact["opportunities"] == 3
    status, body = api(client, admin, "DELETE", f"/api/admin/partners/{tech.partner_id}")
    assert status == 200 and body["opportunities"] == 3
    assert InternshipOpportunity.query.count() == 2                      # only NetSecure's remain
    assert len(engine.model["opportunity_ids"]) == 2


# ---- Internships --------------------------------------------------------------------------------

def test_admin_posts_edits_and_deletes_an_internship(client, admin, seeded, skill_ids, sector_ids, engine):
    tech = User.query.filter_by(email="info@techcorp.co.ke").one().industry_partner
    body = opportunity_body(seeded, skill_ids, sector_ids, partner_id=tech.partner_id)
    status, res = api(client, admin, "POST", "/api/admin/opportunities", **body)
    assert status == 201
    oid = res["opportunity"]["opportunity_id"]
    assert res["opportunity"]["organization_name"] == "TechCorp Kenya"
    assert oid in engine.model["opportunity_ids"]                        # retrained

    form = client.get(f"/api/admin/opportunities/{oid}", headers=auth_header(admin)).get_json()["opportunity"]
    assert form["title"] == "Cloud Support Intern"
    status, res = api(client, admin, "PUT", f"/api/admin/opportunities/{oid}",
                      **{**body, "title": "Cloud Operations Intern", "slots": 4})
    assert status == 200 and (res["opportunity"]["title"], res["opportunity"]["slots"]) == ("Cloud Operations Intern", 4)

    assert api(client, admin, "DELETE", f"/api/admin/opportunities/{oid}")[0] == 200
    assert db.session.get(InternshipOpportunity, oid) is None
    assert oid not in engine.model["opportunity_ids"]


def test_internship_needs_a_company_and_valid_fields(client, admin, seeded, skill_ids, sector_ids):
    body = opportunity_body(seeded, skill_ids, sector_ids, location="Narnia")
    status, res = api(client, admin, "POST", "/api/admin/opportunities", **body)
    assert status == 400 and {"partner_id", "location"} <= set(res["fields"])


def test_admin_actions_are_logged(client, admin):
    sid = api(client, admin, "POST", "/api/admin/students", **STUDENT)[1]["student"]["student_id"]
    api(client, admin, "DELETE", f"/api/admin/students/{sid}")
    actions = {a.action for a in ActivityLog.query.all()}
    assert {"user.created_by_admin", "user.deleted"} <= actions


# ---- Any account ------------------------------------------------------------------------------

def test_delete_account_rules(client, admin):
    me = User.query.filter_by(email=DEFAULT_ADMIN["email"]).one()
    status, body = api(client, admin, "DELETE", f"/api/admin/users/{me.user_id}")
    assert status == 409 and "your own" in body["error"]
    other = api(client, admin, "POST", "/api/admin/admins", name="Second Admin",
                email="second@strathmore.edu", password="Second123")[1]["user"]["user_id"]
    assert api(client, admin, "DELETE", f"/api/admin/users/{other}")[0] == 200
    sid = api(client, admin, "POST", "/api/admin/students", **STUDENT)[1]["student"]["user_id"]
    assert api(client, admin, "DELETE", f"/api/admin/users/{sid}")[0] == 200


def test_non_admins_cannot_use_crud(client, seeded):
    partner = login(client, "info@techcorp.co.ke", DEMO_PASSWORD)
    assert api(client, partner, "POST", "/api/admin/students", **STUDENT)[0] == 403
    assert api(client, partner, "DELETE", "/api/admin/opportunities/1")[0] == 403
