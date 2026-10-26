"""Pytest fixtures shared by ALL test files.

pytest loads this file automatically (the name `conftest.py` is special). Any fixture
defined here can be used by any test just by naming it as a function parameter.

Tests run against a separate MySQL database (TEST_DB_NAME, default wbl_placement_test),
which is created automatically if missing. Tables are rebuilt for every test, so each
test starts from an empty schema and your real data in wbl_placement is never touched.
"""
import os

# The seeded admin's password in tests (set BEFORE the app and the seed catalogue are imported).
os.environ.setdefault("DEFAULT_ADMIN_PASSWORD", "AdminPass123")

import pymysql      # low-level MySQL driver, used only to CREATE the test database
import pytest

from app import create_app              # the application factory (app/__init__.py)
from app.config import TestingConfig    # settings that point at the TEST database
from app.extensions import db           # SQLAlchemy handle, used to create/drop tables


def _ensure_test_database():
    """Create the test database if it doesn't exist yet.

    SQLAlchemy can create TABLES but not the DATABASE itself, so we connect to the
    MySQL server directly (no database selected) and run CREATE DATABASE IF NOT EXISTS.
    """
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{TestingConfig.TEST_DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        conn.close()   # always close the connection, even if the query failed


# scope="session" → this fixture runs ONCE for the whole test run (not once per test),
# because building the Flask app is slow and it doesn't change between tests.
@pytest.fixture(scope="session")
def app(tmp_path_factory):
    _ensure_test_database()
    app = create_app(TestingConfig)
    # Keep the test model file away from the real backend/ml_models/engine.joblib.
    # tmp_path_factory gives a temporary folder that pytest cleans up afterwards.
    model_path = str(tmp_path_factory.mktemp("ml_models") / "engine.joblib")
    app.config["ML_MODEL_PATH"] = model_path
    app.extensions["recommendation_engine"].model_path = model_path
    return app


# autouse=True → runs automatically around EVERY test, without being named as a parameter.
@pytest.fixture(autouse=True)
def _fresh_schema(app):
    engine = app.extensions["recommendation_engine"]
    with app.app_context():          # database work needs an "app context" in Flask
        db.drop_all()                # wipe every table...
        db.create_all()              # ...and recreate them empty, from the models
        engine.model = None          # the DB is empty again, so forget the previous test's model
        yield                        # ← the test itself runs here
        db.session.remove()          # after the test: close the DB session
        db.drop_all()                # and clean up the tables


@pytest.fixture
def client(app):
    """A fake browser: lets tests call the API (client.get / client.post ...) without
    starting a real server."""
    return app.test_client()


@pytest.fixture
def engine(app):
    """The app's RecommendationEngine, so tests can inspect engine.model."""
    return app.extensions["recommendation_engine"]


@pytest.fixture
def seeded(app):
    """Seed the catalogue (12 units, skills, sectors, 2 demo partners, 5 opportunities, admin),
    WITHOUT the demo students. Returns {unit_name: unit_id} so tests can look up ids by name."""
    from app.models import AcademicUnit
    from app.seed.seeder import seed_all
    seed_all(include_demo_students=False)
    return {u.unit_name: u.unit_id for u in AcademicUnit.query.all()}


@pytest.fixture
def seeded_with_students(app):
    """Everything `flask seed-data` creates, INCLUDING the 3 demo students."""
    from app.models import AcademicUnit
    from app.seed.seeder import seed_all
    seed_all()
    return {u.unit_name: u.unit_id for u in AcademicUnit.query.all()}


@pytest.fixture
def skill_ids(seeded):
    """{skill name: skill_id} for the 21 seeded skills."""
    from app.models import Skill
    return {s.name: s.skill_id for s in Skill.query.all()}


@pytest.fixture
def sector_ids(seeded):
    """{sector name: sector_id} for the 7 seeded sectors."""
    from app.models import Sector
    return {s.name: s.sector_id for s in Sector.query.all()}


@pytest.fixture
def profile_body(seeded, skill_ids, sector_ids):
    """Returns a FUNCTION that builds a valid PUT /api/student/profile body.

    profile_body()                                   → varied marks around 60, 2 skills, 1 interest
    profile_body(55, {"Computer Networks": 90}, skills=["Java"], interests=["Software Development"])
    The base marks differ slightly per unit on purpose: 12 IDENTICAL marks would trigger
    the "implausible entry" 409 check.
    """
    def make(default=60, overrides=None, skills=("Python", "SQL"),
             interests=("Data Analytics & AI",), **extra):
        grades = {str(uid): default + (i % 3) for i, uid in enumerate(sorted(seeded.values()))}
        for name, mark in (overrides or {}).items():
            grades[str(seeded[name])] = mark
        return {"grades": grades,
                "skill_ids": [skill_ids[s] for s in skills],
                "sector_ids": [sector_ids[s] for s in interests],
                **extra}
    return make


# ---- Plain helper functions (not fixtures) ------------------------------------------------

def auth_header(token: str) -> dict:
    """The HTTP header that proves who we are: "Authorization: Bearer <JWT>"."""
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, payload: dict) -> str:
    """Register via the API and return an access token."""
    res = client.post("/api/auth/register", json=payload)
    # If registration fails, show the API's error message in the test failure output.
    assert res.status_code == 201, res.get_json()
    res = client.post("/api/auth/login",
                      json={"email": payload["email"], "password": payload["password"]})
    return res.get_json()["access_token"]


def login(client, email: str, password: str) -> str:
    """Log in an EXISTING user and return their access token."""
    return client.post("/api/auth/login",
                       json={"email": email, "password": password}).get_json()["access_token"]


# ---- Sample registration data ---------------------------------------------------------------

@pytest.fixture
def student_payload():
    """Valid student registration body (the data used for test case TC01)."""
    return {
        "role": "student",
        "email": "jane.doe@strathmore.edu",
        "password": "Passw0rd123",
        "confirm_password": "Passw0rd123",
        "admission_no": "168003",
        "first_name": "Jane",
        "last_name": "Doe",
        "course": "BSc Informatics and Computer Science",
        "year_of_study": 3,
    }


@pytest.fixture
def partner_payload():
    """Valid industry partner registration body."""
    return {
        "role": "industry_partner",
        "email": "hr@acme.co.ke",
        "password": "Partner2024",
        "confirm_password": "Partner2024",
        "organization_name": "Acme Kenya Ltd",
        "contact_person": "John Kamau",
        "phone": "+254 712 345678",
    }
