"""System Usability Scale (SUS) questionnaire answers, one row per user (test case TC10)."""
from app.extensions import db


class SusResponse(db.Model):
    __tablename__ = "sus_responses"
    # Each answer must be 1 (strongly disagree) to 5 (strongly agree).
    __table_args__ = tuple(db.CheckConstraint(f"q{i} BETWEEN 1 AND 5", name=f"ck_sus_q{i}")
                           for i in range(1, 11))

    response_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"),
                        nullable=False, unique=True)                 # one response per user
    role = db.Column(db.String(20), nullable=False)
    q1 = db.Column(db.SmallInteger, nullable=False)
    q2 = db.Column(db.SmallInteger, nullable=False)
    q3 = db.Column(db.SmallInteger, nullable=False)
    q4 = db.Column(db.SmallInteger, nullable=False)
    q5 = db.Column(db.SmallInteger, nullable=False)
    q6 = db.Column(db.SmallInteger, nullable=False)
    q7 = db.Column(db.SmallInteger, nullable=False)
    q8 = db.Column(db.SmallInteger, nullable=False)
    q9 = db.Column(db.SmallInteger, nullable=False)
    q10 = db.Column(db.SmallInteger, nullable=False)
    sus_score = db.Column(db.Float, nullable=False)                  # 0 to 100
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(),
                           onupdate=db.func.now())

    user = db.relationship("User")

    @property
    def answers(self) -> list[int]:
        return [getattr(self, f"q{i}") for i in range(1, 11)]
