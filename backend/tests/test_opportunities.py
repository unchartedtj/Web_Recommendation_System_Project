"""Tests for units, opportunity browsing, and partner opportunity management.

How these tests work (pytest basics):
- Every function whose name starts with `test_` is one test. pytest finds and runs them.
- Function parameters like `client`, `seeded` or `partner_token` are FIXTURES: pytest sees
  the name, runs the fixture function with that name (defined here or in conftest.py),
  and passes in what it returns. That's how each test gets a ready-made logged-in user etc.
- `assert <condition>` makes the test fail if the condition is False.
- Every test starts with a fresh, empty database (see `_fresh_schema` in conftest.py),
  so tests never affect each other.
"""
from datetime import date, timedelta   # used to build deadlines relative to today

import pytest

from app.extensions import db                                       # the SQLAlchemy database handle
from app.models import InternshipOpportunity, OpportunityPrecursor  # tables we check directly
from app.seed.catalog import DEMO_PASSWORD                          # password of the seeded demo partners
from tests.conftest import auth_header, login, register_and_login   # small helper functions

# The URL prefix all partner opportunity endpoints share.
PARTNER_OPPS = "/api/partner/opportunities"
# Two unit names used a lot below; kept in constants so a typo can't creep in.
NETWORKS, OS = "Computer Networks", "Operating Systems"


# =============================================================================
# Fixtures used only in this file
# =============================================================================

@pytest.fixture
def partner_token(client, seeded, partner_payload):
    """A NEW industry partner (Acme Kenya) that has posted nothing yet.
    Returns the JWT access token we send with its requests."""
    return register_and_login(client, partner_payload)


@pytest.fixture
def other_partner_token(client, seeded):
    """A DIFFERENT partner (the seeded TechCorp demo account). Used to prove one
    partner can't touch another partner's opportunities."""
    return login(client, "techcorp.demo@wbl.local", DEMO_PASSWORD)


@pytest.fixture
def netsecure_token(client, seeded):
    """The seeded NetSecure demo partner, which owns the Networking opportunity."""
    return login(client, "netsecure.demo@wbl.local", DEMO_PASSWORD)


@pytest.fixture
def student_token(client, seeded, student_payload):
    """A logged-in student. Used to check students can browse but not post."""
    return register_and_login(client, student_payload)


@pytest.fixture
def opportunity_body(seeded):
    """Returns a FUNCTION that builds a valid request body for creating an opportunity.

    Call it with no arguments for the default 2 requirements, or pass your own
    requirement dicts, e.g. opportunity_body({"unit_id": 5, "importance": "essential"}, ...).
    Tests then change one field to make it invalid on purpose.
    """
    def make(*requirements):
        # If the caller passed no requirements, use a sensible default pair:
        # Operating Systems (essential, min mark 60) + Computer Networks (desirable).
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
            # 30 days from today, so the "deadline must be in the future" rule passes.
            "application_deadline": (date.today() + timedelta(days=30)).isoformat(),
            "requirements": list(reqs),
        }
    return make


def post(client, token, body):
    """Shortcut: POST a new opportunity as the user who owns `token`."""
    return client.post(PARTNER_OPPS, json=body, headers=auth_header(token))


def _reqs(seeded, names, importance="essential"):
    """Build a requirements list from unit NAMES, e.g. _reqs(seeded, ["Operating Systems"])."""
    return [{"unit_id": seeded[n], "importance": importance} for n in names]


# =============================================================================
# Units and browsing (any logged-in user)
# =============================================================================

def test_units_lists_the_12_active_units_by_name(client, student_token):
    res = client.get("/api/units", headers=auth_header(student_token))
    units = res.get_json()["units"]
    assert res.status_code == 200
    assert len(units) == 12                                   # the whole seeded catalogue
    assert set(units[0]) == {"unit_id", "unit_name"}          # only these two fields are returned
    # The list must be alphabetical: compare it with a sorted copy of itself.
    assert [u["unit_name"] for u in units] == sorted(u["unit_name"] for u in units)


def test_units_requires_login(client, seeded):
    # No Authorization header → 401 Unauthorized.
    assert client.get("/api/units").status_code == 401


def test_browse_shows_open_opportunities_with_requirements(client, student_token):
    res = client.get("/api/opportunities", headers=auth_header(student_token))
    opps = res.get_json()["opportunities"]
    assert len(opps) == 5   # the 5 seeded demo opportunities, all open
    # Pick out the Software Development one and check its details.
    swe = next(o for o in opps if o["title"] == "Software Development Intern")
    assert swe["organization_name"] == "TechCorp Kenya (Demo)"
    # Turn its requirements into {unit name: (importance, min mark)} and compare.
    assert {r["unit_name"]: (r["importance"], r["min_mark"]) for r in swe["requirements"]} == {
        "Object Oriented Programming": ("essential", 60.0),
        "Data Structures and Algorithms": ("essential", 55.0),
        "Software Engineering": ("desirable", None)}   # None = no minimum mark


# =============================================================================
# Creating opportunities
# =============================================================================

def test_partner_creates_opportunity_with_two_requirements(client, partner_token, opportunity_body):
    res = post(client, partner_token, opportunity_body())
    assert res.status_code == 201                  # 201 Created
    opp = res.get_json()["opportunity"]
    assert opp["status"] == "open"                 # new opportunities start open
    assert len(opp["requirements"]) == 2
    # Check the database directly too: exactly 2 requirement rows were saved.
    assert OpportunityPrecursor.query.filter_by(opportunity_id=opp["opportunity_id"]).count() == 2


def test_partner_creates_opportunity_with_five_requirements(client, partner_token,
                                                           opportunity_body, seeded):
    # 5 is the maximum allowed, so this must still succeed.
    names = [OS, NETWORKS, "Software Engineering", "Database Systems", "IT Project Management"]
    # `*` unpacks the list, so each requirement becomes a separate argument to make().
    assert post(client, partner_token, opportunity_body(*_reqs(seeded, names))).status_code == 201


# @pytest.mark.parametrize runs the SAME test once per row below.
# Each row is (case name, the field we expect the error to be reported on).
# This gives 9 separate tests from one function.
@pytest.mark.parametrize("case,expected_key", [
    ("one_requirement", "requirements"),            # fewer than 2 units
    ("six_requirements", "requirements"),           # more than 5 units
    ("duplicate_unit", "requirements.1.unit_id"),   # the 2nd row (index 1) repeats a unit
    ("unknown_unit", "requirements.0.unit_id"),     # unit id that doesn't exist
    ("no_essential", "requirements"),               # every unit marked desirable
    ("bad_min_mark", "requirements.0.min_mark"),    # min mark above 100
    ("past_deadline", "application_deadline"),      # deadline yesterday
    ("zero_slots", "slots"),                        # slots must be at least 1
    ("missing_title", "title"),                     # only spaces counts as empty
])
def test_invalid_opportunity_returns_400(client, partner_token, opportunity_body, seeded,
                                         case, expected_key):
    # Start from a VALID body, then break exactly one thing depending on the case.
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

    assert res.status_code == 400                         # 400 Bad Request
    assert expected_key in res.get_json()["fields"]       # the error names the right field
    assert InternshipOpportunity.query.count() == 5       # nothing new saved: only the 5 seeded ones


def test_inactive_unit_cannot_be_required(client, partner_token, opportunity_body, seeded):
    # Deactivate Operating Systems directly in the database...
    from app.models import AcademicUnit
    db.session.get(AcademicUnit, seeded[OS]).is_active = False
    db.session.commit()

    # ...then try to post an opportunity that requires it (the default body does).
    res = post(client, partner_token, opportunity_body())
    assert res.status_code == 400
    assert "requirements.0.unit_id" in res.get_json()["fields"]


def test_student_cannot_post_opportunity(client, student_token, opportunity_body):
    # Only industry partners may post → 403 Forbidden for a student.
    assert post(client, student_token, opportunity_body()).status_code == 403


# =============================================================================
# Ownership: partners only see and manage THEIR OWN opportunities
# =============================================================================

def test_partner_only_lists_own_opportunities(client, partner_token, opportunity_body):
    post(client, partner_token, opportunity_body())
    res = client.get(PARTNER_OPPS, headers=auth_header(partner_token))
    # The 5 seeded opportunities belong to the demo partners, so Acme only sees its one.
    assert [o["title"] for o in res.get_json()["opportunities"]] == ["Systems Support Intern"]


def test_partner_cannot_edit_or_close_another_partners_opportunity(
        client, partner_token, other_partner_token, opportunity_body):
    # Acme posts an opportunity...
    opp_id = post(client, partner_token, opportunity_body()).get_json()["opportunity"]["opportunity_id"]
    # ...and TechCorp (a different partner) tries to view, edit and close it.
    headers = auth_header(other_partner_token)

    assert client.put(f"{PARTNER_OPPS}/{opp_id}", json=opportunity_body(),
                      headers=headers).status_code == 403
    assert client.patch(f"{PARTNER_OPPS}/{opp_id}/close", headers=headers).status_code == 403
    assert client.get(f"{PARTNER_OPPS}/{opp_id}", headers=headers).status_code == 403
    # And the opportunity really wasn't changed.
    assert db.session.get(InternshipOpportunity, opp_id).status == "open"


def test_missing_opportunity_returns_404(client, partner_token):
    # An id that doesn't exist → 404 Not Found (not 403).
    res = client.patch(f"{PARTNER_OPPS}/999999/close", headers=auth_header(partner_token))
    assert res.status_code == 404


# =============================================================================
# Editing and closing
# =============================================================================

def test_edit_replaces_requirements(client, partner_token, opportunity_body, seeded):
    opp_id = post(client, partner_token, opportunity_body()).get_json()["opportunity"]["opportunity_id"]
    # A new body with 3 DIFFERENT requirements and a new title.
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
    # The old requirements were REPLACED (not added to): exactly these 3 remain.
    assert {r["unit_name"]: r["importance"] for r in opp["requirements"]} == {
        NETWORKS: "essential", OS: "desirable", "IT Project Management": "desirable"}


def test_closed_opportunity_hidden_from_browse(client, partner_token, student_token,
                                               opportunity_body):
    opp_id = post(client, partner_token, opportunity_body()).get_json()["opportunity"]["opportunity_id"]
    res = client.patch(f"{PARTNER_OPPS}/{opp_id}/close", headers=auth_header(partner_token))
    assert res.get_json()["opportunity"]["status"] == "closed"

    # Students browsing must no longer see it...
    browse = client.get("/api/opportunities", headers=auth_header(student_token)).get_json()
    assert opp_id not in [o["opportunity_id"] for o in browse["opportunities"]]
    # ...and opening it directly gives 404.
    assert client.get(f"/api/opportunities/{opp_id}",
                      headers=auth_header(student_token)).status_code == 404


# =============================================================================
# The recommendation model is refitted after every change
# =============================================================================

def test_create_and_close_refit_the_model(client, engine, seeded, netsecure_token,
                                          partner_token, opportunity_body):
    """With the seed, all 12 units are used, so first free up Computer Networks and
    Operating Systems by closing the only opportunity that needs them."""
    # The model's "vocabulary" = the set of units required by at least one OPEN opportunity.
    net_units = {seeded[NETWORKS], seeded[OS]}
    # `a <= b` on sets means "a is a subset of b": both units are in the vocabulary.
    assert net_units <= set(engine.model["vocabulary"])

    # Close the seeded Networking opportunity → nothing open needs those 2 units anymore.
    net_opp = InternshipOpportunity.query.filter_by(title="Networking & IT Support Intern").one()
    client.patch(f"{PARTNER_OPPS}/{net_opp.opportunity_id}/close",
                 headers=auth_header(netsecure_token))
    # `a & b` = set intersection; empty means neither unit is in the vocabulary now.
    assert not net_units & set(engine.model["vocabulary"])      # closing refits: units gone
    assert len(engine.model["vocabulary"]) == 10

    # Post a new opportunity that needs them again (the default body does).
    opp_id = post(client, partner_token, opportunity_body()).get_json()["opportunity"]["opportunity_id"]
    assert net_units <= set(engine.model["vocabulary"])         # creating refits: units back
    assert opp_id in engine.model["opportunity_ids"]

    # Close it → they disappear again.
    client.patch(f"{PARTNER_OPPS}/{opp_id}/close", headers=auth_header(partner_token))
    assert not net_units & set(engine.model["vocabulary"])
    assert opp_id not in engine.model["opportunity_ids"]
