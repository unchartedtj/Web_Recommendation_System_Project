"""Import every model here so Flask-Migrate (Alembic) detects all 12 tables.

It also means other code can simply write `from app.models import User, Grade`
instead of remembering which file each class lives in.
"""
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

# __all__ lists the names this package "exports" (what `from app.models import *` gives you).
__all__ = [
    "User", "UserRole", "Student", "IndustryPartner", "SystemAdmin",
    "AcademicUnit", "GradeProfile", "Grade",
    "InternshipOpportunity", "OpportunityPrecursor", "Recommendation",
    "Application", "PlacementRecord",
]
