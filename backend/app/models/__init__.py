"""Import every model here so Flask-Migrate (Alembic) detects all tables.

It also means other code can simply write `from app.models import User, Grade`
instead of remembering which file each class lives in.
"""
from app.models.academic import AcademicUnit, Grade, GradeProfile
from app.models.activity import ActivityLog
from app.models.sus import SusResponse
from app.models.placement import (
    Application,
    ApplicationStatus,
    InternshipOpportunity,
    OpportunityPrecursor,
    OpportunityStatus,
    PlacementRecord,
    PlacementStatus,
    Recommendation,
    RequirementImportance,
)
from app.models.profile import OpportunitySkill, Sector, Skill, StudentInterest, StudentSkill
from app.models.user import IndustryPartner, Student, SystemAdmin, User, UserRole

# __all__ lists the names this package "exports" (what `from app.models import *` gives you).
__all__ = [
    "User", "UserRole", "Student", "IndustryPartner", "SystemAdmin",
    "AcademicUnit", "GradeProfile", "Grade",
    "InternshipOpportunity", "OpportunityPrecursor", "Recommendation",
    "Application", "ApplicationStatus", "PlacementRecord", "PlacementStatus",
    "Skill", "Sector", "OpportunitySkill", "StudentSkill", "StudentInterest",
    "ActivityLog", "SusResponse",
]
