"""Admin Reports: placement rate by course, match % vs outcome, internship pay."""
import pytest

from app.extensions import db
from app.models import (Application, ApplicationStatus, InternshipOpportunity, PlacementRecord,
                        PlacementStatus, Student)
from app.seed.catalog import DEFAULT_ADMIN, DEMO_PASSWORD
from tests.conftest import auth_header, login

REPORTS = "/api/admin/reports"


@pytest.fixture
def seeded(seeded_with_students):
    """These tests need some students, so use the seed WITH the 3 demo students."""
    return seeded_with_students


@pytest.fixture
def admin(client, seeded):
    return login(client, DEFAULT_ADMIN["name"], DEFAULT_ADMIN["password"])


@pytest.fixture
def student(client, seeded):
    return login(client, "samuel.kamau@strathmore.edu", DEMO_PASSWORD)


def get_reports(client, admin):
    res = client.get(REPORTS, headers=auth_header(admin))
    assert res.status_code == 200
    return res.get_json()


def clear_applications():
    """The demo seed already has a few applications; start these tests from none."""
    Application.query.delete()
    db.session.commit()


def test_only_admins_can_see_reports(client, student, admin):
    assert client.get(REPORTS, headers=auth_header(student)).status_code == 403
    assert client.get(REPORTS).status_code == 401


def test_report_sections_are_present_with_every_status_and_pay_type(client, admin):
    body = get_reports(client, admin)
    assert [r["status"] for r in body["match_outcomes"]] == list(ApplicationStatus.ALL)
    assert [r["type"] for r in body["pay"]] == ["unpaid", "paid", "stipend"]
    assert set(body["placement_rate"]["total"]) == {"students", "complete_profiles", "placed",
                                                    "rate_percent"}


def test_placement_rate_counts_placed_students_per_course(client, admin, seeded):
    clear_applications()
    students = Student.query.all()
    opp = InternshipOpportunity.query.first()
    # One student placed (ongoing), one with a terminated placement (does NOT count as placed).
    for s, status in zip(students[:2], (PlacementStatus.ONGOING, PlacementStatus.TERMINATED)):
        app_row = Application(student_id=s.student_id, opportunity_id=opp.opportunity_id,
                              status=ApplicationStatus.ACCEPTED, match_score_at_apply=0.7)
        db.session.add(app_row)
        db.session.flush()
        db.session.add(PlacementRecord(student_id=s.student_id, opportunity_id=opp.opportunity_id,
                                       application_id=app_row.application_id, status=status))
    db.session.commit()

    rate = get_reports(client, admin)["placement_rate"]
    assert rate["total"]["students"] == len(students)
    assert rate["total"]["placed"] == 1
    assert sum(r["students"] for r in rate["rows"]) == len(students)
    placed_row = next(r for r in rate["rows"] if r["placed"])
    assert set(placed_row) == {"course", "students", "complete_profiles", "placed", "rate_percent"}
    assert placed_row["rate_percent"] == round(100 / placed_row["students"], 1)
    assert len({r["course"] for r in rate["rows"]}) == len(rate["rows"])   # one row per course


def test_match_outcomes_average_the_match_at_apply(client, admin, seeded):
    clear_applications()
    s = Student.query.first()
    opps = InternshipOpportunity.query.limit(3).all()
    for opp, status, score in zip(opps, (ApplicationStatus.ACCEPTED, ApplicationStatus.ACCEPTED,
                                         ApplicationStatus.REJECTED), (0.8, 0.6, 0.4)):
        db.session.add(Application(student_id=s.student_id, opportunity_id=opp.opportunity_id,
                                   status=status, match_score_at_apply=score))
    db.session.commit()

    rows = {r["status"]: r for r in get_reports(client, admin)["match_outcomes"]}
    assert rows["accepted"] == {"status": "accepted", "applications": 2, "avg_match_percent": 70.0,
                                "min_match_percent": 60.0, "max_match_percent": 80.0}
    assert rows["rejected"]["avg_match_percent"] == 40.0
    assert rows["pending"] == {"status": "pending", "applications": 0, "avg_match_percent": None,
                               "min_match_percent": None, "max_match_percent": None}


def test_pay_summary_counts_types_and_amounts(client, admin, seeded):
    opps = InternshipOpportunity.query.order_by(InternshipOpportunity.opportunity_id).all()
    opps[0].compensation_type, opps[0].compensation_amount = "paid", 20000
    opps[1].compensation_type, opps[1].compensation_amount = "paid", 30000
    opps[2].compensation_type, opps[2].compensation_amount = "stipend", 10000
    opps[2].status = "closed"
    db.session.commit()

    pay = {r["type"]: r for r in get_reports(client, admin)["pay"]}
    assert pay["paid"] == {"type": "paid", "internships": 2, "open": 2, "avg_amount": 25000,
                           "min_amount": 20000, "max_amount": 30000}
    assert pay["stipend"]["internships"] == 1 and pay["stipend"]["open"] == 0
    assert pay["unpaid"]["internships"] == len(opps) - 3
    assert pay["unpaid"]["avg_amount"] is None


# ---- CSV exports ----------------------------------------------------------------------------

def read_csv(res):
    import csv
    import io
    assert res.status_code == 200 and res.mimetype == "text/csv"
    return list(csv.reader(io.StringIO(res.get_data(as_text=True))))


def test_placement_rate_csv_has_one_row_per_course_and_a_total(client, admin):
    res = client.get(f"{REPORTS}/placement-rate.csv", headers=auth_header(admin))
    assert "placement_rate_by_course.csv" in res.headers["Content-Disposition"]
    rows = read_csv(res)
    assert rows[0] == ["course", "students", "complete_profiles", "placed", "placement_rate_percent"]
    courses = get_reports(client, admin)["placement_rate"]["rows"]
    assert [r[0] for r in rows[1:-1]] == [c["course"] for c in courses]
    assert rows[-1][0] == "All students" and rows[-1][1] == str(Student.query.count())


def test_match_and_pay_csv_list_every_status_and_pay_type(client, admin):
    match = read_csv(client.get(f"{REPORTS}/match-outcomes.csv", headers=auth_header(admin)))
    assert match[0][0] == "outcome" and [r[0] for r in match[1:]] == list(ApplicationStatus.ALL)
    pay = read_csv(client.get(f"{REPORTS}/pay.csv", headers=auth_header(admin)))
    assert pay[0][0] == "pay_type" and [r[0] for r in pay[1:]] == ["unpaid", "paid", "stipend"]


@pytest.mark.parametrize("name", ["placement-rate", "match-outcomes", "pay"])
def test_report_csv_is_admin_only(client, student, name):
    assert client.get(f"{REPORTS}/{name}.csv", headers=auth_header(student)).status_code == 403
