"""Tests for applications (student side), candidates (partner side) and placement records.

Uses the seeded catalogue WITHOUT the demo students, and registers fresh students, so each
test controls exactly which applications exist.
    info@techcorp.co.ke  owns Software Development (SWE, 3 slots), Web & Mobile and Data (2 slots)
    info@netsecure.co.ke owns Networking and Business Analyst
"""
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import Application, InternshipOpportunity, OpportunityStatus, PlacementRecord
from app.seed.catalog import DEMO_PASSWORD
from tests.conftest import auth_header, login, register_and_login

SWE = "Software Development Intern"
DATA = "Data Analytics & AI Intern"


def opp_id(title):
    return InternshipOpportunity.query.filter_by(title=title).one().opportunity_id


@pytest.fixture
def make_student(client, profile_body):
    """make_student(n) registers student n, saves a complete profile and returns a token.
    make_student(n, profile=False) leaves the profile empty."""
    def make(n, overrides=None, profile=True, skills=("Java", "Git & GitHub", "Python"),
             interests=("Software Development",)):
        token = register_and_login(client, {
            "role": "student", "email": f"student{n}@strathmore.edu",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123",
            "admission_no": f"7000{n}", "first_name": f"Stu{n}", "last_name": "Dent",
            "course": "BBIT", "year_of_study": 3})
        if profile:
            res = client.put("/api/student/profile", headers=auth_header(token),
                             json=profile_body(65, overrides, skills=skills, interests=interests))
            assert res.status_code == 200, res.get_json()
        return token
    return make


@pytest.fixture
def techcorp(client, seeded):
    return login(client, "info@techcorp.co.ke", DEMO_PASSWORD)


@pytest.fixture
def netsecure(client, seeded):
    return login(client, "info@netsecure.co.ke", DEMO_PASSWORD)


def apply(client, token, title, **body):
    res = client.post("/api/applications", headers=auth_header(token),
                      json={"opportunity_id": opp_id(title), **body})
    return res.status_code, res.get_json()


def decide(client, token, application_id, action, **body):
    res = client.patch(f"/api/partner/applications/{application_id}",
                       headers=auth_header(token), json={"action": action, **body})
    return res.status_code, res.get_json()


def withdraw(client, token, application_id):
    res = client.patch(f"/api/applications/{application_id}/withdraw", headers=auth_header(token))
    return res.status_code, res.get_json()


def app_id(body):
    return body["application"]["application_id"]


# ---- Applying ---------------------------------------------------------------------------------

def test_apply_stores_snapshot_and_match_score(client, make_student):
    token = make_student(1)
    status, body = apply(client, token, SWE, motivation_note="  I love Java.  ")
    assert status == 201, body
    a = db.session.get(Application, app_id(body))
    assert a.status == "pending"
    assert a.motivation_note == "I love Java."
    assert 0 < a.match_score_at_apply <= 1
    assert a.meets_requirements_at_apply is True
    snap = a.profile_snapshot
    assert snap["match_score"] == a.match_score_at_apply
    assert set(snap["breakdown"]) == {"grade_score", "skill_score", "interest_score"}
    assert "Object Oriented Programming" in {u["unit"] for u in snap["units"]}
    assert any(s["skill"] == "Java" and s["i_have"] for s in snap["skills"])
    assert snap["interests"] == ["Software Development"]
    assert body["application"]["match_percent_at_apply"] == round(a.match_score_at_apply * 100, 2)


def test_incomplete_profile_cannot_apply(client, make_student):
    status, body = apply(client, make_student(1, profile=False), SWE)
    assert status == 409 and "profile" in body["error"].lower()


def test_closed_opportunity_cannot_be_applied_to(client, make_student):
    token = make_student(1)
    InternshipOpportunity.query.filter_by(title=SWE).one().status = OpportunityStatus.CLOSED
    db.session.commit()
    status, body = apply(client, token, SWE)
    assert status == 409 and "closed" in body["error"]


def test_expired_opportunity_cannot_be_applied_to(client, make_student):
    token = make_student(1)
    InternshipOpportunity.query.filter_by(title=SWE).one().application_deadline = (
        date.today() - timedelta(days=1))
    db.session.commit()
    assert apply(client, token, SWE)[0] == 409


def test_unknown_opportunity_404_and_long_note_400(client, make_student):
    token = make_student(1)
    res = client.post("/api/applications", headers=auth_header(token),
                      json={"opportunity_id": 999999})
    assert res.status_code == 404
    status, body = apply(client, token, SWE, motivation_note="x" * 501)
    assert status == 400 and "motivation_note" in body["fields"]


def test_duplicate_and_reapply_after_withdraw_are_blocked(client, make_student):
    token = make_student(1)
    status, body = apply(client, token, SWE)
    assert status == 201
    assert apply(client, token, SWE)[0] == 409
    assert withdraw(client, token, app_id(body))[0] == 200
    status, body = apply(client, token, SWE)
    assert status == 409 and "already applied" in body["error"]


def test_below_minimum_needs_acknowledgement(client, make_student):
    token = make_student(1, overrides={"Object Oriented Programming": 40})
    status, body = apply(client, token, SWE)
    assert status == 409
    assert "acknowledge_below_minimum" in body["fields"]
    assert [u["unit"] for u in body["unmet_requirements"]] == ["Object Oriented Programming"]
    assert Application.query.count() == 0                      # nothing saved
    status, body = apply(client, token, SWE, acknowledge_below_minimum=True)
    assert status == 201
    assert body["application"]["meets_requirements_at_apply"] is False


def test_student_with_placement_cannot_apply(client, make_student, techcorp):
    token = make_student(1)
    _, body = apply(client, token, SWE)
    assert decide(client, techcorp, app_id(body), "accept")[0] == 200
    status, body = apply(client, token, DATA)
    assert status == 409 and "placement" in body["error"]


# ---- Status transitions ---------------------------------------------------------------------

def test_allowed_partner_transitions(client, make_student, techcorp):
    a1 = app_id(apply(client, make_student(1), SWE)[1])
    a2 = app_id(apply(client, make_student(2), SWE)[1])
    a3 = app_id(apply(client, make_student(3), SWE)[1])
    assert decide(client, techcorp, a1, "shortlist")[1]["application"]["status"] == "shortlisted"
    assert decide(client, techcorp, a1, "accept")[1]["application"]["status"] == "accepted"
    status, body = decide(client, techcorp, a2, "reject", reason="Not enough experience")
    assert status == 200 and body["application"]["status_reason"] == "Not enough experience"
    assert decide(client, techcorp, a3, "accept")[0] == 200                   # pending → accepted
    assert db.session.get(Application, a2).decided_at is not None


@pytest.mark.parametrize("first,then", [
    ("shortlist", "shortlist"),
    ("reject", "shortlist"), ("reject", "accept"), ("reject", "reject"),
    ("accept", "reject"), ("accept", "shortlist"), ("accept", "accept"),
])
def test_disallowed_partner_transitions_return_409(client, make_student, techcorp, first, then):
    a = app_id(apply(client, make_student(1), SWE)[1])
    assert decide(client, techcorp, a, first)[0] == 200
    status, body = decide(client, techcorp, a, then)
    assert status == 409 and "already" in body["error"]


def test_withdraw_rules(client, make_student, techcorp):
    token = make_student(1)
    a = app_id(apply(client, token, SWE)[1])
    assert decide(client, techcorp, a, "shortlist")[0] == 200
    assert withdraw(client, token, a)[1]["application"]["status"] == "withdrawn"   # shortlisted ok
    assert withdraw(client, token, a)[0] == 409                                    # already final
    assert decide(client, techcorp, a, "accept")[0] == 409

    other = make_student(2)
    b = app_id(apply(client, other, DATA)[1])
    assert decide(client, techcorp, b, "accept")[0] == 200
    assert withdraw(client, other, b)[0] == 409                                    # accepted is final


def test_bad_action_and_invalid_dates_return_400(client, make_student, techcorp):
    a = app_id(apply(client, make_student(1), SWE)[1])
    assert decide(client, techcorp, a, "hire")[0] == 400
    status, body = decide(client, techcorp, a, "accept", start_date="2027-02-01",
                          end_date="2027-01-01")
    assert status == 400 and "end_date" in body["fields"]
    assert decide(client, techcorp, a, "accept", start_date="next week")[0] == 400
    assert PlacementRecord.query.count() == 0


# ---- Ownership --------------------------------------------------------------------------------

def test_partner_cannot_act_on_another_partners_applications(client, make_student, netsecure):
    a = app_id(apply(client, make_student(1), SWE)[1])
    assert decide(client, netsecure, a, "shortlist")[0] == 403
    res = client.get(f"/api/partner/opportunities/{opp_id(SWE)}/candidates",
                     headers=auth_header(netsecure))
    assert res.status_code == 403


def test_student_cannot_withdraw_someone_elses_application(client, make_student):
    a = app_id(apply(client, make_student(1), SWE)[1])
    assert withdraw(client, make_student(2), a)[0] == 403


def test_students_cannot_use_partner_endpoints(client, make_student):
    token = make_student(1)
    a = app_id(apply(client, token, SWE)[1])
    assert decide(client, token, a, "accept")[0] == 403


# ---- Accepting --------------------------------------------------------------------------------

def test_accept_creates_one_placement_and_withdraws_other_applications(client, make_student,
                                                                       techcorp):
    token = make_student(1)
    a = app_id(apply(client, token, SWE)[1])
    other = app_id(apply(client, token, DATA)[1])
    status, body = decide(client, techcorp, a, "accept", start_date="2027-01-10",
                          end_date="2027-04-10")
    assert status == 200
    placements = PlacementRecord.query.all()
    assert len(placements) == 1
    p = placements[0]
    assert (p.application_id, p.status) == (a, "confirmed")
    assert (p.start_date, p.end_date) == (date(2027, 1, 10), date(2027, 4, 10))
    other_app = db.session.get(Application, other)
    assert other_app.status == "withdrawn"
    assert other_app.status_reason == "Placed in another internship"
    assert body["application"]["placement"]["start_date"] == "2027-01-10"


def test_filling_slots_closes_opportunity_and_rejects_the_rest(client, make_student, techcorp):
    # Data Analytics has 2 slots.
    tokens = [make_student(n, skills=("Python", "SQL"), interests=("Data Analytics & AI",))
              for n in (1, 2, 3)]
    ids = [app_id(apply(client, t, DATA)[1]) for t in tokens]
    assert decide(client, techcorp, ids[0], "accept")[0] == 200
    assert InternshipOpportunity.query.filter_by(title=DATA).one().status == "open"
    assert decide(client, techcorp, ids[1], "accept")[0] == 200

    db.session.expire_all()
    assert InternshipOpportunity.query.filter_by(title=DATA).one().status == "closed"
    rest = db.session.get(Application, ids[2])
    assert (rest.status, rest.status_reason) == ("rejected", "All positions filled")
    # The model was refitted: the closed internship left the recommendations.
    recs = client.get("/api/recommendations", headers=auth_header(tokens[2])).get_json()
    assert DATA not in [r["title"] for r in recs["eligible"] + recs["not_eligible"]]


def test_accept_when_slots_already_full_returns_409(client, make_student, techcorp):
    a = app_id(apply(client, make_student(1), SWE)[1])
    b = app_id(apply(client, make_student(2), SWE)[1])
    assert decide(client, techcorp, a, "accept")[0] == 200
    InternshipOpportunity.query.filter_by(title=SWE).one().slots = 1     # partner reduced slots
    db.session.commit()
    status, body = decide(client, techcorp, b, "accept")
    assert status == 409 and body["error"] == "All slots are filled"
    assert PlacementRecord.query.count() == 1
    assert db.session.get(Application, b).status == "pending"            # rolled back, unchanged


# ---- Candidates view --------------------------------------------------------------------------

def test_candidates_sorted_by_match_with_counts_and_filter(client, make_student, techcorp):
    strong = make_student(1, overrides={"Object Oriented Programming": 95,
                                        "Data Structures and Algorithms": 95})
    weak = make_student(2, skills=("SQL",), interests=("Data Analytics & AI",))
    apply(client, weak, SWE)
    a = app_id(apply(client, strong, SWE)[1])
    url = f"/api/partner/opportunities/{opp_id(SWE)}/candidates"
    body = client.get(url, headers=auth_header(techcorp)).get_json()
    scores = [c["match_score"] for c in body["candidates"]]
    assert len(scores) == 2 and scores == sorted(scores, reverse=True)
    assert body["candidates"][0]["student"]["name"] == "Stu1 Dent"
    assert body["counts"]["pending"] == 2 and body["counts"]["all"] == 2
    assert body["opportunity"]["slots_filled"] == 0

    decide(client, techcorp, a, "shortlist")
    res = client.get(f"{url}?status=shortlisted", headers=auth_header(techcorp))
    assert [c["application_id"] for c in res.get_json()["candidates"]] == [a]
    assert client.get(f"{url}?status=nope", headers=auth_header(techcorp)).status_code == 400


def test_email_hidden_until_shortlisted(client, make_student, techcorp):
    a = app_id(apply(client, make_student(1), SWE)[1])
    url = f"/api/partner/opportunities/{opp_id(SWE)}/candidates"
    candidate = client.get(url, headers=auth_header(techcorp)).get_json()["candidates"][0]
    assert candidate["student"]["email"] is None
    assert candidate["student"]["admission_no"] == "70001"
    decide(client, techcorp, a, "shortlist")
    candidate = client.get(url, headers=auth_header(techcorp)).get_json()["candidates"][0]
    assert candidate["student"]["email"] == "student1@strathmore.edu"


def test_snapshot_does_not_change_after_profile_update(client, make_student, techcorp,
                                                       profile_body):
    token = make_student(1)
    apply(client, token, SWE)
    url = f"/api/partner/opportunities/{opp_id(SWE)}/candidates"
    before = client.get(url, headers=auth_header(techcorp)).get_json()["candidates"][0]
    res = client.put("/api/student/profile", headers=auth_header(token),
                     json=profile_body(50, {"Object Oriented Programming": 99},
                                       skills=["SQL"], interests=["Data Analytics & AI"]))
    assert res.status_code == 200
    after = client.get(url, headers=auth_header(techcorp)).get_json()["candidates"][0]
    for key in ("match_score", "breakdown", "units", "skills", "interests"):
        assert after[key] == before[key]


# ---- Student views ------------------------------------------------------------------------------

def test_my_applications_lists_status_and_placement(client, make_student, techcorp):
    token = make_student(1)
    a = app_id(apply(client, token, SWE)[1])
    apply(client, token, DATA)
    decide(client, techcorp, a, "accept", start_date="2027-01-10")
    body = client.get("/api/applications/mine", headers=auth_header(token)).get_json()
    by_title = {x["opportunity"]["title"]: x for x in body["applications"]}
    assert by_title[SWE]["status"] == "accepted"
    assert by_title[SWE]["placement"]["status"] == "confirmed"
    assert by_title[SWE]["placement"]["organization"] == "TechCorp Kenya"
    assert by_title[SWE]["placement"]["start_date"] == "2027-01-10"
    assert by_title[DATA]["status"] == "withdrawn" and by_title[DATA]["placement"] is None
    body = client.get("/api/applications/mine?status=accepted", headers=auth_header(token)).get_json()
    assert len(body["applications"]) == 1


def test_my_application_and_has_placement_on_other_pages(client, make_student, techcorp):
    token = make_student(1)
    a = app_id(apply(client, token, SWE)[1])
    details = client.get(f"/api/opportunities/{opp_id(SWE)}", headers=auth_header(token)).get_json()
    assert details["my_application"] == {"application_id": a, "status": "pending"}
    assert details["has_placement"] is False
    other = client.get(f"/api/opportunities/{opp_id(DATA)}", headers=auth_header(token)).get_json()
    assert other["my_application"] is None

    recs = client.get("/api/recommendations", headers=auth_header(token)).get_json()
    items = {r["title"]: r for r in recs["eligible"] + recs["not_eligible"]}
    assert items[SWE]["my_application"]["status"] == "pending"
    browse = client.get("/api/opportunities", headers=auth_header(token)).get_json()
    assert {o["title"]: o for o in browse["opportunities"]}[SWE]["my_application"] is not None

    decide(client, techcorp, a, "accept")
    recs = client.get("/api/recommendations", headers=auth_header(token)).get_json()
    assert recs["has_placement"] is True


def test_partner_list_shows_counts_and_slots_filled(client, make_student, techcorp):
    a = app_id(apply(client, make_student(1), SWE)[1])
    apply(client, make_student(2), SWE)
    decide(client, techcorp, a, "accept")
    rows = client.get("/api/partner/opportunities", headers=auth_header(techcorp)).get_json()
    swe = next(o for o in rows["opportunities"] if o["title"] == SWE)
    assert swe["applicants"] == 2
    assert swe["slots_filled"] == 1 and swe["slots"] == 3
    assert swe["application_counts"]["pending"] == 1


# ---- Seed ------------------------------------------------------------------------------------------

def test_seed_creates_demo_applications_once(app, seeded_with_students):
    from app.seed.seeder import seed_all
    rows = Application.query.all()
    assert sorted(a.status for a in rows) == ["pending", "pending", "shortlisted"]
    assert PlacementRecord.query.count() == 0
    below = [a for a in rows if a.meets_requirements_at_apply is False]
    assert len(below) == 1 and below[0].opportunity.title == SWE
    assert seed_all()["applications"] == 0
    assert Application.query.count() == 3
