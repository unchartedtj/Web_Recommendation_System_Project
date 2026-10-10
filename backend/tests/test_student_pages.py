"""Tests for the APIs behind the student pages: browse (filters + sorting), internship details
(the "my_match" block), the eligible / not-eligible split, and the 3 demo students.

These use `seeded_with_students`, i.e. everything `flask seed-data` creates, including:
    student.software@wbl.local  – complete profile pointing at Software Development (TC07)
    student.data@wbl.local      – complete profile; below the Software Development OOP minimum
    student.new@wbl.local       – no profile yet
"""
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import InternshipOpportunity, Sector, Skill
from app.seed.catalog import DEMO_PASSWORD
from tests.conftest import auth_header, login

BROWSE = "/api/opportunities"


@pytest.fixture
def tokens(client, seeded_with_students):
    """Logged-in tokens for the demo students and a demo partner."""
    return {name: login(client, f"student.{name}@wbl.local", DEMO_PASSWORD)
            for name in ("software", "data", "new")} | {
        "partner": login(client, "techcorp.demo@wbl.local", DEMO_PASSWORD)}


def browse(client, token, **params):
    res = client.get(BROWSE, query_string=params, headers=auth_header(token))
    return res.status_code, res.get_json()


def titles(body):
    return [o["title"] for o in body["opportunities"]]


def opp(title):
    return InternshipOpportunity.query.filter_by(title=title).one()


# ---- Demo students ---------------------------------------------------------------------------

def test_demo_software_student_gets_software_development_first(client, tokens):
    """TC07 with the seeded demo student."""
    body = client.get("/api/recommendations", headers=auth_header(tokens["software"])).get_json()
    assert body["profile_complete"] is True
    assert body["eligible"][0]["title"] == "Software Development Intern"


def test_demo_data_student_has_both_sections(client, tokens):
    body = client.get("/api/recommendations", headers=auth_header(tokens["data"])).get_json()
    assert body["eligible"] and body["not_eligible"]
    assert "Software Development Intern" in [r["title"] for r in body["not_eligible"]]
    assert body["eligible"][0]["title"] == "Data Analytics & AI Intern"


def test_demo_new_student_has_no_profile(client, tokens):
    profile = client.get("/api/student/profile", headers=auth_header(tokens["new"])).get_json()
    assert profile["profile"]["is_complete"] is False
    body = client.get("/api/recommendations", headers=auth_header(tokens["new"])).get_json()
    assert body["profile_complete"] is False
    assert body["eligible"] == body["not_eligible"] == []


# ---- Eligible / not-eligible split ------------------------------------------------------------

def test_each_section_is_sorted_by_match_score_descending(client, tokens):
    body = client.get("/api/recommendations", headers=auth_header(tokens["data"])).get_json()
    for section in ("eligible", "not_eligible"):
        scores = [r["match_score"] for r in body[section]]
        assert scores == sorted(scores, reverse=True)
    assert all(r["meets_requirements"] for r in body["eligible"])
    assert not any(r["meets_requirements"] for r in body["not_eligible"])


def test_recommendation_cards_have_why_this_match_data(client, tokens):
    body = client.get("/api/recommendations", headers=auth_header(tokens["data"])).get_json()
    swe = next(r for r in body["not_eligible"] if r["title"] == "Software Development Intern")
    oop = next(u for u in swe["units"] if u["unit"] == "Object Oriented Programming")
    assert (oop["min_mark"], oop["my_mark"], oop["met"]) == (60.0, 52.0, False)
    assert {s["skill"]: s["i_have"] for s in swe["skills"]}["Python"] is True
    for key in ("location", "application_deadline", "sector_id", "duration_months", "slots"):
        assert key in swe


# ---- Browse: filters --------------------------------------------------------------------------

def test_browse_search_matches_title_or_company(client, tokens):
    _, body = browse(client, tokens["new"], search="data")
    assert titles(body) == ["Data Analytics & AI Intern"]
    _, body = browse(client, tokens["new"], search="NETSECURE")       # company, any case
    assert sorted(titles(body)) == ["IT Business / Systems Analyst Intern",
                                    "Networking & IT Support Intern"]


def test_browse_sector_and_skill_filters(client, tokens):
    data_sector = Sector.query.filter_by(name="Data Analytics & AI").one().sector_id
    _, body = browse(client, tokens["new"], sector_id=data_sector)
    assert titles(body) == ["Data Analytics & AI Intern"]

    sql = Skill.query.filter_by(name="SQL").one().skill_id             # required by 3
    _, body = browse(client, tokens["new"], skill_id=sql)
    assert len(body["opportunities"]) == 3


@pytest.mark.parametrize("params", [{"sector_id": "abc"}, {"skill_id": "x"}, {"sort": "random"}])
def test_browse_rejects_bad_filters(client, tokens, params):
    status, _ = browse(client, tokens["new"], **params)
    assert status == 400


def test_browse_hides_closed_and_past_deadline(client, tokens):
    opp("Data Analytics & AI Intern").application_deadline = date.today() - timedelta(days=1)
    opp("Networking & IT Support Intern").status = "closed"
    db.session.commit()
    _, body = browse(client, tokens["new"])
    assert len(body["opportunities"]) == 3
    assert "Data Analytics & AI Intern" not in titles(body)
    assert "Networking & IT Support Intern" not in titles(body)


def test_past_deadline_internships_leave_the_recommendations(client, tokens):
    """Same rule as Browse: once the deadline has passed, it's no longer recommended."""
    opp("Software Development Intern").application_deadline = date.today() - timedelta(days=1)
    db.session.commit()
    body = client.get("/api/recommendations", headers=auth_header(tokens["software"])).get_json()
    shown = [r["title"] for r in body["eligible"] + body["not_eligible"]]
    assert "Software Development Intern" not in shown
    assert len(shown) == 4


# ---- Browse: sorting --------------------------------------------------------------------------

def test_browse_sort_by_deadline_soonest_first(client, tokens):
    for days, title in enumerate(["IT Business / Systems Analyst Intern", "Data Analytics & AI Intern",
                                  "Software Development Intern", "Networking & IT Support Intern",
                                  "Web & Mobile App Development Intern"], start=1):
        opp(title).application_deadline = date.today() + timedelta(days=days)
    db.session.commit()
    _, body = browse(client, tokens["new"], sort="deadline")
    deadlines = [o["application_deadline"] for o in body["opportunities"]]
    assert deadlines == sorted(deadlines)
    assert titles(body)[0] == "IT Business / Systems Analyst Intern"


def test_browse_best_match_for_a_complete_profile(client, tokens):
    _, body = browse(client, tokens["software"], sort="best_match")
    assert body["sort"] == "best_match" and body["profile_complete"] is True
    assert titles(body)[0] == "Software Development Intern"
    assert all("match_percent" in o and "meets_requirements" in o for o in body["opportunities"])


def test_best_match_falls_back_to_newest_without_a_profile(client, tokens):
    _, body = browse(client, tokens["new"], sort="best_match")
    assert body["sort"] == "newest" and body["profile_complete"] is False
    assert not any("match_percent" in o for o in body["opportunities"])


def test_partners_browse_without_match_data(client, tokens):
    _, body = browse(client, tokens["partner"])
    assert body["profile_complete"] is False
    assert not any("match_percent" in o for o in body["opportunities"])


# ---- Details: my_match ------------------------------------------------------------------------

def test_details_include_my_match_for_a_complete_profile(client, tokens):
    swe = opp("Software Development Intern").opportunity_id
    body = client.get(f"{BROWSE}/{swe}", headers=auth_header(tokens["software"])).get_json()

    m = body["my_match"]
    assert body["profile_complete"] is True
    assert set(m["breakdown"]) == {"grade_score", "skill_score", "interest_score"}
    assert m["meets_requirements"] is True and m["interest_match"] is True
    units = {u["unit"]: u for u in m["units"]}
    assert units["Object Oriented Programming"]["met"] is True
    assert units["Object Oriented Programming"]["my_mark"] == 90.0
    skills = {s["skill"]: s["i_have"] for s in m["skills"]}
    assert skills == {"Java": True, "Git & GitHub": True, "Python": True, "SQL": False}
    assert m["missing_desirable_skills"] == ["SQL"]


def test_details_show_unmet_minimum(client, tokens):
    swe = opp("Software Development Intern").opportunity_id
    m = client.get(f"{BROWSE}/{swe}", headers=auth_header(tokens["data"])).get_json()["my_match"]
    assert m["meets_requirements"] is False
    oop = next(u for u in m["units"] if u["unit"] == "Object Oriented Programming")
    assert oop["met"] is False


def test_details_without_profile_have_no_my_match(client, tokens):
    swe = opp("Software Development Intern").opportunity_id
    body = client.get(f"{BROWSE}/{swe}", headers=auth_header(tokens["new"])).get_json()
    assert body["profile_complete"] is False
    assert "my_match" not in body
    assert body["opportunity"]["description"]


def test_details_404_for_closed_or_unknown(client, tokens):
    net = opp("Networking & IT Support Intern")
    net.status = "closed"
    db.session.commit()
    assert client.get(f"{BROWSE}/{net.opportunity_id}",
                      headers=auth_header(tokens["software"])).status_code == 404
    assert client.get(f"{BROWSE}/999999", headers=auth_header(tokens["software"])).status_code == 404
