"""Opportunities, their requirements, recommendations, applications and placements.

Application/placement status columns are plain strings (not DB enums) so new states can be
added later without a migration. Opportunity status is limited to open/closed by a CHECK.
"""
from app.extensions import db


class OpportunityStatus:
    OPEN = "open"
    CLOSED = "closed"


class RequirementImportance:
    """How much a precursor unit matters to a partner. The engine weights these 2 : 1."""
    ESSENTIAL = "essential"
    DESIRABLE = "desirable"
    ALL = (ESSENTIAL, DESIRABLE)


class InternshipOpportunity(db.Model):
    __tablename__ = "internship_opportunities"
    __table_args__ = (
        db.CheckConstraint("status IN ('open','closed')", name="ck_opportunities_status"),
        db.CheckConstraint("slots >= 1", name="ck_opportunities_slots"),
    )

    opportunity_id = db.Column(db.Integer, primary_key=True)
    partner_id = db.Column(db.Integer,
                           db.ForeignKey("industry_partners.partner_id", ondelete="CASCADE"),
                           nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sector = db.Column(db.String(100))
    location = db.Column(db.String(150))
    # Nullable in the DB for safety; the API requires them for every new opportunity.
    duration_months = db.Column(db.Integer)
    slots = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    application_deadline = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default=OpportunityStatus.OPEN,
                       server_default=OpportunityStatus.OPEN)
    date_posted = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    partner = db.relationship("IndustryPartner", back_populates="opportunities")
    precursors = db.relationship("OpportunityPrecursor", back_populates="opportunity",
                                 cascade="all, delete-orphan")
    recommendations = db.relationship("Recommendation", back_populates="opportunity",
                                      cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="opportunity")
    placement_records = db.relationship("PlacementRecord", back_populates="opportunity")


class OpportunityPrecursor(db.Model):
    """A requirement: an academic unit a partner expects for an opportunity."""
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
    importance = db.Column(
        db.Enum(*RequirementImportance.ALL, name="requirement_importance"),
        nullable=False, default=RequirementImportance.ESSENTIAL,
        server_default=RequirementImportance.ESSENTIAL,
    )
    min_mark = db.Column(db.Numeric(5, 2))  # optional minimum mark out of 100

    opportunity = db.relationship("InternshipOpportunity", back_populates="precursors")
    unit = db.relationship("AcademicUnit", back_populates="precursor_for")


class Recommendation(db.Model):
    """One ranked result for a student. The last four columns are a snapshot taken at
    generation time, so saved results don't drift if grades or requirements change later."""
    __tablename__ = "recommendations"
    __table_args__ = (
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
    match_score = db.Column(db.Float, nullable=False)
    # "rank" is a reserved word in MySQL 8; SQLAlchemy quotes it automatically.
    rank = db.Column(db.Integer, nullable=False)
    meets_requirements = db.Column(db.Boolean, nullable=False, default=True,
                                   server_default=db.true())
    avg_requirement_mark = db.Column(db.Numeric(5, 2))
    unmet_requirements = db.Column(db.JSON)  # [{unit, importance, required, your_mark}]
    generated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    student = db.relationship("Student", back_populates="recommendations")
    opportunity = db.relationship("InternshipOpportunity", back_populates="recommendations")


class Application(db.Model):
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
    placement_record = db.relationship("PlacementRecord", back_populates="application",
                                       uselist=False)


class PlacementRecord(db.Model):
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
