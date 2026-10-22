
import re   # regular expressions: patterns for checking text formats

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.(?:ke|com|edu)$", re.IGNORECASE) #email specifics 
SELF_REGISTER_ROLES = ("student", "industry_partner")  # create users
# Fields for  sign-up , and the extra fields per role.
COMMON_FIELDS = ("email", "password", "confirm_password")
ROLE_FIELDS = {
    "student": ("admission_no", "first_name", "last_name", "course", "year_of_study"),
    "industry_partner": ("organization_name", "contact_person", "phone"),
}

PHONE_RE = re.compile(r"^(?:0|\+?254)[17]\d{8}$")    #phone no characteristics ie must have digits,start with 0 or +254, followed by 7 or 1, and then 8 more digits 


def _clean(value):
    """Trim strings; convert other scalars (e.g. year_of_study sent as a number) to str."""
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value).strip()


def validate_email(email: str) -> str | None:
    if not EMAIL_RE.match(email) or len(email) > 255:
        return "Enter a valid email address ending in .ke, .com or .edu"
    return None


def normalize_phone(phone: str) -> str | None: #normalize phone numbers to standard format (+2547XXXXXXXX)
   
    compact = re.sub(r"[\s-]", "", phone)   # remove spaces and dashes from phone num
    if not PHONE_RE.match(compact):
        return None
    # The last 9 digits are the same in every format (e.g. 712345678); put +254 in front.
    return "+254" + compact[-9:]

# Password criteria for registration
def validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters"

    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):      # password must contain at least one letter [A-Za-z], and at least one digit (\d)
        return "Password must contain at least one letter and one number"
    return None

# Password validation for registration
def validate_registration(data: dict) -> tuple[dict, dict]:
    """Check a sign-up request. Returns (cleaned data, errors)."""
    errors: dict[str, str] = {}
    role = _clean(data.get("role"))

    # The role decides which fields are needed, so check it first and stop if it's wrong.
    if role == "system_admin":
        errors["role"] = "System administrators cannot self-register"
        return {}, errors
    if role not in SELF_REGISTER_ROLES:
        errors["role"] = "Role must be 'student' or 'industry_partner'"
        return {}, errors

    # Build a cleaned copy containing only the fields this role needs (trimmed).
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
        cleaned["email"] = cleaned["email"].lower()   # emails are stored lowercase
    
        if msg := validate_email(cleaned["email"]):
            errors["email"] = msg

    if "password" not in errors and (msg := validate_password(cleaned["password"])):
        errors["password"] = msg

    # Only compare the two passwords if both were otherwise fine.
    if ("confirm_password" not in errors and "password" not in errors
            and cleaned["password"] != cleaned["confirm_password"]):
        errors["confirm_password"] = "Passwords do not match"

    if role == "student":
        # .isdigit() is True only if every character is 0-9.
        if "admission_no" not in errors and not cleaned["admission_no"].isdigit():
            errors["admission_no"] = "Admission number must contain digits only"
        if "year_of_study" not in errors:
            try:
                year = int(cleaned["year_of_study"])   # "must be digit 1-4" 
                if not 1 <= year <= 4:
                    raise ValueError                   # error if year is not 1,2,3,4
                cleaned["year_of_study"] = year
            except ValueError:
                errors["year_of_study"] = "Year of study must be a whole number from 1 to 4"
    else:
        if "phone" not in errors:
            phone = normalize_phone(cleaned["phone"])
            if phone is None:
                errors["phone"] = ("Enter a valid  phone number, "
                                   "e.g. 0712 345 678 or +254 712 345 678")
            else:
                cleaned["phone"] = phone   # save it in the standard +254 format

    return cleaned, errors


def validate_login(data: dict) -> tuple[dict, dict]:
    """Login only checks that both fields were filled in; the password check happens in the route.

    The "email" box also accepts a system admin's USERNAME (e.g. "Admin"). It's lowercased
    here, so usernames are case-insensitive ("Admin", "admin" and "ADMIN" all work).
    """
    email = _clean(data.get("email")).lower()
    password = data.get("password") if isinstance(data.get("password"), str) else ""
    errors = {}
    if not email:
        errors["email"] = "This field is required"
    if not password:
        errors["password"] = "This field is required"
    return {"email": email, "password": password}, errors
