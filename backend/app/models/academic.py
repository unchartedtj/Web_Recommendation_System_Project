"""Academic data: units, a student's submitted grade profile, and individual grades.

How they fit together:
    Student ──< GradeProfile ──< Grade >── AcademicUnit
    (one student has many grade profiles; each profile has one grade per unit)
A new GradeProfile is created each time a student submits grades, so older submissions
are kept as history. The recommendation engine always uses the LATEST profile.

(See the top of placement.py for how to read db.Column / db.relationship.)
"""
from app.extensions import db


class AcademicUnit(db.Model):
    """A catalog unit, identified by its (unique) name. Partners may only choose
    requirements from active units, and students must submit a grade for every active unit."""
    __tablename__ = "academic_units"

    unit_id = db.Column(db.Integer, primary_key=True)
    unit_code = db.Column(db.String(20), unique=True, nullable=True)  # optional; unused for now
    # unique=True → MySQL rejects two units with the same name.
    unit_name = db.Column(db.String(200), unique=True, nullable=False)
    # Inactive units are hidden from partners and students but kept for old grades.
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
    # profile.grades gives all the Grade rows of this submission.
    grades = db.relationship("Grade", back_populates="profile", cascade="all, delete-orphan")


class Grade(db.Model):
    """One mark: a student's result in one unit, inside one grade profile."""
    __tablename__ = "grades"
    __table_args__ = (
        # A unit appears at most once per grade profile.
        db.UniqueConstraint("profile_id", "unit_id", name="uq_grades_profile_unit"),
        # MySQL refuses marks outside 0-100.
        db.CheckConstraint("grade_value BETWEEN 0 AND 100", name="ck_grades_value_range"),
    )

    grade_id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer,
                           db.ForeignKey("grade_profiles.profile_id", ondelete="CASCADE"),
                           nullable=False, index=True)
    unit_id = db.Column(db.Integer, db.ForeignKey("academic_units.unit_id"),
                        nullable=False, index=True)
    grade_value = db.Column(db.Numeric(5, 2), nullable=False)  # mark out of 100, e.g. 72.50

    profile = db.relationship("GradeProfile", back_populates="grades")
    unit = db.relationship("AcademicUnit", back_populates="grades")
