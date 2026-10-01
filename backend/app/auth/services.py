"""Auth business logic: creating accounts and serialising users for responses.

"Services" hold the real work (database writes, rules) so the route functions stay short,
and so the same logic can be reused. For example, `flask create-admin` and
`flask seed-data` both call create_user_with_profile().
"""
from sqlalchemy.exc import IntegrityError   # raised by the database on e.g. a duplicate UNIQUE value

from app.errors import ApiError
from app.extensions import db
from app.models import IndustryPartner, Student, SystemAdmin, User, UserRole

EMAIL_IN_USE = "Email already in use"
ADMISSION_IN_USE = "Admission number already registered"


def _conflict_from_integrity_error(err: IntegrityError) -> ApiError:
    """Map a MySQL duplicate-key error to a friendly 409 response.

    The duplicate checks at the start of create_user_with_profile() cover normal use.
    This handles two requests racing to register the same email or admission number
    at the same moment: both pass the check, but MySQL's UNIQUE rule rejects the second.
    """
    msg = str(err.orig).lower()   # the raw MySQL message names the column that clashed
    if "admission_no" in msg:
        return ApiError(ADMISSION_IN_USE, 409, {"admission_no": ADMISSION_IN_USE})
    if "email" in msg:
        return ApiError(EMAIL_IN_USE, 409, {"email": EMAIL_IN_USE})
    return ApiError("Could not create account", 409)


def _build_profile(user: User, data: dict):
    """Create the role-specific row (Student / IndustryPartner / SystemAdmin) for a user."""
    if user.role == UserRole.STUDENT:
        return Student(
            user_id=user.user_id,
            admission_no=data["admission_no"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            course=data["course"],
            year_of_study=data["year_of_study"],
        )
    if user.role == UserRole.INDUSTRY_PARTNER:
        return IndustryPartner(
            user_id=user.user_id,
            organization_name=data["organization_name"],
            contact_person=data["contact_person"],
            phone=data["phone"],
        )
    return SystemAdmin(user_id=user.user_id, name=data["name"])


def create_user_with_profile(data: dict) -> User:
    """Create the users row and its role row atomically.

    `data` must already be validated and contain `email`, `password`, `role`,
    plus the role-specific fields.
    "Atomically" = both rows are saved, or neither is. There's never a user without a profile.
    """
    # Friendly duplicate checks first, so the user gets a clear message.
    if User.query.filter_by(email=data["email"]).first():
        raise ApiError(EMAIL_IN_USE, 409, {"email": EMAIL_IN_USE})
    if data["role"] == "student" and \
            Student.query.filter_by(admission_no=data["admission_no"]).first():
        raise ApiError(ADMISSION_IN_USE, 409, {"admission_no": ADMISSION_IN_USE})

    try:
        # One transaction: flush() sends the INSERT for users so we get user_id,
        # but nothing is permanent until commit(). If the role row fails, rollback()
        # removes the user row too.
        user = User(email=data["email"], role=UserRole(data["role"]))
        user.set_password(data["password"])   # store the hash, never the plain password
        db.session.add(user)
        db.session.flush()

        db.session.add(_build_profile(user, data))
        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()
        # `from err` keeps the original database error attached for debugging.
        raise _conflict_from_integrity_error(err) from err
    except Exception:
        db.session.rollback()
        raise
    return user


def serialize_user(user: User) -> dict:
    """Public representation of a user.

    Fields are whitelisted explicitly, so password_hash can never leak.
    "Serialize" = turn a database object into a plain dict that can be sent as JSON.
    """
    result = {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role.value,              # e.g. "student"
        "name": user.display_name,            # e.g. "Jane Doe" or "Acme Kenya Ltd"
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "profile": {},
    }
    # Add the role-specific details.
    p = user.profile
    if user.role == UserRole.STUDENT and p:
        result["profile"] = {
            "student_id": p.student_id,
            "admission_no": p.admission_no,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "course": p.course,
            "year_of_study": p.year_of_study,
        }
    elif user.role == UserRole.INDUSTRY_PARTNER and p:
        result["profile"] = {
            "partner_id": p.partner_id,
            "organization_name": p.organization_name,
            "contact_person": p.contact_person,
            "phone": p.phone,
        }
    elif user.role == UserRole.SYSTEM_ADMIN and p:
        result["profile"] = {"admin_id": p.admin_id, "name": p.name}
    return result
