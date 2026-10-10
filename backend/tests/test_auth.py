"""Tests for /api/auth (register, login, me).

Covers your test cases TC01 (valid student registration) and TC02 (duplicate email),
plus validation, login and the protected /me endpoint.
(See the top of test_opportunities.py for how pytest tests and fixtures work.)
Each test follows the same pattern: arrange (prepare data) → act (call the API)
→ assert (check the status code, the JSON and the database).
"""
import pytest
from flask_jwt_extended import decode_token

from app.auth import services
from app.models import IndustryPartner, Student, User

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
ME = "/api/auth/me"


def login(client, email, password):
    """Call the login endpoint and return the whole response (status + JSON)."""
    return client.post(LOGIN, json={"email": email, "password": password})


# --- Registration -------------------------------------------------------------

def test_tc01_student_registers_with_valid_details(client, student_payload):
    """TC01: valid student registration -> 201, row in users AND students."""
    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 201
    body = res.get_json()
    assert body["user"]["role"] == "student"
    assert "password_hash" not in str(body)

    user = User.query.filter_by(email=student_payload["email"]).one()
    student = Student.query.filter_by(user_id=user.user_id).one()
    assert student.admission_no == "168003"
    assert user.password_hash != student_payload["password"]  # stored hashed


def test_tc02_register_existing_email_returns_409(client, student_payload):
    """TC02: registering an email that already exists -> 409 'Email already in use'."""
    assert client.post(REGISTER, json=student_payload).status_code == 201

    student_payload["admission_no"] = "999999"  # different admission no, same email
    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 409
    assert res.get_json()["error"] == "Email already in use"
    assert User.query.count() == 1


def test_duplicate_email_is_case_insensitive(client, student_payload):
    client.post(REGISTER, json=student_payload)
    student_payload.update(email=student_payload["email"].upper(), admission_no="111")
    assert client.post(REGISTER, json=student_payload).status_code == 409


def test_duplicate_admission_number_returns_409(client, student_payload):
    client.post(REGISTER, json=student_payload)
    student_payload["email"] = "other@strathmore.edu"

    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 409
    assert "admission_no" in res.get_json()["fields"]
    assert User.query.count() == 1


def test_missing_required_field_names_the_field(client, student_payload):
    del student_payload["first_name"]

    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 400
    body = res.get_json()
    assert "first_name" in body["fields"]
    assert set(body) == {"error", "fields"}  # consistent error shape


def test_password_mismatch_returns_400(client, student_payload):
    student_payload["confirm_password"] = "Different123"

    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 400
    assert "confirm_password" in res.get_json()["fields"]


@pytest.mark.parametrize("weak", ["short1", "onlyletters", "12345678"])
def test_weak_password_returns_400(client, student_payload, weak):
    student_payload["password"] = student_payload["confirm_password"] = weak

    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 400
    assert "password" in res.get_json()["fields"]


@pytest.mark.parametrize("field,value", [
    ("email", "not-an-email"),
    ("year_of_study", 5),
    ("year_of_study", 0),
    ("admission_no", "ABC123"),
])
def test_invalid_student_fields_return_400(client, student_payload, field, value):
    student_payload[field] = value

    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 400
    assert field in res.get_json()["fields"]


# Only emails ending in .ke, .com or .edu may register.
@pytest.mark.parametrize("email", [
    "jane.doe@strathmore.edu",
    "jane.doe@strathmore.ac.ke",
    "hr@acme.co.ke",
    "jane.doe@gmail.com",
    "JANE.DOE@STRATHMORE.EDU",      # upper case is fine (stored lowercase)
])
def test_allowed_email_endings_can_register(client, student_payload, email):
    student_payload["email"] = email
    assert client.post(REGISTER, json=student_payload).status_code == 201


@pytest.mark.parametrize("email", [
    "jane@example.org",             # .org not allowed
    "jane@example.net",             # .net not allowed
    "jane@example.co.uk",           # .uk not allowed
    "jane@strathmore.educ",         # must END exactly in .edu
    "jane@strathmore",              # no ending at all
])
def test_other_email_endings_are_rejected(client, student_payload, email):
    student_payload["email"] = email

    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 400
    assert "email" in res.get_json()["fields"]


def test_system_admin_cannot_self_register(client, student_payload):
    student_payload["role"] = "system_admin"

    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 400
    assert "role" in res.get_json()["fields"]
    assert User.query.count() == 0


def test_industry_partner_registers(client, partner_payload):
    res = client.post(REGISTER, json=partner_payload)

    assert res.status_code == 201
    assert res.get_json()["user"]["name"] == "Acme Kenya Ltd"
    assert IndustryPartner.query.count() == 1


# ---- Phone numbers (Kenyan formats) ------------------------------------------------

# Every accepted format is saved the same way: +254 followed by 9 digits.
@pytest.mark.parametrize("phone", [
    "0712345678",          # local mobile
    "0712 345 678",        # with spaces
    "0712-345-678",        # with dashes
    "0110345678",          # newer 01 prefix
    "+254712345678",       # international
    "+254 712 345 678",    # international with spaces
    "254712345678",        # international without the +
])
def test_valid_kenyan_phone_is_accepted_and_standardised(client, partner_payload, phone):
    partner_payload["phone"] = phone

    res = client.post(REGISTER, json=partner_payload)

    assert res.status_code == 201
    expected = "+254" + phone.replace(" ", "").replace("-", "")[-9:]
    assert res.get_json()["user"]["profile"]["phone"] == expected


@pytest.mark.parametrize("phone", [
    "07123456789",         # one digit too many
    "071234567",           # one digit too few
    "0812345678",          # must start 07 or 01
    "1234567",             # not a Kenyan number
    "0712 abc 678",        # letters
    "+255712345678",       # Tanzania code, not Kenya
    "254+712345678",       # + in the wrong place
])
def test_invalid_phone_is_rejected(client, partner_payload, phone):
    partner_payload["phone"] = phone

    res = client.post(REGISTER, json=partner_payload)

    assert res.status_code == 400
    assert "phone" in res.get_json()["fields"]
    assert IndustryPartner.query.count() == 0   # nothing saved


def test_failed_profile_insert_rolls_back_user_row(client, student_payload, monkeypatch):
    """If the role row can't be created, the users row must not be left behind."""
    # monkeypatch temporarily replaces a function for this test only. Here we swap
    # _build_profile for one that always crashes, to simulate the second INSERT failing.
    def boom(user, data):
        raise RuntimeError("simulated failure")
    monkeypatch.setattr(services, "_build_profile", boom)

    res = client.post(REGISTER, json=student_payload)

    assert res.status_code == 500
    assert User.query.count() == 0


# --- Login ------------------------------------------------------------------------

def test_login_with_correct_credentials_returns_token_with_role(app, client, student_payload):
    client.post(REGISTER, json=student_payload)

    res = login(client, student_payload["email"], student_payload["password"])

    assert res.status_code == 200
    body = res.get_json()
    # decode_token opens the JWT so we can read what's inside it (its "claims").
    claims = decode_token(body["access_token"])
    assert claims["role"] == "student"
    assert claims["user_id"] == body["user"]["user_id"]
    assert "password_hash" not in str(body)


def test_login_with_wrong_password_returns_401(client, student_payload):
    client.post(REGISTER, json=student_payload)

    res = login(client, student_payload["email"], "WrongPass999")

    assert res.status_code == 401
    assert res.get_json()["error"] == "Invalid email or password"


def test_login_with_unknown_email_returns_same_generic_401(client):
    res = login(client, "nobody@strathmore.edu", "Whatever123")

    assert res.status_code == 401
    assert res.get_json()["error"] == "Invalid email or password"


# --- Default admin: username login ------------------------------------------------
# `seeded` runs flask seed-data's logic, which creates the admin (username "Admin").

@pytest.mark.parametrize("username", ["Admin", "admin", "ADMIN", "  Admin  "])
def test_default_admin_logs_in_with_username(app, client, seeded, username):
    res = login(client, username, "Admin")

    assert res.status_code == 200
    body = res.get_json()
    assert body["user"]["role"] == "system_admin"
    assert decode_token(body["access_token"])["role"] == "system_admin"


def test_default_admin_wrong_password_returns_401(client, seeded):
    res = login(client, "Admin", "wrong-password1")
    assert res.status_code == 401
    assert res.get_json()["error"] == "Invalid email or password"


def test_default_admin_can_also_log_in_with_email(client, seeded):
    assert login(client, "admin@wbl.local", "Admin").status_code == 200


def test_students_cannot_log_in_by_name(client, seeded, student_payload):
    # Username login is only for system admins; a student's name is not a username.
    client.post(REGISTER, json=student_payload)
    assert login(client, "Jane Doe", student_payload["password"]).status_code == 401
    assert login(client, "Jane", student_payload["password"]).status_code == 401


def test_reseeding_does_not_duplicate_the_admin(seeded):
    from app.models import SystemAdmin
    from app.seed.seeder import seed_all
    seed_all()
    assert SystemAdmin.query.count() == 1


# --- /me --------------------------------------------------------------------------

def test_me_without_token_returns_401(client):
    res = client.get(ME)

    assert res.status_code == 401
    assert set(res.get_json()) == {"error", "fields"}


def test_me_with_token_returns_current_user(client, student_payload):
    client.post(REGISTER, json=student_payload)
    token = login(client, student_payload["email"], student_payload["password"]) \
        .get_json()["access_token"]

    res = client.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200
    user = res.get_json()["user"]
    assert user["email"] == student_payload["email"]
    assert user["role"] == "student"
    assert "password_hash" not in str(user)
