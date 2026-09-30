"""Unit tests for the pure recommendation maths (no database needed)."""
import math

import numpy as np
import pytest

from app.seed import catalog
from services.recommendation_engine import (IncompleteGradesError, build_model,
                                            build_student_vector, rank, recommend, score)

E, D = "essential", "desirable"


def req(unit_id, importance=E, min_mark=None):
    return {"unit_id": unit_id, "importance": importance, "min_mark": min_mark}


# The seed catalogue as plain data. Unit ids are 1..12 in catalogue order.
UNIT_ID = {name: i for i, name in enumerate(catalog.UNITS, start=1)}
OPP_ID = {o["key"]: i for i, o in enumerate(catalog.OPPORTUNITIES, start=1)}

# Short aliases to keep the tests readable.
OOP = UNIT_ID["Object Oriented Programming"]
DSA = UNIT_ID["Data Structures and Algorithms"]
SE = UNIT_ID["Software Engineering"]
DBS = UNIT_ID["Database Systems"]
STATS = UNIT_ID["Probability and Statistics I"]
NETW = UNIT_ID["Computer Networks"]
OS = UNIT_ID["Operating Systems"]


def catalog_opportunities():
    return [{
        "id": OPP_ID[o["key"]],
        "title": o["title"],
        "requirements": [req(UNIT_ID[name], imp, mm) for name, imp, mm in o["requirements"]],
    } for o in catalog.OPPORTUNITIES]


def marks_for(default=55, overrides=None):
    """Marks for all 12 catalogue units, e.g. marks_for(55, {OOP: 90})."""
    marks = {uid: default for uid in UNIT_ID.values()}
    marks.update(overrides or {})
    return marks


@pytest.fixture(scope="module")
def catalog_model():
    return build_model(catalog_opportunities())


# ---- TC05: student vector weighting -----------------------------------------------------

def test_tc05_student_vector_is_mark_over_100_times_idf():
    """Hand-computed example. 3 opportunities, 3 units:
        opp1: u1 (essential), u2 (desirable)
        opp2: u2
        opp3: u2, u3
    df(u1)=1, df(u2)=3, df(u3)=1, n=3.
    smooth idf = ln((1+n)/(1+df)) + 1:
        idf(u1) = ln(4/2) + 1 = 1.693147...
        idf(u2) = ln(4/4) + 1 = 1.0
        idf(u3) = ln(4/2) + 1 = 1.693147...
    Marks u1=80, u2=50, u3=100:
        vector = [0.80 * 1.693147, 0.50 * 1.0, 1.00 * 1.693147]
               = [1.354518, 0.5, 1.693147]
    """
    model = build_model([
        {"id": 1, "requirements": [req(1, E), req(2, D)]},
        {"id": 2, "requirements": [req(2, E)]},
        {"id": 3, "requirements": [req(2, E), req(3, E)]},
    ])
    idf_rare = math.log(4 / 2) + 1

    assert model["vocabulary"] == [1, 2, 3]
    assert model["idf"] == pytest.approx([idf_rare, 1.0, idf_rare])
    # Opportunity vector = importance weight (essential 2, desirable 1) x idf
    assert model["opp_vectors"][0] == pytest.approx([2 * idf_rare, 1.0, 0.0])

    vec = build_student_vector({1: 80, 2: 50, 3: 100}, model)
    assert vec == pytest.approx([1.354518, 0.5, 1.693147], abs=1e-6)


# ---- TC06: score range and essential vs desirable ----------------------------------

def test_tc06_scores_are_between_0_and_1(catalog_model):
    rng = np.random.default_rng(7)
    for _ in range(50):
        marks = {uid: float(rng.uniform(0, 100)) for uid in UNIT_ID.values()}
        s = score(build_student_vector(marks, catalog_model), catalog_model)
        assert len(s) == 5
        assert np.all(s >= 0) and np.all(s <= 1)


def test_tc06_essential_unit_influences_score_more_than_desirable():
    # One opportunity: unit 1 essential, unit 2 desirable.
    model = build_model([{"id": 1, "requirements": [req(1, E), req(2, D)]}])
    strong_in_essential = score(build_student_vector({1: 90, 2: 40}, model), model)[0]
    strong_in_desirable = score(build_student_vector({1: 40, 2: 90}, model), model)[0]
    assert strong_in_essential > strong_in_desirable


def test_tc06_strong_student_scores_matching_opportunity_higher():
    model = build_model([{"id": 1, "requirements": [req(1), req(2)]},
                         {"id": 2, "requirements": [req(3), req(4)]}])
    s = score(build_student_vector({1: 90, 2: 88, 3: 45, 4: 50}, model), model)
    assert s[0] > s[1]


# ---- TC07: top recommendation ------------------------------------------------------

def test_tc07_strongest_in_oop_and_dsa_gets_software_development_first(catalog_model):
    results = recommend(marks_for(55, {OOP: 92, DSA: 90}), catalog_model)
    assert results[0]["opportunity_id"] == OPP_ID["SWE"]
    assert results[0]["title"] == "Software Development Intern"


# ---- TC08: complete ranking, eligible first ----------------------------------------

def test_tc08_all_open_opportunities_ranked_1_to_n_eligible_first(catalog_model):
    # Stats 50 < 60 fails Data Analytics & AI; Networks 45 < 55 fails Networking.
    results = recommend(marks_for(65, {STATS: 50, NETW: 45, OOP: 80, DSA: 78}), catalog_model)

    assert len(results) == 5
    assert [r["rank"] for r in results] == [1, 2, 3, 4, 5]
    eligibility = [r["meets_requirements"] for r in results]
    assert eligibility == sorted(eligibility, reverse=True)  # all True before all False
    assert eligibility.count(False) == 2
    # Within each group, scores descend.
    for group in (True, False):
        scores = [r["match_score"] for r in results if r["meets_requirements"] is group]
        assert scores == sorted(scores, reverse=True)


# ---- Minimum marks ----------------------------------------------------------------------

def test_below_essential_minimum_is_ineligible_and_listed(catalog_model):
    results = {r["opportunity_id"]: r for r in
               recommend(marks_for(80, {STATS: 55}), catalog_model)}
    data = results[OPP_ID["DATA"]]
    assert data["meets_requirements"] is False
    assert data["unmet_requirements"] == [{
        "unit_id": STATS, "unit": str(STATS),
        "importance": "essential", "required": 60.0, "your_mark": 55.0}]


def test_below_desirable_minimum_is_listed_but_still_eligible():
    model = build_model([{"id": 1, "requirements": [req(1, E, 60), req(2, D, 70)]}])
    result = recommend({1: 75, 2: 65}, model)[0]
    assert result["meets_requirements"] is True
    assert [(u["unit_id"], u["importance"]) for u in result["unmet_requirements"]] == [(2, "desirable")]


# ---- TC04 at the pure level ---------------------------------------------------------------

def test_tc04_missing_unit_raises(catalog_model):
    marks = marks_for(70)
    del marks[OOP]  # 11 of 12 units
    with pytest.raises(IncompleteGradesError) as exc:
        recommend(marks, catalog_model)
    assert exc.value.missing == [OOP]


def test_tc04_out_of_range_mark_raises(catalog_model):
    with pytest.raises(IncompleteGradesError) as exc:
        recommend(marks_for(70, {SE: 120}), catalog_model)
    assert exc.value.invalid == [SE]


# ---- IDF behaviour -------------------------------------------------------------------------

def test_shared_database_systems_has_lower_idf_than_computer_networks(catalog_model):
    idf = dict(zip(catalog_model["vocabulary"], catalog_model["idf"]))
    # n = 5 opportunities. Database Systems: df = 3. Computer Networks: df = 1.
    assert idf[DBS] == pytest.approx(math.log(6 / 4) + 1)
    assert idf[NETW] == pytest.approx(math.log(6 / 2) + 1)
    assert idf[DBS] < idf[SE] < idf[NETW]  # Software Engineering sits between (df = 2)


def test_all_twelve_units_are_in_the_vocabulary(catalog_model):
    assert catalog_model["vocabulary"] == sorted(UNIT_ID.values())


# ---- Tie-breaker -----------------------------------------------------------------------------

def test_tie_breaker_orders_equal_scores_by_average_mark():
    results = [
        {"opportunity_id": 1, "match_score": 0.61234, "avg_requirement_mark": 60.0,
         "meets_requirements": True},
        {"opportunity_id": 2, "match_score": 0.61234, "avg_requirement_mark": 75.0,
         "meets_requirements": True},
    ]
    ranked = rank(results)
    assert [r["opportunity_id"] for r in ranked] == [2, 1]
    assert [r["rank"] for r in ranked] == [1, 2]


def test_tie_breaker_end_to_end_with_equal_cosine_scores():
    """Two opportunities with EXACTLY equal cosine scores but different average marks.

    All units are unique, so they share one idf value c. Student marks:
    u1=80, u2..u5=40.
      opp 1 needs u2..u5 → cos = (2c * 0.4c * 4) / (|s| * 4c)   = 0.8c / |s|
      opp 2 needs u1     → cos = (2c * 0.8c)     / (|s| * 2c)   = 0.8c / |s|
    Equal scores, so the average mark decides: opp 2 (80) beats opp 1 (40),
    even though opp 1 has the lower id.
    """
    model = build_model([
        {"id": 1, "requirements": [req(2), req(3), req(4), req(5)]},
        {"id": 2, "requirements": [req(1)]},
    ])
    results = recommend({1: 80, 2: 40, 3: 40, 4: 40, 5: 40}, model)
    assert results[0]["match_score"] == results[1]["match_score"]
    assert [r["opportunity_id"] for r in results] == [2, 1]


def test_empty_model_returns_no_recommendations():
    model = build_model([])
    assert model["vocabulary"] == []
    assert recommend({1: 50}, model) == []
