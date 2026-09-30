"""Import every model here so Flask-Migrate (Alembic) detects all 12 tables."""
from app.models.academic import AcademicUnit, Grade, GradeProfile
from app.models.placement import (
    Application,
    InternshipOpportunity,
    OpportunityPrecursor,
    OpportunityStatus,
    PlacementRecord,
    Recommendation,
    RequirementImportance,
)
from app.models.user import IndustryPartner, Student, SystemAdmin, User, UserRole

__all__ = [
    "User", "UserRole", "Student", "IndustryPartner", "SystemAdmin",
    "AcademicUnit", "GradeProfile", "Grade",
    "InternshipOpportunity", "OpportunityPrecursor", "Recommendation",
    "Application", "PlacementRecord",
]
