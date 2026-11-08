"""Transcript upload (student) and marks verification (system admin).

    GET   /api/student/transcript               my transcript and its status (or null)
    POST  /api/student/transcript               upload / replace my PDF (form field "file")
    GET   /api/student/transcript/file          download my PDF
    GET   /api/admin/transcripts?status=&search= list (pending first)
    GET   /api/admin/transcripts/<id>           one transcript + the marks the student typed
    GET   /api/admin/transcripts/<id>/file      the PDF
    PATCH /api/admin/transcripts/<id>           {action: accept | reject, reason?}
"""
from flask import jsonify, request, send_file
from sqlalchemy import case, func, or_

from app.admin.common import ADMIN, choice_arg, paginate, str_arg
from app.auth.decorators import current_student, current_user, role_required
from app.errors import ApiError
from app.extensions import db
from app.models import AcademicUnit, Student, Transcript, TranscriptStatus
from app.recommendations.services import latest_marks
from app.transcripts import transcripts_bp
from app.verification import file_path, review, save_upload, serialize
from app.utils import json_body

STUDENT = "student"


def _send_pdf(t: Transcript):
    try:
        return send_file(file_path(t), mimetype="application/pdf", download_name=t.original_name)
    except FileNotFoundError:
        raise ApiError("The transcript file is missing. Ask the student to upload it again.", 404)


# ---- Student -------------------------------------------------------------------------------

@transcripts_bp.get("/student/transcript")
@role_required(STUDENT)
def my_transcript():
    return jsonify({"transcript": serialize(current_student().transcript)})


@transcripts_bp.post("/student/transcript")
@role_required(STUDENT)
def upload_transcript():
    t = save_upload(current_student(), request.files.get("file"))
    return jsonify({"message": "Transcript uploaded. The WBL office will verify your marks.",
                    "transcript": serialize(t)}), 201


@transcripts_bp.get("/student/transcript/file")
@role_required(STUDENT)
def my_transcript_file():
    t = current_student().transcript
    if t is None:
        raise ApiError("You haven't uploaded a transcript yet", 404)
    return _send_pdf(t)


# ---- System admin --------------------------------------------------------------------------

def _get(transcript_id: int) -> Transcript:
    t = db.session.get(Transcript, transcript_id)
    if t is None:
        raise ApiError("Transcript not found", 404)
    return t


def _row(t: Transcript) -> dict:
    s = t.student
    return {**serialize(t), "student": {
        "student_id": s.student_id, "name": f"{s.first_name} {s.last_name}",
        "admission_no": s.admission_no, "course": s.course, "year_of_study": s.year_of_study}}


@transcripts_bp.get("/admin/transcripts")
@role_required(ADMIN)
def list_transcripts():
    query = Transcript.query.join(Student)
    status = choice_arg("status", TranscriptStatus.ALL)
    if status:
        query = query.filter(Transcript.status == status)
    search = str_arg("search").lower()
    if search:
        like = f"%{search}%"
        full_name = func.lower(func.concat(Student.first_name, " ", Student.last_name))
        query = query.filter(or_(full_name.like(like), Student.admission_no.like(like)))
    pending_first = case((Transcript.status == TranscriptStatus.PENDING, 0), else_=1)
    query = query.order_by(pending_first, Transcript.uploaded_at.desc())
    page = paginate(query, _row)
    page["pending"] = Transcript.query.filter_by(status=TranscriptStatus.PENDING).count()
    return jsonify(page)


@transcripts_bp.get("/admin/transcripts/<int:transcript_id>")
@role_required(ADMIN)
def transcript_detail(transcript_id):
    t = _get(transcript_id)
    marks = latest_marks(t.student_id)
    units = {u.unit_id: u.unit_name for u in AcademicUnit.query.all()}
    return jsonify({"transcript": {
        **_row(t),
        "reviewed_by": t.reviewer.display_name if t.reviewer else None,
        "marks": sorted(({"unit": units.get(uid), "mark": m} for uid, m in marks.items()),
                        key=lambda g: g["unit"] or ""),
    }})


@transcripts_bp.get("/admin/transcripts/<int:transcript_id>/file")
@role_required(ADMIN)
def transcript_file(transcript_id):
    return _send_pdf(_get(transcript_id))


@transcripts_bp.patch("/admin/transcripts/<int:transcript_id>")
@role_required(ADMIN)
def review_transcript(transcript_id):
    data = json_body()
    t = review(_get(transcript_id), current_user(), data.get("action"), data.get("reason"))
    return jsonify({"message": f"Marks {t.status}", "transcript": _row(t)})
