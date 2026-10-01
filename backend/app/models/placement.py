"""Opportunities, their requirements, recommendations, applications and placements.

How to read a model class:
- Each class = one database table (__tablename__ gives the table name).
- Each db.Column = one column. primary_key = the row's unique id;
  db.ForeignKey("table.column") = this column points at a row in another table.
- ondelete="CASCADE" → if the referenced row is deleted, MySQL deletes this row too.
- nullable=False → the column must have a value (NOT NULL).
- default=... is filled in by Python; server_default=... is filled in by MySQL itself.
- db.relationship(...) is NOT a column. It lets Python code follow links between tables,
  e.g. opportunity.partner or opportunity.precursors, without writing SQL joins.
  back_populates names the matching relationship on the other class.

Application/placement status columns are plain strings (not DB enums) so new states can be
added later without a migration. Opportunity status is limited to open/closed by a CHECK.
"""
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
    sector = db.Column(db.String(100))
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
    generated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    student = db.relationship("Student", back_populates="recommendations")
    opportunity = db.relationship("InternshipOpportunity", back_populates="recommendations")


class Application(db.Model):
    """A student's application to an opportunity (used in a later step)."""
    __tablename__ = "applications"

    application_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id", ondelete="CASCADE"),
                           nullable=False, index=True)
    opportunity_id = db.Column(db.Integer,
                               db.ForeignKey("internship_opportunities.opportunity_id"),
                               nullable=False, index=True)
    application_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    status = db.Column(db.String(20), nullable=False, default="pending", server_default="pending")

    student = db.relationship("Student", back_populates="applications")
    opportunity = db.relationship("InternshipOpportunity", back_populates="applications")
    # uselist=False → one-to-one: an application has at most one placement record.
    placement_record = db.relationship("PlacementRecord", back_populates="application",
                                       uselist=False)


class PlacementRecord(db.Model):
    """A confirmed placement: which student is at which internship, and when (later step)."""
    __tablename__ = "placement_records"

    placement_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"),
                           nullable=False, index=True)
    opportunity_id = db.Column(db.Integer,
                               db.ForeignKey("internship_opportunities.opportunity_id"),
                               nullable=False, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.application_id"),
                               nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="ongoing", server_default="ongoing")
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    student = db.relationship("Student", back_populates="placement_records")
    opportunity = db.relationship("InternshipOpportunity", back_populates="placement_records")
    application = db.relationship("Application", back_populates="placement_record")
