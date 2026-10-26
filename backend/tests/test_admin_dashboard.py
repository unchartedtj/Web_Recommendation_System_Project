"""Admin dashboard API: placements (TC09), records, opportunities, catalogue units, model,
activity log, CSV exports, access control and the reset-demo command."""
import csv
import io
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import ActivityLog, InternshipOpportunity, PlacementRecord
from app.seed.catalog import DEFAULT_ADMIN, DEMO_PASSWORD
from tests.conftest import auth_header, login, register_and_login

SWE = "Software Development Intern"
DATA = "Data Analytics & AI Intern"


def opp_id(title):
    return InternshipOpportunity.query.filter_by(title=title).one().opportunity_id


@pytest.fixture
def admin(client, seeded):
    return login(client, DEFAULT_ADMIN["name"], DEFAULT_ADMIN["password"])


@pytest.fixture
def techcorp(client, seeded):
    return login(client, "info@techcorp.co.ke", DEMO_PASSWORD)


@pytest.fixture
def make_student(client, profile_body):
    def make(n, profile=True):
        token = register_and_login(client, {
            "role": "student", "email": f"student{n}@strathmore.edu",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123",
            "admission_no": f"7000{n}", "first_name": f"Stu{n}", "last_name": "Dent",
            "course": "BBIT", "year_of_study": 3})
        if profile:
            res = client.put("/api/student/profile", headers=auth_header(token),
                             json=profile_body(65, skills=("Java", "Git & GitHub"),
                                               interests=("Software Development",)))
            assert res.status_code == 200, res.get_json()
        return token
    return make


def apply_and_accept(client, student_token, partner_token, title=SWE, **accept_body):
    res = client.post("/api/applications", headers=auth_header(student_token),
                      json={"opportunity_id": opp_id(title)})
    app_id = res.get_json()["application"]["application_id"]
    res = client.patch(f"/api/partner/applications/{app_id}", headers=auth_header(partner_token),
                       json={"action": "accept", **accept_body})
    assert res.status_code == 200, res.get_json()
    return PlacementRecord.query.filter_by(application_id=app_id).one().placement_id


def patch_placement(client, admin, pid, **body):
    res = client.patch(f"/api/admin/placements/{pid}", headers=auth_header(admin), json=body)
    return res.status_code, res.get_json()


# ---- TC09: placement records ------------------------------------------------------------------

def test_tc09_admin_sees_all_placement_records(client, admin, techcorp, make_student):
    apply_and_accept(client, make_student(1), techcorp, SWE, start_date="2027-01-10")
    apply_and_accept(client, make_student(2), techcorp, DATA)
    body = client.get("/api/admin/placements", headers=auth_header(admin)).get_json()
    assert body["total"] == 2
    rows = {r["student"]["name"]: r for r in body["items"]}
    assert rows["Stu1 Dent"]["company"]["name"] == "TechCorp Kenya"
    assert rows["Stu1 Dent"]["opportunity"]["title"] == SWE
    assert rows["Stu1 Dent"]["status"] == "confirmed"
    assert rows["Stu1 Dent"]["student"]["admission_no"] == "70001"
    assert rows["Stu1 Dent"]["start_date"] == "2027-01-10"
    assert rows["Stu2 Dent"]["opportunity"]["title"] == DATA
    assert rows["Stu1 Dent"]["match_percent_at_apply"] > 0
    # Filters
    only = client.get("/api/admin/placements?search=70002", headers=auth_header(admin)).get_json()
    assert [r["student"]["name"] for r in only["items"]] == ["Stu2 Dent"]
    detail = client.get(f"/api/admin/placements/{rows['Stu1 Dent']['placement_id']}",
                        headers=auth_header(admin)).get_json()["placement"]
    assert detail["application"]["snapshot"]["match_score"] > 0


def test_valid_placement_transitions(client, admin, techcorp, make_student):
    pid = apply_and_accept(client, make_student(1), techcorp)
    status, body = patch_placement(client, admin, pid, status="ongoing", start_date="2027-01-10",
                                   end_date="2027-04-10")
    assert status == 200 and body["placement"]["status"] == "ongoing"
    status, body = patch_placement(client, admin, pid, status="completed")
    assert status == 200 and body["placement"]["status"] == "completed"

    pid2 = apply_and_accept(client, make_student(2), techcorp, DATA)
    status, body = patch_placement(client, admin, pid2, status="terminated", reason="Left early")
    assert status == 200 and body["placement"]["status_reason"] == "Left early"


@pytest.mark.parametrize("body,expected", [
    ({"status": "completed"}, 409),                                   # confirmed → completed
    ({"status": "terminated"}, 400),                                  # no reason
    ({"status": "ongoing"}, 400),                                     # no start date
    ({"start_date": "2027-02-01", "end_date": "2027-01-01"}, 400),    # end before start
    ({"status": "finished"}, 400),                                    # unknown status
])
def test_invalid_placement_changes(client, admin, techcorp, make_student, body, expected):
    pid = apply_and_accept(client, make_student(1), techcorp)
    assert patch_placement(client, admin, pid, **body)[0] == expected
    assert db.session.get(PlacementRecord, pid).status == "confirmed"


def test_final_placement_cannot_change(client, admin, techcorp, make_student):
    pid = apply_and_accept(client, make_student(1), techcorp)
    patch_placement(client, admin, pid, status="terminated", reason="Company closed")
    assert patch_placement(client, admin, pid, status="ongoing", start_date="2027-01-01")[0] == 409


def test_placements_csv_export(client, admin, techcorp, make_student):
    apply_and_accept(client, make_student(1), techcorp, start_date="2027-01-10")
    res = client.get("/api/admin/placements/export.csv", headers=auth_header(admin))
    assert res.status_code == 200 and res.mimetype == "text/csv"
    rows = list(csv.reader(io.StringIO(res.get_data(as_text=True))))
    assert rows[0] == ["placement_id", "student", "admission_no", "company", "internship", "sector",
                       "status", "start_date", "end_date", "match_percent_at_apply",
                       "status_reason", "created_at"]
    assert len(rows) == 2
    assert rows[1][1:5] == ["Stu1 Dent", "70001", "TechCorp Kenya", SWE]
    assert rows[1][6:8] == ["confirmed", "2027-01-10"]


# ---- Access control ------------------------------------------------------------------------------

def test_non_admins_get_403_on_every_admin_route(app, client, seeded, make_student, techcorp):
    student = make_student(1, profile=False)
    rules = [r for r in app.url_map.iter_rules() if r.rule.startswith("/api/admin")]
    assert len(rules) > 25
    for rule in rules:
        url = rule.rule
        for arg in rule.arguments:
            url = url.replace(f"<int:{arg}>", "1")
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            for token in (student, techcorp):
                res = client.open(url, method=method, headers=auth_header(token), json={})
                assert res.status_code == 403, (method, url, res.status_code)


# ---- Overview, records, opportunities ------------------------------------------------------------

def test_overview_counts(client, admin, techcorp, make_student):
    apply_and_accept(client, make_student(1), techcorp)
    make_student(2, profile=False)
    body = client.get("/api/admin/overview", headers=auth_header(admin)).get_json()
    assert body["students"] == {"total": 2, "complete_profiles": 1}
    assert body["partners"] == 2
    assert body["applications"]["accepted"] == 1
    assert body["placements"]["confirmed"] == 1
    assert body["match"]["accepted_avg_percent"] == body["match"]["all_avg_percent"]
    assert sum(s["count"] for s in body["opportunities_per_sector"]) == 5
    assert body["recent_activity"][0]["action"]


def test_student_records_filters_and_detail(client, admin, make_student):
    make_student(1)
    make_student(2, profile=False)
    page = client.get("/api/admin/students?profile_complete=true", headers=auth_header(admin)).get_json()
    assert [s["name"] for s in page["items"]] == ["Stu1 Dent"]
    page = client.get("/api/admin/students?search=70002", headers=auth_header(admin)).get_json()
    assert [s["admission_no"] for s in page["items"]] == ["70002"]
    sid = client.get("/api/admin/students?search=70001", headers=auth_header(admin)).get_json()["items"][0]["student_id"]
    detail = client.get(f"/api/admin/students/{sid}", headers=auth_header(admin)).get_json()["student"]
    assert len(detail["grades"]) == 12 and "Java" in detail["skills"]
    assert detail["top_recommendations"]


def test_partner_records(client, admin):
    page = client.get("/api/admin/partners", headers=auth_header(admin)).get_json()
    assert page["total"] == 2
    tech = next(p for p in page["items"] if p["organization_name"] == "TechCorp Kenya")
    assert tech["opportunities"] == 3
    detail = client.get(f"/api/admin/partners/{tech['partner_id']}", headers=auth_header(admin)).get_json()
    assert len(detail["partner"]["opportunity_list"]) == 3


def test_admin_close_and_reopen_opportunity(client, admin):
    oid = opp_id(SWE)
    res = client.patch(f"/api/admin/opportunities/{oid}/close", headers=auth_header(admin))
    assert res.status_code == 200 and res.get_json()["opportunity"]["status"] == "closed"
    res = client.patch(f"/api/admin/opportunities/{oid}/reopen", headers=auth_header(admin))
    assert res.status_code == 200 and res.get_json()["opportunity"]["status"] == "open"

    o = db.session.get(InternshipOpportunity, oid)
    o.status, o.application_deadline = "closed", date.today() - timedelta(days=1)
    db.session.commit()
    res = client.patch(f"/api/admin/opportunities/{oid}/reopen", headers=auth_header(admin))
    assert res.status_code == 409 and "deadline" in res.get_json()["error"]
    page = client.get("/api/admin/opportunities?status=closed", headers=auth_header(admin)).get_json()
    assert [o["opportunity_id"] for o in page["items"]] == [oid]


# ---- Catalogue: units ---------------------------------------------------------------------------

def test_adding_a_unit_needs_confirm_and_makes_profiles_incomplete(client, admin, make_student):
    student = make_student(1)
    res = client.post("/api/admin/units", headers=auth_header(admin), json={"name": "Cloud Computing"})
    assert res.status_code == 409
    assert res.get_json()["affected_students"] == 1
    res = client.post("/api/admin/units", headers=auth_header(admin),
                      json={"name": "Cloud Computing", "confirm": True})
    assert res.status_code == 201
    profile = client.get("/api/student/profile", headers=auth_header(student)).get_json()["profile"]
    assert profile["is_complete"] is False


def test_catalogue_lists_show_in_use_counts(client, admin, make_student):
    make_student(1)
    skills = client.get("/api/admin/skills", headers=auth_header(admin)).get_json()["skills"]
    java = next(s for s in skills if s["name"] == "Java")
    assert java["in_use"] >= 2                       # an opportunity + the student
    units = client.get("/api/admin/units", headers=auth_header(admin)).get_json()["units"]
    assert all(u["in_use"] >= 1 for u in units if u["is_active"])


# ---- Model, activity log --------------------------------------------------------------------------

def test_model_page(client, admin):
    body = client.get("/api/admin/model", headers=auth_header(admin)).get_json()
    assert body["n_opportunities"] == 5 and body["fitted_at"]
    assert body["unit_idf"] and body["skill_idf"]
    assert body["match_weights"] == {"grades": 0.60, "skills": 0.25, "interests": 0.15}
    assert body["evaluation"]["ablation"]                       # evaluation/ablation.csv exists


def test_activity_log_records_key_actions(client, admin, techcorp, make_student):
    pid = apply_and_accept(client, make_student(1), techcorp)
    patch_placement(client, admin, pid, status="ongoing", start_date="2027-01-10")
    client.post("/api/admin/sectors", headers=auth_header(admin), json={"name": "Robotics"})
    actions = {a.action for a in ActivityLog.query.all()}
    for expected in ("auth.registered", "auth.login", "application.submitted",
                     "application.accepted", "placement.created", "placement.updated",
                     "catalog.sector_created"):
        assert expected in actions, expected
    page = client.get("/api/admin/activity?action=placement", headers=auth_header(admin)).get_json()
    assert {i["action"] for i in page["items"]} == {"placement.created", "placement.updated"}


def test_pagination_shape(client, admin):
    body = client.get("/api/admin/opportunities?per_page=2&page=2", headers=auth_header(admin)).get_json()
    assert (body["page"], body["per_page"], body["total"], body["pages"]) == (2, 2, 5, 3)
    assert len(body["items"]) == 2


# ---- reset-demo ---------------------------------------------------------------------------------

def test_reset_demo_refuses_without_the_confirmation_word(app, seeded):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["reset-demo", "--confirm", "yes"])
    assert result.exit_code != 0 and "Cancelled" in result.output
    result = runner.invoke(args=["reset-demo"], input="reset\n")      # wrong case
    assert result.exit_code != 0
    assert InternshipOpportunity.query.count() == 5                    # nothing was deleted
