
from app.extensions import db


class OpportunityStatus:
    """Allowed values for InternshipOpportunity.status (constants avoid typos)."""
    OPEN = "open"
    CLOSED = "closed"


class RequirementImportance:
    """How much a precursor unit matters to a partner. The engine weights these 2 : 1."""
    ESSENTIAL = "essential"
    DESIRABLE = "desirable"
    ALL = (ESSENTIAL, DESIRABLE)


class InternshipOpportunity(db.Model):
    """An internship posted by an industry partner."""
    __tablename__ = "internship_opportunities"
    # CHECK constraints: MySQL itself refuses rows that break these rules.
    __table_args__ = (
        db.CheckConstraint("status IN ('open','closed')", name="ck_opportunities_status"),
        db.CheckConstraint("slots >= 1", name="ck_opportunities_slots"),
    )

    opportunity_id = db.Column(db.Integer, primary_key=True)
    # Which partner posted it. index=True makes "find all of partner X's posts" fast.
    partner_id = db.Column(db.Integer,
                           db.ForeignKey("industry_partners.partner_id", ondelete="CASCADE"),
                           nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)         # Text = long text, no fixed limit
    # The sector is chosen from the preset `sectors` list (it used to be free text).
    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.sector_id"), nullable=False, index=True)
    location = db.Column(db.String(150))
    # Nullable in the DB for safety; the API requires them for every new opportunity.
    duration_months = db.Column(db.Integer)
    slots = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    application_deadline = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default=OpportunityStatus.OPEN,
                       server_default=OpportunityStatus.OPEN)
    # db.func.now() → MySQL fills in the current date/time when the row is inserted.
    date_posted = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    partner = db.relationship("IndustryPartner", back_populates="opportunities")
    sector = db.relationship("Sector")                     # opportunity.sector.name → e.g. "Data Analytics & AI"
    # Required skills (see models/profile.py). Same ownership rules as the unit requirements below.
    skills = db.relationship("OpportunitySkill", back_populates="opportunity",
                             cascade="all, delete-orphan")
    # cascade="all, delete-orphan": requirements belong to the opportunity. Removing one
    # from opportunity.precursors deletes the row, and deleting the opportunity deletes them all.
    precursors = db.relationship("OpportunityPrecursor", back_populates="opportunity",
                                 cascade="all, delete-orphan")
    recommendations = db.relationship("Recommendation", back_populates="opportunity",
                                      cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="opportunity")
    placement_records = db.relationship("PlacementRecord", back_populates="opportunity")


class OpportunityPrecursor(db.Model):
    """A requirement: an academic unit a partner expects for an opportunity.

    This is a "link table" between opportunities and units. Its primary key is BOTH
    columns together (a composite key), so the same unit can't be added twice to the
    same opportunity.
    """
    __tablename__ = "opportunity_precursors"
    __table_args__ = (
        db.CheckConstraint("min_mark IS NULL OR min_mark BETWEEN 0 AND 100",
                           name="ck_precursors_min_mark"),
    )

    opportunity_id = db.Column(
        db.Integer,
        db.ForeignKey("internship_opportunities.opportunity_id", ondelete="CASCADE"),
        primary_key=True,
    )
    unit_id = db.Column(db.Integer,
                        db.ForeignKey("academic_units.unit_id", ondelete="CASCADE"),
                        primary_key=True, index=True)
    # ENUM column: MySQL only accepts 'essential' or 'desirable'.
    importance = db.Column(
        db.Enum(*RequirementImportance.ALL, name="requirement_importance"),
        nullable=False, default=RequirementImportance.ESSENTIAL,
        server_default=RequirementImportance.ESSENTIAL,
    )
    # Numeric(5, 2) = DECIMAL(5,2): up to 5 digits, 2 after the point, e.g. 100.00 or 65.50.
    min_mark = db.Column(db.Numeric(5, 2))  # optional minimum mark out of 100

    opportunity = db.relationship("InternshipOpportunity", back_populates="precursors")
    unit = db.relationship("AcademicUnit", back_populates="precursor_for")


class Recommendation(db.Model):
    """One ranked result for a student. The last four columns are a snapshot taken at
    generation time, so saved results don't drift if grades or requirements change later."""
    __tablename__ = "recommendations"
    __table_args__ = (
        # A student has at most one saved result per opportunity.
        db.UniqueConstraint("student_id", "opportunity_id",
                            name="uq_recommendations_student_opportunity"),
    )

    recommendation_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id", ondelete="CASCADE"),
                           nullable=False, index=True)
    opportunity_id = db.Column(
        db.Integer,
        db.ForeignKey("internship_opportunities.opportunity_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    match_score = db.Column(db.Float, nullable=False)   # cosine similarity, 0 to 1
    # "rank" is a reserved word in MySQL 8; SQLAlchemy quotes it automatically.
    rank = db.Column(db.Integer, nullable=False)        # 1 = best match
    meets_requirements = db.Column(db.Boolean, nullable=False, default=True,
                                   server_default=db.true())
    avg_requirement_mark = db.Column(db.Numeric(5, 2))
    # JSON column: stores a Python list/dict directly (MariaDB keeps it as text).
    unmet_requirements = db.Column(db.JSON)  # [{unit, importance, required, your_mark}]
    # Score breakdown: match_score = weighted sum of these three (weights in config MATCH_WEIGHTS).
    grade_score = db.Column(db.Float)
    skill_score = db.Column(db.Float)
    interest_score = db.Column(db.Float)
    interest_match = db.Column(db.Boolean)   # is the opportunity's sector one of the student's interests?
    missing_skills = db.Column(db.JSON)      # {"essential": [names], "desirable": [names]}
    generated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    student = db.relationship("Student", back_populates="recommendations")
    opportunity = db.relationship("InternshipOpportunity", back_populates="recommendations")


class ApplicationStatus:
    """Allowed values for Application.status."""
    PENDING = "pending"
    SHORTLISTED = "shortlisted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ALL = (PENDING, SHORTLISTED, ACCEPTED, REJECTED, WITHDRAWN)
    ACTIVE = (PENDING, SHORTLISTED)          # still being considered
    FINAL = (ACCEPTED, REJECTED, WITHDRAWN)  # can never change again


class PlacementStatus:
    """Allowed values for PlacementRecord.status."""
    CONFIRMED = "confirmed"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    ALL = (CONFIRMED, ONGOING, COMPLETED, TERMINATED)


class Application(db.Model):
    """A student's application to an opportunity, with their match frozen at apply time."""
    __tablename__ = "applications"
    # One application per student per opportunity (no re-applying after withdrawing).
    __table_args__ = (
        db.UniqueConstraint("student_id", "opportunity_id",
                            name="uq_applications_student_opportunity"),
    )

    application_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id", ondelete="CASCADE"),
                           nullable=False, index=True)
    opportunity_id = db.Column(db.Integer,
                               db.ForeignKey("internship_opportunities.opportunity_id"),
                               nullable=False, index=True)
    application_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    status = db.Column(db.Enum(*ApplicationStatus.ALL, name="application_status"),
                       nullable=False, default=ApplicationStatus.PENDING,
                       server_default=ApplicationStatus.PENDING)
    motivation_note = db.Column(db.Text)                 # optional, max 500 characters
    # The student's marks, skills, interests and match breakdown when they applied.
    # Frozen: later profile changes don't alter what the partner sees.
    profile_snapshot = db.Column(db.JSON)
    match_score_at_apply = db.Column(db.Float)
    meets_requirements_at_apply = db.Column(db.Boolean)
    status_reason = db.Column(db.String(255))            # e.g. "All positions filled"
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(),
                           onupdate=db.func.now())
    decided_at = db.Column(db.DateTime)                  # when it reached a final status

    student = db.relationship("Student", back_populates="applications")
    opportunity = db.relationship("InternshipOpportunity", back_populates="applications")
    # uselist=False → one-to-one: an application has at most one placement record.
    placement_record = db.relationship("PlacementRecord", back_populates="application",
                                       uselist=False)


class PlacementRecord(db.Model):
    """A placement: created when a partner accepts an application."""
    __tablename__ = "placement_records"
    __table_args__ = (
        db.UniqueConstraint("application_id", name="uq_placement_records_application"),
    )

    placement_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"),
                           nullable=False, index=True)
    opportunity_id = db.Column(db.Integer,
                               db.ForeignKey("internship_opportunities.opportunity_id"),
                               nullable=False, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.application_id"),
                               nullable=False, index=True)
    status = db.Column(db.Enum(*PlacementStatus.ALL, name="placement_status"),
                       nullable=False, default=PlacementStatus.CONFIRMED,
                       server_default=PlacementStatus.CONFIRMED)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    status_reason = db.Column(db.String(255))      # e.g. why a placement was terminated
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(),
                           onupdate=db.func.now())

    student = db.relationship("Student", back_populates="placement_records")
    opportunity = db.relationship("InternshipOpportunity", back_populates="placement_records")
    application = db.relationship("Application", back_populates="placement_record")
