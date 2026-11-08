"""A student's uploaded transcript (PDF) and its verification status.

The student types their marks AND uploads their official transcript. The WBL office (system
admin) compares the two and accepts or rejects them. Only students whose marks were ACCEPTED
can apply for internships. One transcript per student: uploading again replaces it.
The PDF itself is stored on disk (TRANSCRIPT_FOLDER), not in the database.
"""
from app.extensions import db


class TranscriptStatus:
    PENDING = "pending"        # uploaded, waiting for the WBL office
    ACCEPTED = "accepted"      # the typed marks match the transcript
    REJECTED = "rejected"      # they don't match (review_reason says why)
    ALL = (PENDING, ACCEPTED, REJECTED)


class Transcript(db.Model):
    __tablename__ = "transcripts"

    transcript_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id", ondelete="CASCADE"),
                           nullable=False, unique=True)
    stored_name = db.Column(db.String(80), nullable=False)       # random file name on disk
    original_name = db.Column(db.String(255), nullable=False)    # the name the student uploaded
    file_size = db.Column(db.Integer, nullable=False)            # bytes
    uploaded_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    status = db.Column(db.Enum(*TranscriptStatus.ALL, name="transcript_status"), nullable=False,
                       default=TranscriptStatus.PENDING, server_default=TranscriptStatus.PENDING)
    review_reason = db.Column(db.String(255))                    # why it was rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"))
    reviewed_at = db.Column(db.DateTime)

    student = db.relationship("Student", back_populates="transcript")
    reviewer = db.relationship("User")
