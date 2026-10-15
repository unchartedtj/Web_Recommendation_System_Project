
from app.extensions import db


class Skill(db.Model):
    """A technical skill, e.g. "Python" in the category "Programming"."""
    __tablename__ = "skills"

    skill_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)   # used to group skills in the UI
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())


class Sector(db.Model):
    """A career area. Used both as a student's career interest and as an internship's sector."""
    __tablename__ = "sectors"

    sector_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())


class OpportunitySkill(db.Model):
    """A skill an internship requires, marked essential or desirable (like unit requirements)."""
    __tablename__ = "opportunity_skills"

    opportunity_id = db.Column(
        db.Integer,
        db.ForeignKey("internship_opportunities.opportunity_id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.skill_id", ondelete="CASCADE"),
                         primary_key=True, index=True)
    importance = db.Column(
        db.Enum("essential", "desirable", name="skill_importance"),
        nullable=False, default="essential", server_default="essential",
    )

    opportunity = db.relationship("InternshipOpportunity", back_populates="skills")
    skill = db.relationship("Skill")


class StudentSkill(db.Model):
    """A skill a student says they have (self-reported, picked from the preset list)."""
    __tablename__ = "student_skills"

    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id", ondelete="CASCADE"),
                           primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.skill_id", ondelete="CASCADE"),
                         primary_key=True, index=True)

    student = db.relationship("Student", back_populates="skills")
    skill = db.relationship("Skill")


class StudentInterest(db.Model):
    """A sector a student is interested in working in (1 to 3 per student)."""
    __tablename__ = "student_interests"

    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id", ondelete="CASCADE"),
                           primary_key=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.sector_id", ondelete="CASCADE"),
                          primary_key=True, index=True)

    student = db.relationship("Student", back_populates="interests")
    sector = db.relationship("Sector")
