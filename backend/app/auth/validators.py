"""Input validation for auth requests.

Each validator returns (cleaned_data, errors). `errors` maps field name -> message,
so the frontend can show every problem next to its input in one round trip.
"""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
SELF_REGISTER_ROLES = ("student", "industry_partner")  # system admins are created via CLI only

COMMON_FIELDS = ("email", "password", "confirm_password")
ROLE_FIELDS = {
    "student": ("admission_no", "first_name", "last_name", "course", "year_of_study"),
    "industry_partner": ("organization_name", "contact_person", "phone"),
}
PHONE_RE = re.compile(r"^\+?[0-9 ()-]{7,20}$")


def _clean(value):
    """Trim strings; convert other scalars (e.g. year_of_study sent as a number) to str."""
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value).strip()


def validate_email(email: str) -> str | None:
    if not EMAIL_RE.match(email) or len(email) > 255:
        return "Enter a valid email address"
    return None


def validate_password(password: str) -> str | None:
    """Password policy: at least 8 characters, containing a letter and a number."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number"
    return None


def validate_registration(data: dict) -> tuple[dict, dict]:
    errors: dict[str, str] = {}
    role = _clean(data.get("role"))

    if role == "system_admin":
        errors["role"] = "System administrators cannot self-register"
        return {}, errors
    if role not in SELF_REGISTER_ROLES:
        errors["role"] = "Role must be 'student' or 'industry_partner'"
        return {}, errors

    # Passwords are not trimmed. Leading and trailing spaces are the user's choice.
    cleaned = {f: _clean(data.get(f)) for f in COMMON_FIELDS + ROLE_FIELDS[role]
               if f not in ("password", "confirm_password")}
    cleaned["password"] = data.get("password") if isinstance(data.get("password"), str) else ""
    cleaned["confirm_password"] = (data.get("confirm_password")
                                   if isinstance(data.get("confirm_password"), str) else "")
    cleaned["role"] = role

    # 1. Required fields
    for field in COMMON_FIELDS + ROLE_FIELDS[role]:
        if not cleaned[field]:
            errors[field] = "This field is required"

    # 2. Format rules. Only checked for fields that are present, so each field gets one message.
    if "email" not in errors:
        cleaned["email"] = cleaned["email"].lower()
        if msg := validate_email(cleaned["email"]):
            errors["email"] = msg

    if "password" not in errors and (msg := validate_password(cleaned["password"])):
        errors["password"] = msg

    if ("confirm_password" not in errors and "password" not in errors
            and cleaned["password"] != cleaned["confirm_password"]):
        errors["confirm_password"] = "Passwords do not match"

    if role == "student":
        if "admission_no" not in errors and not cleaned["admission_no"].isdigit():
            errors["admission_no"] = "Admission number must contain digits only"
        if "year_of_study" not in errors:
            try:
                year = int(cleaned["year_of_study"])
                if not 1 <= year <= 4:
                    raise ValueError
                cleaned["year_of_study"] = year
            except ValueError:
                errors["year_of_study"] = "Year of study must be a whole number from 1 to 4"
    else:
        if "phone" not in errors and not PHONE_RE.match(cleaned["phone"]):
            errors["phone"] = "Enter a valid phone number"

    return cleaned, errors


def validate_login(data: dict) -> tuple[dict, dict]:
    email = _clean(data.get("email")).lower()
    password = data.get("password") if isinstance(data.get("password"), str) else ""
    errors = {}
    if not email:
        errors["email"] = "This field is required"
    if not password:
        errors["password"] = "This field is required"
    return {"email": email, "password": password}, errors
