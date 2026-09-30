"""Tests for units, opportunity browsing, and partner opportunity management."""
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import InternshipOpportunity, OpportunityPrecursor
from app.seed.catalog import DEMO_PASSWORD
from tests.conftest import auth_header, login, register_and_login

PARTNER_OPPS = "/api/partner/opportunities"
NETWORKS, OS = "Computer Networks", "Operating Systems"


@pytest.fixture
def partner_token(client, seeded, partner_payload):
    return register_and_login(client, partner_payload)


@pytest.fixture
def other_partner_token(client, seeded):
    return login(client, "techcorp.demo@wbl.local", DEMO_PASSWORD)


@pytest.fixture
def netsecure_token(client, seeded):
    return login(client, "netsecure.demo@wbl.local", DEMO_PASSWORD)


@pytest.fixture
def student_token(client, seeded, student_payload):
    return register_and_login(client, student_payload)


@pytest.fixture
def opportunity_body(seeded):
    def make(*requirements):
        reqs = requirements or (
            {"unit_id": seeded[OS], "importance": "essential", "min_mark": 60},
            {"unit_id": seeded[NETWORKS], "importance": "desirable"},
        )
        return {
            "title": "Systems Support Intern",
            "description": "Help maintain servers and end-user systems.",
            "sector": "Infrastructure",
            "location": "Nairobi",
            "duration_months": 3,
            "slots": 2,
            "application_deadline": (date.today() + timedelta(days=30)).isoformat(),
            "requirements": list(reqs),
        }
    return make


def post(client, token, body):
    return client.post(PARTNER_OPPS, json=body, headers=auth_header(token))


def _reqs(seeded, names, importance="essential"):
    return [{"unit_id": seeded[n], "importance": importance} for n in names]


# ---- Units and browsing -------------------------------------------------------------------

def test_units_lists_the_12_active_units_by_name(client, student_token):
    res = client.get("/api/units", headers=auth_header(student_token))
    units = res.get_json()["units"]
    assert res.status_code == 200
    assert len(units) == 12
    assert set(units[0]) == {"unit_id", "unit_name"}
    assert [u["unit_name"] for u in units] == sorted(u["unit_name"] for u in units)


def test_units_requires_login(client, seeded):
    assert client.get("/api/units").status_code == 401


def test_browse_shows_open_opportunities_with_requirements(client, student_token):
    res = client.get("/api/opportunities", headers=auth_header(student_token))
    opps = res.get_json()["opportunities"]
    assert len(opps) == 5
    swe = next(o for o in opps if o["title"] == "Software Development Intern")
    assert swe["organization_name"] == "TechCorp Kenya (Demo)"
    assert {r["unit_name"]: (r["importance"], r["min_mark"]) for r in swe["requirements"]} == {
        "Object Oriented Programming": ("essential", 60.0),
        "Data Structures and Algorithms": ("essential", 55.0),
        "Software Engineering": ("desirable", None)}


# ---- Create --------------------------------------------------------------------------------

def test_partner_creates_opportunity_with_two_requirements(client, partner_token, opportunity_body):
    res = post(client, partner_token, opportunity_body())
    assert res.status_code == 201
    opp = res.get_json()["opportunity"]
    assert opp["status"] == "open"
    assert len(opp["requirements"]) == 2
    assert OpportunityPrecursor.query.filter_by(opportunity_id=opp["opportunity_id"]).count() == 2


def test_partner_creates_opportunity_with_five_requirements(client, partner_token,
                                                           opportunity_body, seeded):
    names = [OS, NETWORKS, "Software Engineering", "Database Systems", "IT Project Management"]
    assert post(client, partner_token, opportunity_body(*_reqs(seeded, names))).status_code == 201


@pytest.mark.parametrize("case,expected_key", [
    ("one_requirement", "requirements"),
    ("six_requirements", "requirements"),
    ("duplicate_unit", "requirements.1.unit_id"),
    ("unknown_unit", "requirements.0.unit_id"),
    ("no_essential", "requirements"),
    ("bad_min_mark", "requirements.0.min_mark"),
    ("past_deadline", "application_deadline"),
    ("zero_slots", "slots"),
    ("missing_title", "title"),
])
def test_invalid_opportunity_returns_400(client, partner_token, opportunity_body, seeded,
                                         case, expected_key):
    body = opportunity_body()
    if case == "one_requirement":
        body["requirements"] = _reqs(seeded, [OS])
    elif case == "six_requirements":
        body["requirements"] = _reqs(seeded, [OS, NETWORKS, "Software Engineering",
                                              "Database Systems", "IT Project Management",
                                              "Artificial Intelligence"])
    elif case == "duplicate_unit":
        body["requirements"] = _reqs(seeded, [OS, OS])
    elif case == "unknown_unit":
        body["requirements"][0]["unit_id"] = 999999
    elif case == "no_essential":
        body["requirements"] = _reqs(seeded, [OS, NETWORKS], "desirable")
    elif case == "bad_min_mark":
        body["requirements"][0]["min_mark"] = 120
    elif case == "past_deadline":
        body["application_deadline"] = (date.today() - timedelta(days=1)).isoformat()
    elif case == "zero_slots":
        body["slots"] = 0
    elif case == "missing_title":
        body["title"] = "  "

    res = post(client, partner_token, body)

    assert res.status_code == 400
    assert expected_key in res.get_json()["fields"]
    assert InternshipOpportunity.query.count() == 5  # only the seeded ones


def test_inactive_unit_cannot_be_required(client, partner_token, opportunity_body, seeded):
    from app.models import AcademicUnit
    db.session.get(AcademicUnit, seeded[OS]).is_active = False
    db.session.commit()

    res = post(client, partner_token, opportunity_body())
    assert res.status_code == 400
    assert "requirements.0.unit_id" in res.get_json()["fields"]


def test_student_cannot_post_opportunity(client, student_token, opportunity_body):
    assert post(client, student_token, opportunity_body()).status_code == 403


# ---- Ownership -----------------------------------------------------------------------------

def test_partner_only_lists_own_opportunities(client, partner_token, opportunity_body):
    post(client, partner_token, opportunity_body())
    res = client.get(PARTNER_OPPS, headers=auth_header(partner_token))
    assert [o["title"] for o in res.get_json()["opportunities"]] == ["Systems Support Intern"]


def test_partner_cannot_edit_or_close_another_partners_opportunity(
        client, partner_token, other_partner_token, opportunity_body):
    opp_id = post(client, partner_token, opportunity_body()).get_json()["opportunity"]["opportunity_id"]
    headers = auth_header(other_partner_token)

    assert client.put(f"{PARTNER_OPPS}/{opp_id}", json=opportunity_body(),
                      headers=headers).status_code == 403
    assert client.patch(f"{PARTNER_OPPS}/{opp_id}/close", headers=headers).status_code == 403
    assert client.get(f"{PARTNER_OPPS}/{opp_id}", headers=headers).status_code == 403
    assert db.session.get(InternshipOpportunity, opp_id).status == "open"


def test_missing_opportunity_returns_404(client, partner_token):
    res = client.patch(f"{PARTNER_OPPS}/999999/close", headers=auth_header(partner_token))
    assert res.status_code == 404


# ---- Edit and close ------------------------------------------------------------------------

def test_edit_replaces_requirements(client, partner_token, opportunity_body, seeded):
    opp_id = post(client, partner_token, opportunity_body()).get_json()["opportunity"]["opportunity_id"]
    body = opportunity_body(
        {"unit_id": seeded[NETWORKS], "importance": "essential", "min_mark": 70},
        {"unit_id": seeded[OS], "importance": "desirable"},
        {"unit_id": seeded["IT Project Management"], "importance": "desirable"},
    )
    body["title"] = "Network Support Intern"

    res = client.put(f"{PARTNER_OPPS}/{opp_id}", json=body, headers=auth_header(partner_token))

    assert res.status_code == 200
    opp = res.get_json()["opportunity"]
    assert opp["title"] == "Network Support Intern"
    assert {r["unit_name"]: r["importance"] for r in opp["requirements"]} == {
        NETWORKS: "essential", OS: "desirable", "IT Project Management": "desirable"}


def test_closed_opportunity_hidden_from_browse(client, partner_token, student_token,
                                               opportunity_body):
    opp_id = post(client, partner_token, opportunity_body()).get_json()["opportunity"]["opportunity_id"]
    res = client.patch(f"{PARTNER_OPPS}/{opp_id}/close", headers=auth_header(partner_token))
    assert res.get_json()["opportunity"]["status"] == "closed"

    browse = client.get("/api/opportunities", headers=auth_header(student_token)).get_json()
    assert opp_id not in [o["opportunity_id"] for o in browse["opportunities"]]
    assert client.get(f"/api/opportunities/{opp_id}",
                      headers=auth_header(student_token)).status_code == 404


# ---- Model refit ---------------------------------------------------------------------------

def test_create_and_close_refit_the_model(client, engine, seeded, netsecure_token,
                                          partner_token, opportunity_body):
    """With the seed, all 12 units are used, so first free up Computer Networks and
    Operating Systems by closing the only opportunity that needs them."""
    net_units = {seeded[NETWORKS], seeded[OS]}
    assert net_units <= set(engine.model["vocabulary"])

    net_opp = InternshipOpportunity.query.filter_by(title="Networking & IT Support Intern").one()
    client.patch(f"{PARTNER_OPPS}/{net_opp.opportunity_id}/close",
                 headers=auth_header(netsecure_token))
    assert not net_units & set(engine.model["vocabulary"])      # closing refits: units gone
    assert len(engine.model["vocabulary"]) == 10

    opp_id = post(client, partner_token, opportunity_body()).get_json()["opportunity"]["opportunity_id"]
    assert net_units <= set(engine.model["vocabulary"])         # creating refits: units back
    assert opp_id in engine.model["opportunity_ids"]

    client.patch(f"{PARTNER_OPPS}/{opp_id}/close", headers=auth_header(partner_token))
    assert not net_units & set(engine.model["vocabulary"])
    assert opp_id not in engine.model["opportunity_ids"]
