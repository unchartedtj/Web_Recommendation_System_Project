"""Transcript upload and marks verification.

Flow: the student types their marks and uploads their transcript (PDF) → status "pending" →
the WBL office (system admin) compares them → "accepted" (the student may now apply) or
"rejected" with a reason (the student fixes their marks and/or uploads again).
If an accepted student later changes their marks, the status goes back to "pending".
"""
import os
import secrets
from datetime import datetime, timezone

from flask import current_app

from app.activity import log_activity
from app.errors import ApiError
from app.extensions import db
from app.models import Transcript, TranscriptStatus
from app.utils import iso

REASON_MAX = 255


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def folder() -> str:
    path = current_app.config["TRANSCRIPT_FOLDER"]
    os.makedirs(path, exist_ok=True)
    return path


def file_path(t: Transcript) -> str:
    return os.path.join(folder(), t.stored_name)


def marks_verified(student) -> bool:
    """May this student apply? Only once the WBL office accepted their marks."""
    return student.transcript is not None and student.transcript.status == TranscriptStatus.ACCEPTED


def transcript_status(student) -> str | None:
    return student.transcript.status if student.transcript else None


def serialize(t: Transcript | None) -> dict | None:
    if t is None:
        return None
    return {
        "transcript_id": t.transcript_id,
        "status": t.status,
        "original_name": t.original_name,
        "file_size": t.file_size,
        "uploaded_at": iso(t.uploaded_at),
        "review_reason": t.review_reason,
        "reviewed_at": iso(t.reviewed_at),
    }


def _write_file(data: bytes) -> str:
    """Save the bytes under a new random name; return that name."""
    name = f"{secrets.token_hex(16)}.pdf"
    with open(os.path.join(folder(), name), "wb") as f:
        f.write(data)
    return name


def _remove_file(name: str | None):
    if not name:
        return
    try:
        os.remove(os.path.join(folder(), name))
    except OSError:
        pass                                    # already gone: nothing to do


def save_upload(student, upload) -> Transcript:
    """Store a newly uploaded transcript (replacing any earlier one) → status pending."""
    if upload is None or not upload.filename:
        raise ApiError("Choose a PDF file to upload", 400, {"file": "Choose a PDF file to upload"})
    data = upload.read()
    if not data:
        raise ApiError("The file is empty", 400, {"file": "The file is empty"})
    if len(data) > current_app.config["TRANSCRIPT_MAX_BYTES"]:
        raise ApiError("The file is too large (maximum 5 MB)", 400, {"file": "Maximum size is 5 MB"})
    # Check the real content, not just the ".pdf" name: every PDF starts with "%PDF-".
    if not data.startswith(b"%PDF-"):
        raise ApiError("Only PDF files are accepted", 400, {"file": "Upload your transcript as a PDF"})

    original = os.path.basename(upload.filename)[:255]
    new_name = _write_file(data)
    t = student.transcript
    old_name = t.stored_name if t else None
    try:
        if t is None:
            t = Transcript(student_id=student.student_id)
            db.session.add(t)
        t.stored_name, t.original_name, t.file_size = new_name, original, len(data)
        t.uploaded_at, t.status = _now(), TranscriptStatus.PENDING
        t.review_reason = t.reviewed_by = t.reviewed_at = None
        db.session.flush()
        log_activity("transcript.uploaded", actor=student.user_id, target_type="transcript",
                     target_id=t.transcript_id, details={"file": original})
        db.session.commit()
    except Exception:
        db.session.rollback()
        _remove_file(new_name)
        raise
    _remove_file(old_name)                       # the replaced PDF is no longer needed
    return t


def reset_after_marks_change(student) -> bool:
    """The student changed their marks: an earlier decision no longer applies.
    Doesn't commit (the profile save does). Returns True if the status changed."""
    t = student.transcript
    if t is None or t.status == TranscriptStatus.PENDING:
        return False
    t.status = TranscriptStatus.PENDING
    t.review_reason = t.reviewed_by = t.reviewed_at = None
    log_activity("transcript.reset", actor=student.user_id, target_type="transcript",
                 target_id=t.transcript_id, details={"reason": "Marks changed"})
    return True


def review(t: Transcript, admin, action, reason) -> Transcript:
    """The admin accepts or rejects the marks. A rejection needs a reason."""
    if action not in ("accept", "reject"):
        raise ApiError("Validation failed", 400, {"action": "Must be 'accept' or 'reject'"})
    reason = (reason or "").strip() if isinstance(reason, str) else ""
    if action == "reject" and not reason:
        raise ApiError("Validation failed", 400,
                       {"reason": "Tell the student why their marks were rejected"})
    if len(reason) > REASON_MAX:
        raise ApiError("Validation failed", 400, {"reason": f"At most {REASON_MAX} characters"})

    t.status = TranscriptStatus.ACCEPTED if action == "accept" else TranscriptStatus.REJECTED
    t.review_reason = reason or None
    t.reviewed_by, t.reviewed_at = admin.user_id, _now()
    log_activity(f"transcript.{t.status}", actor=admin, target_type="transcript",
                 target_id=t.transcript_id,
                 details={"student": f"{t.student.first_name} {t.student.last_name}",
                          "reason": t.review_reason})
    db.session.commit()
    return t


def demo_pdf(title: str, lines: list[str]) -> bytes:
    """A small, valid one-page PDF with some text (used for the seeded demo students)."""
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    text = ["BT", "/F1 16 Tf", "60 780 Td", f"({esc(title)}) Tj", "/F1 11 Tf"]
    for line in lines:
        text += ["0 -18 Td", f"({esc(line)}) Tj"]
    text.append("ET")
    stream = "\n".join(text).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> "
        b"/Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def seed_accepted(student, lines: list[str]) -> bool:
    """Give a demo student an already-accepted transcript (only if they have none)."""
    if student.transcript is not None:
        return False
    data = demo_pdf(f"DEMO transcript: {student.first_name} {student.last_name} "
                    f"({student.admission_no})", lines)
    t = Transcript(student_id=student.student_id, stored_name=_write_file(data),
                   original_name="demo-transcript.pdf", file_size=len(data),
                   uploaded_at=_now(), status=TranscriptStatus.ACCEPTED,
                   review_reason=None, reviewed_at=_now())
    db.session.add(t)
    return True
