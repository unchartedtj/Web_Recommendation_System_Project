"""The activity log: who did what, to what, and when (shown on the admin Activity Log page)."""
from app.extensions import db


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    log_id = db.Column(db.Integer, primary_key=True)
    # NULL for system events (e.g. an application rejected automatically when slots fill).
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"))
    action = db.Column(db.String(60), nullable=False, index=True)   # e.g. "application.accepted"
    target_type = db.Column(db.String(40))                           # e.g. "application"
    target_id = db.Column(db.Integer)
    details = db.Column(db.JSON)                                     # any extra facts
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), index=True)

    actor = db.relationship("User")
