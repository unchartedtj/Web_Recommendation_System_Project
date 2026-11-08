"""Transcript upload and marks verification: a student can only apply after the WBL office
(system admin) accepts their typed marks against the uploaded PDF."""
import io
import os

import pytest

from app.extensions import db
from app.models import ActivityLog, InternshipOpportunity, Transcript, User
from app.seed.catalog import DEFAULT_ADMIN, DEMO_PASSWORD
from tests.conftest import auth_header, login, register_and_login

PDF = b"%PDF-1.4\n% test transcript\n%%EOF\n"
SWE = "Software Development Intern"


def opp_id(title=SWE):
    return InternshipOpportunity.query.filter_by(title=title).one().opportunity_id


@pytest.fixture
def admin(client, seeded):
    return login(client, DEFAULT_ADMIN["name"], DEFAULT_ADMIN["password"])


@pytest.fixture
def student(client, seeded, profile_body):
    """A student with a complete profile but NO transcript yet."""
    token = register_and_login(client, {
        "role": "student", "email": "stu@strathmore.edu", "password": "Passw0rd123",
        "confirm_password": "Passw0rd123", "admission_no": "70001", "first_name": "Stu",
        "last_name": "Dent", "course": "BBIT", "year_of_study": 3})
    res = client.put("/api/student/profile", headers=auth_header(token),
                     json=profile_body(65, skills=("Java", "Git & GitHub"),
                                       interests=("Software Development",)))
    assert res.status_code == 200
    return token


def upload(client, token, data=PDF, name="transcript.pdf"):
    return client.post("/api/student/transcript", headers=auth_header(token),
                       data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data")


def apply(client, token):
    return client.post("/api/applications", headers=auth_header(token),
                       json={"opportunity_id": opp_id()})


def the_transcript():
    return Transcript.query.one()


def review(client, admin, action, **body):
    return client.patch(f"/api/admin/transcripts/{the_transcript().transcript_id}",
                        headers=auth_header(admin), json={"action": action, **body})


# ---- Uploading ----------------------------------------------------------------------------------

def test_upload_makes_it_pending_and_stores_the_file(app, client, student):
    res = upload(client, student)
    assert res.status_code == 201
    t = res.get_json()["transcript"]
    assert t["status"] == "pending" and t["original_name"] == "transcript.pdf"
    stored = the_transcript()
    assert os.path.exists(os.path.join(app.config["TRANSCRIPT_FOLDER"], stored.stored_name))
    assert stored.stored_name != "transcript.pdf"                 # random name on disk
    profile = client.get("/api/student/profile", headers=auth_header(student)).get_json()["profile"]
    assert profile["transcript"]["status"] == "pending"
    own = client.get("/api/student/transcript/file", headers=auth_header(student))
    assert own.status_code == 200 and own.data == PDF


@pytest.mark.parametrize("data,name", [
    (b"just some text", "transcript.pdf"),     # not really a PDF (checked by content)
    (b"", "transcript.pdf"),                    # empty
])
def test_only_real_pdfs_are_accepted(client, student, data, name):
    res = upload(client, student, data, name)
    assert res.status_code == 400 and "file" in res.get_json()["fields"]
    assert Transcript.query.count() == 0


def test_missing_file_and_size_limit(app, client, student):
    res = client.post("/api/student/transcript", headers=auth_header(student),
                      data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    old = app.config["TRANSCRIPT_MAX_BYTES"]
    app.config["TRANSCRIPT_MAX_BYTES"] = 20
    try:
        assert upload(client, student, PDF + b"x" * 50).status_code == 400
    finally:
        app.config["TRANSCRIPT_MAX_BYTES"] = old


def test_uploading_again_replaces_the_file_and_resets_to_pending(app, client, student, admin):
    upload(client, student)
    first = the_transcript().stored_name
    review(client, admin, "accept")
    upload(client, student, PDF + b"% v2\n", "new.pdf")
    t = the_transcript()
    assert Transcript.query.count() == 1
    assert (t.status, t.original_name) == ("pending", "new.pdf")
    assert not os.path.exists(os.path.join(app.config["TRANSCRIPT_FOLDER"], first))   # old one removed


# ---- The application gate -----------------------------------------------------------------------

def test_cannot_apply_until_marks_are_accepted(client, student, admin):
    res = apply(client, student)
    assert res.status_code == 409 and res.get_json()["fields"]["transcript"] == "missing"
    upload(client, student)
    res = apply(client, student)
    assert res.status_code == 409 and res.get_json()["fields"]["transcript"] == "pending"
    details = client.get(f"/api/opportunities/{opp_id()}", headers=auth_header(student)).get_json()
    assert (details["marks_verified"], details["transcript_status"]) == (False, "pending")

    assert review(client, admin, "accept").status_code == 200
    assert apply(client, student).status_code == 201
    details = client.get(f"/api/opportunities/{opp_id()}", headers=auth_header(student)).get_json()
    assert details["marks_verified"] is True


def test_rejection_needs_a_reason_and_blocks_applying(client, student, admin):
    upload(client, student)
    assert review(client, admin, "reject").status_code == 400
    res = review(client, admin, "reject", reason="OOP mark is 58 on the transcript, not 65")
    assert res.status_code == 200
    mine = client.get("/api/student/transcript", headers=auth_header(student)).get_json()["transcript"]
    assert (mine["status"], mine["review_reason"]) == ("rejected", "OOP mark is 58 on the transcript, not 65")
    assert apply(client, student).get_json()["fields"]["transcript"] == "rejected"


def test_changing_marks_after_acceptance_resets_to_pending(client, student, admin, profile_body):
    upload(client, student)
    review(client, admin, "accept")
    same = profile_body(65, skills=("Java", "Git & GitHub"), interests=("Software Development",))
    client.put("/api/student/profile", headers=auth_header(student), json=same)
    assert the_transcript().status == "accepted"                     # same marks: still accepted
    changed = profile_body(65, {"Object Oriented Programming": 99}, skills=("Java",),
                           interests=("Software Development",))
    client.put("/api/student/profile", headers=auth_header(student), json=changed)
    db.session.expire_all()
    assert the_transcript().status == "pending"
    assert apply(client, student).status_code == 409


# ---- Admin review ------------------------------------------------------------------------------

def test_admin_list_detail_and_file(client, student, admin):
    upload(client, student)
    page = client.get("/api/admin/transcripts?status=pending", headers=auth_header(admin)).get_json()
    assert page["total"] == 1 and page["pending"] == 1
    assert page["items"][0]["student"]["admission_no"] == "70001"
    tid = page["items"][0]["transcript_id"]
    detail = client.get(f"/api/admin/transcripts/{tid}", headers=auth_header(admin)).get_json()["transcript"]
    assert len(detail["marks"]) == 12
    pdf = client.get(f"/api/admin/transcripts/{tid}/file", headers=auth_header(admin))
    assert pdf.status_code == 200 and pdf.mimetype == "application/pdf" and pdf.data == PDF


def test_partners_and_students_cannot_review(client, student, admin):
    upload(client, student)
    tid = the_transcript().transcript_id
    partner = login(client, "info@techcorp.co.ke", DEMO_PASSWORD)
    for token in (partner, student):
        assert client.get("/api/admin/transcripts", headers=auth_header(token)).status_code == 403
        assert client.get(f"/api/admin/transcripts/{tid}/file", headers=auth_header(token)).status_code == 403
        assert client.patch(f"/api/admin/transcripts/{tid}", headers=auth_header(token),
                            json={"action": "accept"}).status_code == 403
    assert client.get("/api/student/transcript", headers=auth_header(partner)).status_code == 403


def test_review_is_logged(client, student, admin):
    upload(client, student)
    review(client, admin, "accept")
    actions = {a.action for a in ActivityLog.query.all()}
    assert {"transcript.uploaded", "transcript.accepted"} <= actions


def test_partner_flow_is_unchanged(client, seeded):
    """Partners never need a transcript."""
    token = login(client, "info@techcorp.co.ke", DEMO_PASSWORD)
    assert client.get("/api/partner/opportunities", headers=auth_header(token)).status_code == 200


# ---- Seed --------------------------------------------------------------------------------------

def test_demo_students_are_seeded_as_verified(app, seeded_with_students):
    by_email = {u.email: u.student for u in User.query.filter(User.email.like("%@strathmore.edu"))}
    assert by_email["samuel.kamau@strathmore.edu"].transcript.status == "accepted"
    assert by_email["diana.wanjiru@strathmore.edu"].transcript.status == "accepted"
    assert by_email["kevin.mwangi@strathmore.edu"].transcript is None      # shows the upload flow
    t = by_email["samuel.kamau@strathmore.edu"].transcript
    path = os.path.join(app.config["TRANSCRIPT_FOLDER"], t.stored_name)
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"
