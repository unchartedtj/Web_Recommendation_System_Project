"""Academic data: units, a student's submitted grade profile, and individual grades.

Not used by the auth feature yet. Created now so later steps don't need a schema redesign.
"""
from app.extensions import db


class AcademicUnit(db.Model):
    """A catalog unit, identified by its (unique) name. Partners may only choose
    requirements from active units, and students must submit a grade for every active unit."""
    __tablename__ = "academic_units"

    unit_id = db.Column(db.Integer, primary_key=True)
    unit_code = db.Column(db.String(20), unique=True, nullable=True)  # optional; unused for now
    unit_name = db.Column(db.String(200), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())

    grades = db.relationship("Grade", back_populates="unit")
    precursor_for = db.relationship("OpportunityPrecursor", back_populates="unit",
                                    cascade="all, delete-orphan")


class GradeProfile(db.Model):
    """One submission of a student's grades (a student may submit more than once)."""
    __tablename__ = "grade_profiles"

    profile_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id", ondelete="CASCADE"),
                           nullable=False, index=True)
    submission_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    student = db.relationship("Student", back_populates="grade_profiles")
    grades = db.relationship("Grade", back_populates="profile", cascade="all, delete-orphan")


class Grade(db.Model):
    __tablename__ = "grades"
    __table_args__ = (
        # A unit appears at most once per grade profile.
        db.UniqueConstraint("profile_id", "unit_id", name="uq_grades_profile_unit"),
        db.CheckConstraint("grade_value BETWEEN 0 AND 100", name="ck_grades_value_range"),
    )

    grade_id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer,
                           db.ForeignKey("grade_profiles.profile_id", ondelete="CASCADE"),
                           nullable=False, index=True)
    unit_id = db.Column(db.Integer, db.ForeignKey("academic_units.unit_id"),
                        nullable=False, index=True)
    grade_value = db.Column(db.Numeric(5, 2), nullable=False)  # mark out of 100

    profile = db.relationship("GradeProfile", back_populates="grades")
    unit = db.relationship("AcademicUnit", back_populates="grades")
